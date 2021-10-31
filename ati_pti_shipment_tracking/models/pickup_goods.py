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



_STATES = [
    ("draft", "Draft"),
    ("supervisor", "Waiting SAC Supervisor"),
    ("logistics", "Waiting Logistics Confirmation"),
    ("confirmed", "Done"),
    ("cancelled", "Cancelled"),
    ("unlocked", "Unlock"),
]

_STATES_SI = [
    ("si_partial", "Onprogress"),
    ("si_full", "Complete"),
]

_STATES_INV = [
    ("draft", "Draft"),
    ("waiting", "Waiting Validation"),
    ("logistic", "Logistic Validation"),
    # ("done", "Done"),
    ("cancelled", "Cancelled"),
]

_STATES_CLARIFICATION = [
    ("draft", "Draft"),
    ("done", "Done"),
    ("cancelled", "Cancelled"),
]

_CO_TYPE = [
    ("div_21", "DIV-21"),
    ("general", "General"),
]

_STATES_TRACKING = [
    ("draft","Draft"),
    ("order_to_collect", "Ordered To Collect"),
    ("at_forwarder_wh", "At Forwarder WH"),
    ("in_port_of_origin", "In Port Of Origin"),
    ("in_port_of_transit", "In Port Of Transit"),
    ("arrived_in_dest", "Arrived In Destination"),
    ("waiting_pabean_1", "Waiting Pabean 1"),
    ("clear_pabean_1_wh", "Clear Pabean 1 (WH)"),
    ("in_pti_warehouse", "In PTI Warehouse"),
    ("clear_pabean_1_plb", "Clear Pabean 1 (PLB)"),
    ("clear_pabean_2_plb", "Clear Pabean 2 (PLB)"),
]

