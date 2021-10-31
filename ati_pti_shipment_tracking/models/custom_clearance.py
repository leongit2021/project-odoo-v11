# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from odoo.addons.base_import.models.base_import import xlrd
from base64 import decodestring
import xlsxwriter
import os

from odoo.addons import decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)



_TYPE = [
    ("bc_16", "BC 1.6"),
    ("bc_20", "BC 2.0"),
]

_STATES = [
    ("draft", "Draft"),
    ("confirm", "Waiting SPPB"),
    ("need_bc_28", "Need BC 2.8"),
    ("done", "Done"),
    ("cancelled", "Cancel"),
]

_STATES_BC_28 = [
    ("draft", "Draft"),
    ("done", "Done"),
    ("cancelled", "Cancel"),
]


class CustomClearance(models.Model):
    _name = 'custom.clearance'
    _description = "Custom Clearance"
    _order = 'id asc'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string='Number',track_visibility="onchange")
    awb_bl_id = fields.Many2one('awb.bl', string='Nomor AWB/BL')
    shipping_instruction_id = fields.Many2one('goods.invoice', related='awb_bl_id.awb_bl_ids', string='Shipping Instruction')
    job_ref = fields.Char(string='Vendor Job Ref')
    pabean_partner_id = fields.Many2one('res.partner', string='Kantor Pabean',  change_default=True, track_visibility='always')
    # bc_type = fields.Selection(selection=_TYPE,string="BC Type",index=True,track_visibility="onchange",copy=False)
    bc_type_id = fields.Many2one('bc.bc',string='BC Type')
    code = fields.Char(related='bc_type_id.code',string='BC Type Code')
    state = fields.Selection(selection=_STATES,string="Status",index=True,track_visibility="onchange",copy=False,default="draft")
    arrival_date = fields.Datetime(string='Arrival Date', compute='_get_arrival_date') 
    
    goods_detail_ids = fields.Many2many('pickup.goods.line', string='Goods', compute='_onchange_awb_bl_id')
    document_ids = fields.One2many('custom.clearance.document','document_id', string="Document Checklist")
    bc_two_eight_ids = fields.One2many('bc.two.eight','bc_two_eight_id', string="BC 2.8")
    box_ids = fields.Many2many('goods.invoice.line', string='Load Code')

    
    # step 1 
    # BC 1.6/ BC 2.0
    submission_no = fields.Char(string='Nomor Pengajuan')
    submission_date = fields.Date(string='Tanggal Pengajuan')
    registration_no = fields.Char(string='Nomor Pendaftaran')
    registration_date = fields.Date(string='Tanggal Pendaftaran')
    hoarding_place = fields.Char(string='Tempat Penimbunan')
    # Input BC: 1.6/ BC 2.0
    sppb_no = fields.Char(string='Nomor SPPB')
    sppb_date = fields.Date(string='Tanggal SPPB')
    sppb_registration_no = fields.Char(string='Nomor Daftar')
    item_out_date = fields.Datetime(string='Tanggal Pengeluaran Barang') 

    # # step 2
    # # BC 1.6 to BC 2.8
    

    @api.model
    def create(self, vals):
        res = super(CustomClearance, self).create(vals)
        name = self.env['ir.sequence'].next_by_code(self._name)
        if name:
            res['name'] = name
        return res


    @api.depends('awb_bl_id','box_ids')
    def _onchange_awb_bl_id(self):
        self.goods_detail_ids = False
        self.awb_bl_document_ids = False
        # self.box_ids = False
        if self.awb_bl_id and self.awb_bl_id.awb_bl_ids and self.awb_bl_id.awb_bl_ids.goods_detail_ids:
            if self.box_ids:
                ids = []
                for rec in self.awb_bl_id.awb_bl_ids.goods_detail_ids:
                    if rec.load_code in self.box_ids.mapped('commercial_invoice_id.name'):
                        ids.append(rec.id)
                self.goods_detail_ids = ids
            else:
                self.goods_detail_ids = self.awb_bl_id.awb_bl_ids.goods_detail_ids.ids
        

    @api.onchange('awb_bl_id')
    def onchange_awb_bl_id(self):
        self.job_ref = self.awb_bl_id and self.awb_bl_id.job_ref or ''
        self.box_ids = False
        if self.awb_bl_id and self.awb_bl_id.document_ids:
            vals = []
            for rec in self.awb_bl_id.document_ids:
                val = {
                    'document_check_id': rec.document_check_id.id or False,
                    'remarks': rec.remarks or '',
                    'date': rec.date or False,
                    'attachment': rec.attachment,
                }
                vals.append((0,0,val))
            self.document_ids = vals
        else:
            self.document_ids = [(5,0,0)]


    def action_draft(self):
        self._updateby_set_draft_bc_type()
        return self.write({'state': 'draft'})

    def action_confirm(self):
        self._warning_goods_detail()
        self._updateby_confirm_bc_type()
        # update state tracking
        self._set_state_tracking()
        return self.write({'state': 'confirm'})
    
    def action_need_bc_28(self):
        self._warning_all_made_bc_28()
        return self.write({'state': 'done'})

    def action_done(self):
        if self.bc_type_id and self.bc_type_id.code in ('BC16'):
            self._update_receipt()
            # update state tracking
            self._set_state_tracking()
            return self.write({'state': 'need_bc_28'})
        else:
            # update qty receipt wh/in
            self._update_receipt()
            # update state tracking
            self._set_state_tracking()

        return self.write({'state': 'done'})

    def action_cancel(self):
        self._updateby_cancel()
        return self.write({'state': 'cancelled'})

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Can not deleted if state not draft."))
                
        return super(CustomClearance, self).unlink()

    # define state tracking
    def _set_state_tracking(self):
        # action confirm
        if self.state == 'draft':
            if self.bc_type_id.code in ('BC16','BC20'):
                for rec in self.goods_detail_ids:
                    rec.state_tracking = 'waiting_pabean_1'
        # action done
        if self.state == 'confirm':
            if self.bc_type_id.code == 'BC16':
                for rec in self.goods_detail_ids:
                    rec.state_tracking = 'clear_pabean_1_plb'
            elif self.bc_type_id.code == 'BC20':
                for rec in self.goods_detail_ids:
                    rec.state_tracking = 'clear_pabean_1_wh'
            else:
                pass


    @api.depends('awb_bl_id')
    def _get_arrival_date(self):
        for rec in self.awb_bl_id:
            if rec.bill_type == 'awb':
                for line in rec.awb_transit_history_ids:
                    self.arrival_date = line.arrival_date or False
            elif rec.bill_type == 'bl':
                for line in rec.bl_transit_history_ids:
                    self.arrival_date = line.arrival_date or False
            else:
                pass


    def _warning_goods_detail(self):
        custom_clearance = self.env[self._name].sudo().search([('awb_bl_id','=', self.awb_bl_id.id),('id','!=',self.id)])
        ids = [line.id for cc in custom_clearance for line in cc.goods_detail_ids]
        for rec in self.goods_detail_ids:
            if rec.id in ids:
                raise UserError(_("Warning, it has been used before, SP Number: %s, Load Code: %s." %(rec.partner_ref or '', rec.load_code or '')))

    def _warning_all_made_bc_28(self):
        ids = [line.id for bc in self.bc_two_eight_ids for line in bc.goods_detail_ids]
        for rec in self.goods_detail_ids:
            if not rec.id in ids:
                raise UserError(_("Warning, Need BC 2.8 for SP Number: %s, Load Code: %s." %(rec.partner_ref or '', rec.load_code or '')))


    def _updateby_confirm_bc_type(self):
        if self.bc_type_id:
            for rec in self.goods_detail_ids:
                rec.need_bc_ids = [(4,self.bc_type_id.id)]
    
    def _updateby_set_draft_bc_type(self):
        if self.bc_type_id:
            for rec in self.goods_detail_ids:
                rec.need_bc_ids = [(3,self.bc_type_id.id)]

    def _updateby_cancel(self):
        if self.bc_type_id and self.bc_type_id.code in ('BC16'):
            for rec in self.goods_detail_ids.mapped('purchase_order_line_id.order_id'):
                picking = rec.picking_ids.filtered(lambda r: r.custom_clearance_id.id == self.id) 
                if picking.state in ('done','cancel'):
                    raise UserError(_("Warning, Can not cancel. %s has status Done or Cancel ." %(picking.name)))
                
                # warning bc 2.8
                self._warning_cancel()

                if picking:
                    for good in self.goods_detail_ids:
                        moves = picking.move_lines.filtered(lambda s: s.purchase_line_id.id == good.purchase_order_line_id.id)
                        for line in moves:
                            line.write({'bc_16_no_pengajuan': '', 
                            'bc_16_no_pendaftaran': '',
                            'bc_16_tanggal_pendaftaran': False,
                            'no_skep': '',
                            'skep_date': False,
                            'line_no_skep': 0,
                            'quantity_skep':0,})
                    # unrelated custom clrearance
                    picking.custom_clearance_id = False
                

        else:
            for rec in self.goods_detail_ids.mapped('purchase_order_line_id.order_id'):
                picking = rec.picking_ids.filtered(lambda r: r.custom_clearance_id.id == self.id) 
                if picking.state in ('done','cancel'):
                    raise UserError(_("Warning, Can not cancel. %s has status Done or Cancel ." %(picking.name)))

                if picking:
                    for good in self.goods_detail_ids:
                        moves = picking.move_lines.filtered(lambda s: s.purchase_line_id.id == good.purchase_order_line_id.id)
                        for line in moves:
                            line.quantity_done = 0
                    # unrelated custom clrearance
                    picking.custom_clearance_id = False

    def _warning_cancel(self):
        if len(self.bc_two_eight_ids) > 0:
            raise UserError(_("Warning, Can not cancel. Set draft all BC 2.8 then delete."))

    # skep
    def _get_param_skep(self, skep=False, product=False):
        if skep:
            for rec in skep.skep_ids:
                if rec.part_number == product.default_code:
                    return rec.seq_skep, rec.skep_qty
                return 0,0
        else:
            return 0,0


    def _update_receipt(self):
        if self.bc_type_id and self.bc_type_id.code in ('BC16'):
            for rec in self.goods_detail_ids.mapped('purchase_order_line_id.order_id'):
                ids = rec.picking_ids.filtered(lambda r: r.state not in ('done','cancel')).ids
                if ids:
                    picking = rec.picking_ids.filtered(lambda r: r.id == max(ids)) 
                    for good in self.goods_detail_ids:
                        moves = picking.move_lines.filtered(lambda s: s.purchase_line_id.id == good.purchase_order_line_id.id)
                        for line in moves:
                            line.bc_16_no_pengajuan = self.submission_no or '' 
                            line.bc_16_no_pendaftaran = self.registration_no or ''
                            line.bc_16_tanggal_pendaftaran = self.registration_date or False
                            line.no_skep = good.skep_pib_id.skep_no or ''
                            line.skep_date = good.skep_pib_id.skep_date or False
                            line_no_skep, quantity_skep = self._get_param_skep(skep=good.skep_pib_id, product=good.purchase_order_line_id.product_id)
                            line.line_no_skep = line_no_skep
                            line.quantity_skep = quantity_skep
                    
                    # related to customer clearance 
                    picking.custom_clearance_id = self.id or False
                    picking.scheduled_date = self.item_out_date or False

        else:
            for rec in self.goods_detail_ids.mapped('purchase_order_line_id.order_id'):
                ids = rec.picking_ids.filtered(lambda r: r.state not in ('done','cancel')).ids
                if ids:
                    picking = rec.picking_ids.filtered(lambda r: r.id == max(ids)) 
                    for good in self.goods_detail_ids:
                        moves = picking.move_lines.filtered(lambda s: s.purchase_line_id.id == good.purchase_order_line_id.id)
                        for line in moves:
                            line.quantity_done = good.picked_qty

                    # related to customer clearance 
                    picking.custom_clearance_id = self.id or False
                    picking.scheduled_date = self.item_out_date or False
            

    @api.multi
    def _compute_bc_two_eight(self):
        for rec in self:
            bc_two_eight_count = self.env['bc.two.eight'].sudo().search([('bc_two_eight_id', '=', rec.id)])
            rec.bc_two_eight_count = len(bc_two_eight_count)


    @api.multi
    def bc_two_eight_view(self):
        self.ensure_one()
        views = [(self.env.ref('ati_pti_shipment_tracking.bc_two_eight_tree').id,'tree'),(self.env.ref('ati_pti_shipment_tracking.bc_two_eight_form').id,'form')]
        domain = [('bc_two_eight_id', '=', self.id)]
        return {
            'name': ('BC 2.8'),
            'domain': domain,
            'res_model': 'bc.two.eight',
            'type': 'ir.actions.act_window',
            # 'view_id': False,
            'views': views,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'help': ('''<p class="oe_view_nocontent_create">
                           Click to Create for BC 2.8
                        </p>'''),
            'limit': 80,
            'context': "{'default_bc_two_eight_id': %s}" % (self.id)
        }

    bc_two_eight_count = fields.Integer(compute='_compute_bc_two_eight')


    @api.multi
    def _compute_inventory_receipt(self):
        for rec in self:
            stock_picking_count = self.env['stock.picking'].sudo().search([('custom_clearance_id', '=', rec.id)])
            rec.stock_picking_count = len(stock_picking_count)

    @api.multi
    def cc_inventory_view(self):
        self.ensure_one()
        domain = [('custom_clearance_id', '=', self.id)]
        return {
            'name': ('Inventory Receipt'),
            'domain': domain,
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            # 'help': ('''<p class="oe_view_nocontent_create">
            #                Click to Create for BC 2.8
            #             </p>'''),
            'limit': 80,
            'context': "{'default_custom_clearance_id': %s}" % (self.id)
        }

    stock_picking_count = fields.Integer(compute='_compute_inventory_receipt')