class PickupGoods(models.Model):
    _name = 'pickup.goods'
    _description = "Pickup Goods"
    _order = 'id asc'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string='Pickup No.', index=True, track_visibility='onchange', defaul='_New')
    created_by = fields.Many2one('res.users','Created By', default=lambda self: self.env.user.id)
    partner_id = fields.Many2one('res.partner', string='Forwarder',  change_default=True, track_visibility='always')
    supervisor_date = fields.Datetime(string='SAC Supervisor Date') 
    logistics_date = fields.Datetime(string='Logistics Confirmation Date') 
    confirmed_date = fields.Datetime(string='Confirmed Date') 
    state = fields.Selection(selection=_STATES,string="Status Order",index=True,track_visibility="onchange",copy=False,default="draft")
    si_state = fields.Selection(selection=_STATES_SI,string="Status Instruction",index=True,track_visibility="onchange",copy=False,default="si_partial")
    pickup_ids = fields.One2many('pickup.goods.line','pickup_id', string='Pickup')
    invoice_ids = fields.One2many('goods.invoice','invoice_id', string='Shipping Invoice')
    is_lartas = fields.Boolean('Lartas?')
    mode_transport = fields.Many2one('mode.transport', string='Mode Of Transport')
    origin = fields.Many2one('departure.arrival',string='Origin')
    destination = fields.Many2one('departure.arrival',string='Destination')

    # co_type = fields.Selection(selection=_CO_TYPE,string="Type",index=True,track_visibility="onchange",copy=False,default="div_21")


    @api.model
    def create(self, vals):
        res = super(PickupGoods, self).create(vals)
        name = self.env['ir.sequence'].next_by_code(self._name)
        if name:
            # date = fields.Datetime.from_string(fields.Datetime.now())
            # res['name'] = name.replace(name[3:5], str(date.year)[-2:])
            res['name'] = name
        return res


    def _warning_pickup_ids(self):
        if len(self.pickup_ids) == 0:
            raise UserError(_("Nothing Collect Goods."))

    @api.onchange('pickup_ids','pickup_ids.id')
    def _set_sequence(self):
        sequence = 1
        for rec in self.pickup_ids:
            rec.sequence = sequence
            sequence += 1


    @api.onchange('pickup_ids','pickup_ids.is_lartas')
    def onchange_pickup_ids(self):
        self.is_lartas = False
        if any([lartas.is_lartas for lartas in self.pickup_ids]):
            self.is_lartas = True
      
    def action_draft(self):
        return self.write({'state':'draft'})

    def action_supervisor(self):
        self._warning_pickup_ids()
        for rec in self.pickup_ids:
            rec.purchase_order_line_id.pickup_id = self.id
        # 
        self._set_state_tracking()

        self.supervisor_date = fields.Datetime.now()    
        return self.write({'state':'supervisor'})

    def action_logistics(self):
        self.logistics_date = fields.Datetime.now()
        return self.write({'state':'logistics'})
    
    def action_confirmed(self):
        new_invoice = self.env['goods.invoice'].sudo()
        new_commercial_no = self.env['commercial.invoice'].sudo()
        new_report_survey = self.env['report.survey'].sudo()
        existing_invoice = self.env['goods.invoice'].sudo().search([('invoice_id','=',self.id)], limit=1)
        val = {'partner_id': self.partner_id and self.partner_id.id or False}
        # new create/update shipping invoice
        if existing_invoice:
            currenct_commercial_no = self.env['commercial.invoice'].sudo().search([('pickup_goods_id','=',self.id)])
            current_report_survey = self.env['report.survey'].sudo().search([('survey_id.invoice_id','=', self.id)])
            # # inv.write(val)
            # for line in inv.invoice_line_ids.filtered(lambda r: r.purchase_id.id in self.pickup_ids.mapped('purchase_id').ids):
            #     line.write({'partner_ref': line.purchase_id.partner_ref,'customer_partner_ref': line.purchase_id.x_client_order_ref })

            # update shipment instruction
            for wj in self.pickup_ids.mapped('load_code'):
                if wj and wj not in list(set(currenct_commercial_no.mapped('name'))):
                    po_by_wj = self.pickup_ids.filtered(lambda powj: powj.load_code == wj).mapped('purchase_id')
                    val_commercial_no = {'pickup_goods_id': self.id,'name': wj or '', 'purchase_id': po_by_wj.id or False}
                    new_commercial_no |= new_commercial_no.create(val_commercial_no)

            # # update survey
            # for lartas in self.pickup_ids.filtered(lambda lartas: lartas.is_lartas == True):
            #     if lartas.purchase_order_line_id.id not in current_report_survey.mapped('purchase_order_line_id').ids and lartas.load_code not in current_report_survey.mapped('load_code'):
            #         new_report_survey |= new_report_survey.create({'sequence': seq,'purchase_order_line_id':lartas.purchase_order_line_id.id,'survey_id': new_invoice.id})

                
        else:
            # create new
            for wj in list(set(self.pickup_ids.mapped('load_code'))):
                po_by_wj = self.pickup_ids.filtered(lambda powj: powj.load_code == wj).mapped('purchase_id')
                val_commercial_no = {'pickup_goods_id': self.id,'name': wj or '', 'purchase_id': po_by_wj.id or False}
                new_commercial_no |= new_commercial_no.create(val_commercial_no)
            # 
            val.update({
                        'invoice_id': self.id,
                        'invoice_line_ids': [(0,0,{'commercial_invoice_id': com.id, 'purchase_id':com.purchase_id.id,'partner_ref':com.purchase_id.partner_ref,'customer_partner_ref':com.purchase_id.x_client_order_ref}) for com in new_commercial_no],
                        # 'invoice_line_ids': [(0,0,{'purchase_id':purchase.id,'partner_ref':purchase.partner_ref,'customer_partner_ref':  purchase.x_client_order_ref}) for purchase in self.pickup_ids.mapped('purchase_id')],
                        # 'survey_ids': survey,
                        })

            new_invoice |= new_invoice.create(val)
            # 
            survey = []
            seq = 1
            for lartas in self.pickup_ids.filtered(lambda lartas: lartas.is_lartas == True):
                new_report_survey |= new_report_survey.create({'sequence': seq,'purchase_order_line_id':lartas.purchase_order_line_id.id,'survey_id': new_invoice.id})
                seq += 1

        # update purchase order line: qty picked up
        for pol in self.pickup_ids:
            new_picked_qty = pol.picked_qty + pol.purchase_order_line_id.picked_qty
            pol.purchase_order_line_id.write({'picked_qty': new_picked_qty})
                        
            # update summary nor goods: pickup_qty
            summary_nor_goods = self.env['summary.nor.goods'].sudo().search([
                                                                ('purchase_id','=',pol.purchase_id.id),
                                                                ('position','=',pol.purchase_order_line_id.sequence),
                                                                ('product_id','=',pol.product_id.id)
                                                                ])
            for summary in summary_nor_goods:
                new_picked_qty_nor = pol.picked_qty + summary.pickup_qty
                summary.write({'pickup_qty': new_picked_qty_nor})

        self.confirmed_date = fields.Datetime.now()
        return self.write({'state':'confirmed'})


    def action_cancelled(self):
        for rec in self.pickup_ids:
            rec.purchase_order_line_id.pickup_id = False

        return self.write({'state':'cancelled'})

    def action_unlocked(self):
        return self.write({'state':'unlocked'})

    def action_locked(self):
        self.action_confirmed()


    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Can not deleted if state not draft."))
                
        return super(PickupGoods, self).unlink()

    @api.multi
    def action_delete_pickup_line(self):
        for rec in self.pickup_ids:
            rec.unlink()


    # @api.onchange('origin','destination')
    # def _warning_origin_destination(self):
    #     self.ensure_one()
    #     if self.origin.id == self.destination.id:
    #             raise UserError(_("Can not the same origin and destination."))

    @api.constrains('origin')
    def _warning_origin_destination(self):
        self.ensure_one()
        if self.origin.id == self.destination.id:
                raise UserError(_("Can not the same origin and destination."))
            
    
    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id,'%s' % (rec.name if rec.name else '')))
        return res


    @api.multi
    def _compute_purchase_order_line(self):
        for rec in self:
            purchase_order_line = self.env['purchase.order.line'].sudo().search([('pickup_id', '=', rec.id)])
            rec.purchase_order_line_count = len(purchase_order_line)


    @api.multi
    # @api.one
    def purchase_order_line_view(self):
        self.ensure_one()
        domain = [('pickup_id', '=', self.id)]
        views = self.env.ref('purchase_order_line_tree_st',False)
        return {
            'name': ('Purchase Order Line'),
            'domain': domain,
            'res_model': 'purchase.order.line',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'help': ('''<p class="oe_view_nocontent_create">
                           Click to Show Order Line
                        </p>'''),
            'limit': 80,
            'context': "{'default_pickup_id': %s}" % (self.id)
        }

    purchase_order_line_count = fields.Integer(compute='_compute_purchase_order_line')

    # define state tracking
    def _set_state_tracking(self):
        for rec in self.pickup_ids:
            rec.state_tracking = 'order_to_collect'
    

class PickupGoodsLine(models.Model):
    _name = 'pickup.goods.line'
    _description = "Pickup Goods Detail"
    _order = 'id asc'
        

    pickup_id = fields.Many2one('pickup.goods', string='Goods', ondelete='cascade')
    sequence = fields.Integer(string='Sequence')
    purchase_order_line_id = fields.Many2one('purchase.order.line', string='Purchase Order Line')
    purchase_id = fields.Many2one('purchase.order', related='purchase_order_line_id.order_id',string='PO Number')
    po_number = fields.Char(string="PO Number", related="purchase_id.name", store=True)
    partner_ref = fields.Char(string='Vendor Reference', related='purchase_id.partner_ref')
    load_code = fields.Char(string='Load Code', related='purchase_order_line_id.load_code')
    transaction_method_id = fields.Many2one('transaction.method', related='purchase_id.sale_id.transaction_method_id', string='Transaction Method')
    transaction_method_name = fields.Char(related='transaction_method_id.name',string='Transaction Method')
    po_line_number = fields.Integer(related='purchase_order_line_id.sequence', string='PO Line Number')
    product_id = fields.Many2one('product.product', related='purchase_order_line_id.product_id', string='Product')
    item_code = fields.Char(string='Item Code', related='product_id.default_code')
    item_desc = fields.Text(string='Description', related='purchase_order_line_id.name')
    # item_code = fields.Char(string='Item Code & Description', compute='_get_item_description')
    product_qty = fields.Float(related='purchase_order_line_id.product_qty', string='Qty Ordered', readonly='1',digits=dp.get_precision('Product Unit of Measure'))    
    product_uom = fields.Many2one(related='purchase_order_line_id.product_uom', string='UoM PO')
    picked_qty  = fields.Float(string='Qty to Collect', digits=dp.get_precision('Product Unit of Measure'))
    picked_uom = fields.Many2one('product.uom',string='UoM to Collect')
    rts_date = fields.Date(string='RTS Date') 
    nor_date = fields.Date(string='NOR Date', related='purchase_order_line_id.nor_date')
    is_lartas = fields.Boolean('Lartas?', compute='_show_lartas')
    # add to dashboard
    state_tracking = fields.Selection(selection=_STATES_TRACKING,string="Status",index=True,track_visibility="onchange",copy=False,default="draft")
    need_bc_ids = fields.Many2many('bc.bc', string='BC Type')
    skep_pib_id = fields.Many2one('skep.pib', related='purchase_order_line_id.skep_pib_id', string='SKEP')



    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id,'%s%s%s' % (rec.pickup_id.name if rec.pickup_id else '', '/'+rec.po_number if rec.po_number else '', '/'+rec.partner_ref if rec.partner_ref else '')))
        return res

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        domain = args + ['|','|', ('pickup_id.name', operator, name), ('po_number', operator, name),('partner_ref', operator, name)]
        return super(PickupGoodsLine, self).search(domain, limit=limit).name_get()
    

    # @api.depends('purchase_order_line_id','product_id')
    # def _get_item_description(self):
    #     for rec in self:
    #         if rec.purchase_order_line_id and rec.product_id:
    #            rec.item_code = '[%s]%s' %(rec.product_id.default_code or '',rec.purchase_order_line_id.name or '')

    @api.onchange('purchase_order_line_id')
    def onchage_purchase_order_line(self):
        for rec in self:
            if rec.purchase_order_line_id:
                if rec.picked_qty < 0:
                    raise UserError(_("Not allowed Qty less than zero(0)."))

            # count picked qty  on progress
            picked_qty_onprogress = sum(self.env['pickup.goods.line'].sudo().search([('purchase_order_line_id','=',rec.purchase_order_line_id.id),('pickup_id.state','not in',('draft','confirmed','cancelled'))]).mapped('picked_qty'))
            
            if rec.purchase_order_line_id:
                if rec.purchase_order_line_id.load_code == '' or not rec.purchase_order_line_id.load_code:
                    rec['picked_qty'] = rec.purchase_order_line_id.buffer_qty - picked_qty_onprogress
                else:
                    picked_qty_nor = self.env['summary.nor.goods'].sudo().search([('sales_order_no','=',rec.purchase_order_line_id.partner_ref),('position','=',rec.purchase_order_line_id.sequence),('product_id','=',rec.purchase_order_line_id.product_id.id)])
                    rec['picked_qty'] = sum([pqn.buffer_qty for pqn in picked_qty_nor])



    @api.depends('purchase_order_line_id','product_id')
    def _show_lartas(self):
        for rec in self:
            if rec.product_id.product_lartas in ('LARTAS','Lartas','lartas'):
                rec.is_lartas = True

    @api.onchange('picked_qty')
    def _warning_picked_qty(self):
        for rec in self:
            if rec.purchase_order_line_id:
                if rec.picked_qty <= 0:
                    raise UserError(_("Not allowed Qty less than or equal zero(0)."))

            picked_qty_onprogress = sum(self.env['pickup.goods.line'].sudo().search([('purchase_order_line_id','=',rec.purchase_order_line_id.id),('pickup_id.state','not in',('draft','confirmed','cancelled'))]).mapped('picked_qty'))

            if rec.purchase_order_line_id.load_code == '' or not rec.purchase_order_line_id.load_code:
                qty_limit = rec.purchase_order_line_id.buffer_qty - picked_qty_onprogress
                if rec.picked_qty > qty_limit:
                    raise UserError(_("Not allowed: Qty Pickup greater than %d." % (qty_limit)))
            else:
                picked_qty_nor = self.env['summary.nor.goods'].sudo().search([('sales_order_no','=',rec.purchase_order_line_id.partner_ref),('position','=',rec.purchase_order_line_id.sequence),('product_id','=',rec.purchase_order_line_id.product_id.id)])
                qty_limit = sum([pqn.buffer_qty for pqn in picked_qty_nor]) - picked_qty_onprogress
                if rec.picked_qty > qty_limit:
                    raise UserError(_("Not allowed: Qty Pickup greater than %d." % (qty_limit)))


    @api.constrains('picked_qty')
    def _constrains_picked_qty(self):
        for rec in self:
            if rec.purchase_order_line_id:
                if rec.picked_qty < 0:
                    raise UserError(_("Not allowed Qty less than zero(0)."))

        