class BcTwoEight(models.Model):
    _name = 'bc.two.eight'
    _description = "BC 2.8"
    _order = 'id asc'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    # step 2
    # BC 1.6 to BC 2.8
    name = fields.Char(string='Number')
    submission_no = fields.Char(string='Nomor Pengajuan')
    bc_two_eight_id  = fields.Many2one('custom.clearance', string='Custom Clearance', ondelete='cascade')
    submission_date = fields.Date(string='Tanggal Pengajuan')
    registration_no = fields.Char(string='Nomor Pendaftaran')
    registration_date = fields.Date(string='Tanggal Pendaftaran')
    hoarding_place = fields.Char(string='Tempat Penimbunan')
    # Input BC: BC 2.8
    sppb_no = fields.Char(string='Nomor SPPB')
    sppb_date = fields.Date(string='Tanggal SPPB')
    sppb_registration_no = fields.Char(string='Nomor Daftar')
    goods_detail_ids = fields.Many2many('pickup.goods.line', string='Goods')
    # instruction_id = fields.Many2one('goods.invoice',string='Shipping Instruction')
    pickup_goods_id = fields.Many2one('pickup.goods', related='bc_two_eight_id.awb_bl_id.awb_bl_ids.invoice_id',string='Collect Order')
    state = fields.Selection(selection=_STATES_BC_28,string="Status",index=True,track_visibility="onchange",copy=False,default="draft")
    bc_type_id = fields.Many2one('bc.bc',string='BC Type', default=lambda self: self.env['bc.bc'].search([('code','=','BC28')], limit=1))


    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id,'%s%s' % (rec.submission_no if rec.submission_no else '', '/'+rec.sppb_no if rec.sppb_no else '')))
        return res


    def action_draft(self):
        self._updateby_draft_bc()
        return self.write({'state': 'draft'})

    def action_done(self):
        if len(self.goods_detail_ids) < 1:
            raise UserError(_("Warning, Empty Goods Detail."))
        
        self._updateby_confirm_bc()
        # update state tracking
        self._set_state_tracking()
        return self.write({'state': 'done'})

    def action_cancel(self):
        self._updateby_cancel()
        return self.write({'state': 'cancelled'})

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Can not deleted if state not draft."))
                
        return super(BcTwoEight, self).unlink()

    # define state tracking
    def _set_state_tracking(self):
        if self.state == 'draft':
            for rec in self.goods_detail_ids:
                rec.state_tracking = 'clear_pabean_2_plb'


    def _updateby_confirm_bc(self):
        if self.bc_two_eight_id:
            for rec in self.goods_detail_ids:
                goods = self.bc_two_eight_id.goods_detail_ids.filtered(lambda r: r.id == rec.id)
                for g in goods:
                    g.need_bc_ids = [(4,self.bc_type_id.id)]

            for rec in self.goods_detail_ids.mapped('purchase_order_line_id.order_id'):
                ids = rec.picking_ids.filtered(lambda r: r.state not in ('done','cancel')).ids
                picking = rec.picking_ids.filtered(lambda r: r.id == max(ids)) 
                if ids:
                    for good in self.goods_detail_ids:
                        # unique purchase order line - purchase line id
                        moves = picking.move_lines.filtered(lambda s: s.purchase_line_id.id == good.purchase_order_line_id.id)
                        for line in moves:
                            line.bc_28_no_pengajuan = self.submission_no or '' 
                            line.bc_28_no_pendaftaran = self.registration_no or ''
                            line.bc_28_tanggal_pendaftaran = self.registration_date or False
                            line.no_sppb = self.sppb_no or ''
                            line.quantity_bc_28 = good.picked_qty 
                            line.quantity_done = good.picked_qty  
                    # related to bc 2.8 
                    picking.bc_two_eight_id = self.id or False


    def _updateby_cancel(self):
        for rec in self.goods_detail_ids.mapped('purchase_order_line_id.order_id'):
            picking = rec.picking_ids.filtered(lambda r: r.bc_two_eight_id.id == self.id) 
            if picking.state in ('done','cancel'):
                raise UserError(_("Warning, Can not cancel. %s has status Done or Cancel ." %(picking.name)))
            
            if picking:
                for good in self.goods_detail_ids:
                    moves = picking.move_lines.filtered(lambda s: s.purchase_line_id.id == good.purchase_order_line_id.id)
                    for line in moves:
                        line.write({'bc_28_no_pengajuan': '', 
                        'bc_28_no_pendaftaran': '',
                        'bc_28_tanggal_pendaftaran': False,
                        'no_sppb': '',
                        'quantity_bc_28': 0,
                        'quantity_done':0,})
                # unrelated bc 2.8
                picking.bc_two_eight_id = False
                

    def _updateby_draft_bc(self):
        if self.bc_two_eight_id:
            for rec in self.goods_detail_ids:
                goods = self.bc_two_eight_id.goods_detail_ids.filtered(lambda r: r.id == rec.id)
                for g in goods:
                    g.need_bc_ids = [(3,self.bc_type_id.id)]


    @api.onchange('goods_detail_ids','id','bc_type_id','bc_two_eight_id')
    def _onchange_goods_detail_ids(self):
        bc_two_eight = self.env['bc.two.eight'].search([('bc_two_eight_id','=', self.bc_two_eight_id.id)])
        reference = [line.id for bc in bc_two_eight for line in bc.goods_detail_ids]
        ids = []
        for rec in self.bc_two_eight_id.goods_detail_ids:
            if not rec.id in reference:
                ids.append(rec.id)
        return {'domain': {'goods_detail_ids': [('id','in',ids)]}}


    @api.multi
    def _compute_inventory_receipt(self):
        for rec in self:
            stock_picking_count = self.env['stock.picking'].sudo().search([('bc_two_eight_id', '=', rec.id)])
            rec.stock_picking_count = len(stock_picking_count)


    @api.multi
    def bc_two_eight_inventory_view(self):
        self.ensure_one()
        domain = [('bc_two_eight_id', '=', self.id)]
        return {
            'name': ('Inventory Receipt'),
            'domain': domain,
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            # 'help': ('''<p class="oe_view_nocontent_create">
            #                Click to Create for BC 2.8
            #             </p>'''),
            'limit': 80,
            'context': "{'default_bc_two_eight_id': %s}" % (self.id)
        }

    stock_picking_count = fields.Integer(compute='_compute_inventory_receipt')

   

class CustomClearanceDocumentChecklist(models.Model):
    _name = 'custom.clearance.document'
    _description = "Document Checklist"
    _order = 'id asc'


    document_check_id  = fields.Many2one('document.checklist.type', string='Document Checklist')
    document_id  = fields.Many2one('custom.clearance', string='Document Checklist', ondelete='cascade')
    remarks = fields.Char(string='Remarks/Subject')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    attachment = fields.Binary(string='Attachment')


class BcType(models.Model):
    _name = 'bc.bc'
    _description = "BC Type"
    _order = 'id asc'


    name = fields.Char(string='BC')
    code = fields.Char(string='Code')
    