class GoodsInvoice(models.Model):
    _name = 'goods.invoice'
    _description = "Pickup Goods Invoice"
    _order = 'id asc'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    
    name = fields.Char(string='Document No.')
    invoice_id = fields.Many2one('pickup.goods', string='Invoice Line', ondelete='cascade')
    date = fields.Date(string='Pickup Date', default=fields.Datetime.now)
    partner_id = fields.Many2one('res.partner', string='Forwarder',  change_default=True, track_visibility='always')
    mode_transport = fields.Many2one('mode.transport', string='Mode Of Transport')
    departure = fields.Many2one('departure.arrival',string='Origin')
    arrival = fields.Many2one('departure.arrival',string='Destination')
    invoice_line_ids = fields.One2many('goods.invoice.line','invoice_line_id', string='Shipping Invoice Detail')
    # survey_ids = fields.One2many('report.survey','survey_id', string='Survey', compute='')
    survey_ids = fields.Many2many('report.survey', string='Survey', compute='depends_goods_detail_ids')
    goods_detail_ids = fields.Many2many('pickup.goods.line', string='Goods', compute='depends_invoice_line_ids')
    # awb_bl_ids = fields.One2many('awb.bl','awb_bl_id', string='AWB/BL')
    awb_bl_id = fields.Many2one('awb.bl', string='AWB/BL')
    
    state = fields.Selection(selection=_STATES_INV,string="Status",index=True,track_visibility="onchange",copy=False,default="draft")
    currency_id  = fields.Many2one('res.currency', string='Currency')
    amount_total = fields.Monetary(string='Amount Total')    
    shipping_marks = fields.Html(string='Shipping Marks')
    total_boxes_qty = fields.Float(string='Total Boxes Qty', compute='_compute_total')
    total_gross_lb = fields.Float(string='Total Gross Weight (Lbs)', compute='_compute_total')
    total_gross_kg = fields.Float(string='Total Gross Weight (Kgs)', compute='_compute_total')


    @api.model
    def create(self, vals):
        res = super(GoodsInvoice, self).create(vals)
        name = self.env['ir.sequence'].next_by_code(self._name)
        if name:
            # date = fields.Datetime.from_string(fields.Datetime.now())
            # res['name'] = name.replace(name[3:5], str(date.year)[-2:])
            res['name'] = name
        return res

    @api.multi
    def write(self, vals):
        res = super(GoodsInvoice, self).write(vals)
        return res


    def action_draft(self):
        return self.write({'state':'draft'})

    def action_waiting(self):
        if len(self.invoice_line_ids) < 1:
            raise UserError(_("Warning, not allowed to empty data: Invoice Detail."))
        
        # update state tracking
        self._set_state_tracking()
        return self.write({'state':'waiting'})

    def action_logistic(self):
        return self.write({'state':'logistic'})

    def action_done(self):
        return self.write({'state':'done'})
    
    def action_cancel(self):
        return self.write({'state':'cancelled'})


    @api.depends('invoice_line_ids','invoice_line_ids.boxes_qty','invoice_line_ids.gross_lb','invoice_line_ids.gross_kg')
    def _compute_total(self):
        for rec in self:
            rec.total_boxes_qty = sum(rec.invoice_line_ids.mapped('boxes_qty'))
            rec.total_gross_lb = sum(rec.invoice_line_ids.mapped('gross_lb'))
            rec.total_gross_kg = sum(rec.invoice_line_ids.mapped('gross_kg'))

    @api.depends('invoice_line_ids','invoice_line_ids.commercial_invoice_id')
    def depends_invoice_line_ids(self):
        self.goods_detail_ids = False
        ids = []
        for rec in self.invoice_line_ids:
            if self.invoice_id.pickup_ids:
                pickup_ids = self.invoice_id.pickup_ids.filtered(lambda r: r.load_code == rec.commercial_invoice_id.name)
                ids += pickup_ids.ids
        
        self.goods_detail_ids = list(set(ids))

    @api.depends('goods_detail_ids')
    def depends_goods_detail_ids(self):
        ids = []
        for rec in self.goods_detail_ids.filtered(lambda r: r.is_lartas == True):
            ids += self.env['report.survey'].search([('purchase_order_line_id','=',rec.purchase_order_line_id.id),('load_code','=',rec.load_code)]).ids

        self.survey_ids = list(set(ids))


    @api.multi
    def awb_bl_view(self):
        self.ensure_one()
        awb_bl_ids = self.env['awb.bl'].sudo().search([])
        ids = []
        for rec in awb_bl_ids:
            for awbbl in rec.awb_bl_ids:
                if awbbl.id == self.id:
                    ids.append(rec.id)

        domain = [('id', 'in', ids)]
        views = [(self.env.ref('ati_pti_shipment_tracking.awb_bl_tree2').id,'tree'),(self.env.ref('ati_pti_shipment_tracking.awb_bl_form2').id,'form')]
        return {
            'name': ('AWB/BL'),
            'domain': domain,
            'res_model': 'awb.bl',
            'type': 'ir.actions.act_window',
            # 'view_id': view_id,
            'views': views,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'help': ('''<p class="oe_view_nocontent_create">
                           Click to Create for New AWB/BL
                        </p>'''),
            'limit': 80,
            # 'context': "{'default_awb_bl_id': %s}" % (self.id)
        }

    # define state tracking
    def _set_state_tracking(self):
        for rec in self.goods_detail_ids:
            rec.state_tracking = 'at_forwarder_wh'
    

class GoodsInvoiceLine(models.Model):
    _name = 'goods.invoice.line'
    _description = "Pickup Goods Invoice Line"
    _order = 'id asc'


    # name = fields.Char(string='Invoice No.')
    commercial_invoice_id = fields.Many2one('commercial.invoice', string='Commercial Invoice No.')
    invoice_line_id = fields.Many2one('goods.invoice', string='Invoice Detail Line', ondelete='cascade')
    date = fields.Date(string='Invoice Date', default=fields.Datetime.now)
    purchase_id = fields.Many2one('purchase.order', string='PO Number', store=True)
    transaction_method_id = fields.Many2one('transaction.method', related='purchase_id.sale_id.transaction_method_id', string='Transaction')
    transaction_method_name = fields.Char(related='transaction_method_id.name',string='Transaction Method')
    partner_ref = fields.Char(string='Internal Reference (SP#)') 
    customer_partner_ref = fields.Char(string='Customer Reference (Customer PO#)') 
    boxes_qty = fields.Float(string='Boxes Qty')
    gross_lb = fields.Float(string='Gross Weight (Lbs)')
    gross_kg = fields.Float(string='Gross Weight (Kg)')
    # # product_uom = fields.Many2one('product.uom', string='UOM')
    # currency_id  = fields.Many2one('res.currency', string='Currency')
    # unit_price = fields.Monetary(string='Unit Price')


    @api.constrains('boxes_qty','gross_lb','gross_kg')
    def Validate_invoice(self):
        for rec in self:
            if rec.boxes_qty <= 0 and rec.gross_lb <= 0 and rec.gross_kg <= 0:
                raise UserError(_("Warning, Boxes Qty or Weight must greater than zero(0)."))


    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id,'%s%s%s' % (rec.commercial_invoice_id.name if rec.commercial_invoice_id else '', '/'+rec.partner_ref if rec.partner_ref else '', '/'+rec.customer_partner_ref if rec.customer_partner_ref else '')))
        return res

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        domain = args + ['|', ('commercial_invoice_id.name', operator, name), ('partner_ref', operator, name)]
        return super(GoodsInvoiceLine, self).search(domain, limit=limit).name_get()


    @api.onchange('commercial_invoice_id')
    def onchange_commercial_invoice_id(self):
        for wj in self:
            if len([wj_exist for wj_exist in wj.invoice_line_id.invoice_line_ids.mapped('commercial_invoice_id.name') if wj_exist == wj.commercial_invoice_id.name]) > 1:
                raise UserError(_("Warning, Commercial Invoice/WJ# must be unique."))

        for rec in self:
            if rec.commercial_invoice_id:
                rec.commercial_invoice_id.write({'pickup_goods_id': rec.invoice_line_id and rec.invoice_line_id.invoice_id.id or False})
            else:
                rec.commercial_invoice_id.write({'pickup_goods_id': rec.invoice_line_id and rec.invoice_line_id.invoice_id.id or False})

            rec.partner_ref = rec.commercial_invoice_id.purchase_id.partner_ref or '' 
            rec.customer_partner_ref = rec.commercial_invoice_id.purchase_id.x_client_order_ref or ''
            # print('----rec', rec, rec.commercial_invoice_id.name)

    # @api.depend('transaction_method_id')
    # def get_transaction_method_


class ReportSurvey(models.Model):
    _name = 'report.survey'
    _description = "Report Survey"
    _order = 'id asc'


    name = fields.Char(string='Description')
    sequence = fields.Integer(string='Sequence')
    date = fields.Date(string='Survey Date')
    # survey_id = fields.Many2one('goods.invoice', string='Survey Detail', ondelete='cascade')
    survey_id = fields.Many2one('goods.invoice', string='Survey Detail')
    purchase_order_line_id = fields.Many2one('purchase.order.line', string='Purchase Order Line')
    product_id = fields.Many2one('product.product', related='purchase_order_line_id.product_id', string='Product')
    purchase_id = fields.Many2one('purchase.order', related='purchase_order_line_id.order_id',string='PO Number')
    load_code = fields.Char(string='Load Code', related='purchase_order_line_id.load_code')
    partner_ref = fields.Char(string='Vendor Reference', related='purchase_order_line_id.partner_ref')
    doc_survey = fields.Binary(string='Attachment')



    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id,'%s%s' % (rec.load_code if rec.load_code else '', '/'+rec.product_id.name if rec.product_id else '')))
        return res

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        domain = args + ['|', ('load_code', operator, name), ('product_id.name', operator, name)]
        return super(ReportSurvey, self).search(domain, limit=limit).name_get()



