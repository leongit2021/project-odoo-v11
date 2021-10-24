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
    ("awb", "AWB"),
    ("bl", "BL"),
]

_STATES = [
    ("draft", "Draft"),
    ("validate", "Validate"),
    ("done", "Done"),
]


class AwbBL(models.Model):
    _name = 'awb.bl'
    _description = "AWB/BL"
    _order = 'id asc'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']


    name = fields.Char(string='Number',track_visibility="onchange")
    bill_type = fields.Selection(selection=_TYPE,string="Shipping Document",index=True,track_visibility="onchange",copy=False,default="awb")
    created_by = fields.Many2one('res.users','Created By', default=lambda self: self.env.user.id)
    awb_bl_ids = fields.Many2one('goods.invoice', string='Shipping Instruction')
    mode_transport = fields.Many2one('mode.transport', string='Mode Of Transport')
    partner_id = fields.Many2one('res.partner', string='Forwarder',  change_default=True, track_visibility='always')
    transporter = fields.Many2one('delivery.carrier', string='Transport Name')
    date = fields.Date(string='Date')
    awb_bl_line_ids = fields.One2many('awb.bl.line', 'awb_bl_line_id', string='AWB/BL')
    awb_transit_history_ids = fields.One2many('transit.history', 'awb_transit_history_id', string='Flight Info')
    bl_transit_history_ids = fields.One2many('transit.history', 'bl_transit_history_id', string='Voyage Info')
    document_ids = fields.One2many('awb.bl.document', 'document_id', string='Document Checklist')

    # 
    mawb = fields.Char(string='MAWB #')
    hawb = fields.Char(string='HAWB #')
    job_ref = fields.Char(string='Job Ref #')
    document_date = fields.Date(string='Document Date')
    number_of_boxes = fields.Float(string='Number of Boxes')
    currency_id = fields.Many2one('res.currency', string='Currency')
    total_amount = fields.Monetary(string='Invoice Total Amt', compute='_compute_total_amount')
    awb_gross_weight = fields.Float(string='Gross Weight')
    # awb_gross_uom_id = fields.Many2one('product.uom', string='UOM')
    chargeable_weight = fields.Float(string='Chargeable Weight')
    # changeable_uom_id = fields.Many2one('product.uom', string='UOM')
    #
    carrier_partner_id = fields.Many2one('res.partner', string='Forwarder',  change_default=True, track_visibility='always')
    bl_no = fields.Char(string='BL No')
    date_of_issue = fields.Date(string='Date of Issue')
    quantity_of_package = fields.Float(string='Quantity of Package')
    kind_of_package = fields.Char(string='Kind of Package')
    bl_gross_weight = fields.Float(string='Gross Weight')
    # bl_gross_uom_id = fields.Many2one('product.uom', string='UOM')
    measurement = fields.Float(string='Measurement')
    # measurement_uom_id = fields.Many2one('product.uom', string='UOM')
    # 
    state = fields.Selection(selection=_STATES,string="Status",index=True,track_visibility="onchange",copy=False,default="draft")



    @api.model
    def create(self, vals):
        res = super(AwbBL, self).create(vals)
        # name = self.env['ir.sequence'].next_by_code(self._name)
        date = fields.Datetime.from_string(fields.Datetime.now())
        existing = self.env['awb.bl'].sudo().search([('id','!=',res.id)])

        if res.bill_type == 'awb':
            number_list = [0]
            for rec in existing:
                if rec.name and rec.name[0:3] == 'AWB' and rec.name[0:6] != 'AWB-BL':
                    number_list.append(int(rec.name[-5:]))
            
            number = max(number_list) + 1
            new_number = '' 
            for n in range(5 - len(str(number))):
                new_number += '0'

            new_number += str(number)
            res['name'] = 'AWB-%s-%s' %(str(date.year)[-2:],new_number)

        if res.bill_type == 'bl':
            number_list = [0]
            for rec in existing:
                if rec.name and rec.name[0:2] == 'BL':
                    number_list.append(int(rec.name[-5:]))
            
            number = max(number_list) + 1
            new_number = '' 
            for n in range(5 - len(str(number))):
                new_number += '0'

            new_number += str(number)
            res['name'] = 'BL-%s-%s' %(str(date.year)[-2:],new_number)

        return res


    @api.model
    def default_get(self,fields):
        active_id = self.env.context.get('active_id')
        vals = []
        for line in self.env['goods.invoice'].sudo().browse(active_id).invoice_line_ids:
            val = {'box_id': line.id,'purchase_id':line.purchase_id.id}
            vals.append((0,0,val))

        result      = super(AwbBL, self).default_get(fields)
        result['awb_bl_line_ids'] = vals
        return result


    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id,'%s %s' % (rec.name,'('+ rec.awb_bl_ids.name +')' if rec.awb_bl_ids else '')))
        return res


    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        domain = args + ['|',('name', operator, name),('awb_bl_ids.name', operator, name)]
        return super(AwbBL, self).search(domain, limit=limit).name_get()

    
    def action_draft(self):
        return self.write({'state': 'draft'})

    def action_validate(self):
        # update state tracking
        self._set_state_tracking()
        return self.write({'state': 'validate'})

    def action_done(self):
        if len(self.awb_bl_line_ids) < 1:
            raise UserError(_("Not allowed. Invoice Detail is empty."))
        # update state tracking
        self._set_state_tracking()
        return self.write({'state': 'done'})

    # define state tracking
    def _set_state_tracking(self):
        if self.state == 'draft':
            if self.bill_type == 'awb':
                if self.awb_bl_ids.invoice_id.origin.id in (awb.departure.id for awb in self.awb_transit_history_ids): 
                    for rec in self.awb_bl_ids.goods_detail_ids:
                        rec.state_tracking = 'in_port_of_origin'
                else:
                    for rec in self.awb_bl_ids.goods_detail_ids:
                        rec.state_tracking = 'in_port_of_transit'
            
            elif self.bill_type == 'bl':
                if self.awb_bl_ids.invoice_id.origin.id in (bl.departure.id for bl in self.bl_transit_history_ids): 
                    for rec in self.awb_bl_ids.goods_detail_ids:
                        rec.state_tracking = 'in_port_of_origin'
                else:
                    for rec in self.awb_bl_ids.goods_detail_ids:
                        rec.state_tracking = 'in_port_of_transit'
            else:
                pass

        else:
            if self.bill_type == 'awb':
                if self.awb_bl_ids.invoice_id.destination.id in (awb.destination.id for awb in self.awb_transit_history_ids): 
                    for rec in self.awb_bl_ids.goods_detail_ids:
                        rec.state_tracking = 'arrived_in_dest'
                else:
                    for rec in self.awb_bl_ids.goods_detail_ids:
                        rec.state_tracking = 'in_port_of_transit'
            
            elif self.bill_type == 'bl':
                if self.awb_bl_ids.invoice_id.destination.id in (bl.destination.id for bl in self.bl_transit_history_ids): 
                    for rec in self.awb_bl_ids.goods_detail_ids:
                        rec.state_tracking = 'arrived_in_dest'
                else:
                    for rec in self.awb_bl_ids.goods_detail_ids:
                        rec.state_tracking = 'in_port_of_transit'
            else:
                pass


    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Can not deleted if state not draft."))
                
        return super(AwbBL, self).unlink()

    @api.depends('awb_bl_line_ids','awb_bl_line_ids.invoice')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.awb_bl_line_ids.mapped('invoice'))


    @api.onchange('awb_bl_ids')
    def _onchange_awb_bl_ids(self):
        for rec in self:
            rec.awb_bl_line_ids = [(5,0,0)]
            rec.partner_id = rec.awb_bl_ids.partner_id.id or False
            rec.mode_transport = rec.awb_bl_ids.mode_transport.id or False
            # fill invoice detail
            vals = []
            for line in rec.awb_bl_ids.invoice_line_ids:
                vals.append((0,0,{'box_id': line.id,'purchase_id': line.commercial_invoice_id.purchase_id.id}))
            rec.awb_bl_line_ids = vals
            


class AwbBLLine(models.Model):
    _name = 'awb.bl.line'
    _description = "AWB/BL Detail"
    _order = 'id asc'


    box_id      = fields.Many2one('goods.invoice.line', string='Load Code')
    box_number      = fields.Integer(string='Box')
    awb_bl_line_id  = fields.Many2one('awb.bl', string='AWB/BL Detail', ondelete='cascade')
    # shipping_instruction_id = fields.Many2one('goods.invoice', string='Shipping Instruction')
    purchase_id = fields.Many2one('purchase.order', string='PO')
    client_order_ref = fields.Char(related='purchase_id.sale_id.client_order_ref', string='PO#')
    # load_code   =  fields.Char('WJ#',related='purchase_id.partner_ref')
    pti_ref     = fields.Char(string='PTI REF#', compute='_compute_pti_ref')
    partner_ref = fields.Char(string='SP#', related='purchase_id.partner_ref')
    currency_id = fields.Many2one('res.currency', string='Currency')
    invoice     = fields.Monetary(string='Invoice Amt')
    gross_wt    = fields.Float(string='Gross Wt (L)')
    volume_wt   = fields.Float(string='Volume Wt (CuFt)')


    @api.onchange('box_id')
    def onchange_box_id(self):
        box_id = False
        for wj in self:
            if len([line_id.box_id.id for line_id in wj.awb_bl_line_id.awb_bl_line_ids if line_id.box_id.id == wj.box_id.id]) > 2:
                raise UserError(_("Not Allowed, Load Code must be unique."))


        for rec in self:
            rec.purchase_id = rec.box_id and rec.box_id.commercial_invoice_id and rec.box_id.commercial_invoice_id.purchase_id.id or False


    @api.depends('purchase_id','box_id')
    def _compute_pti_ref(self):
        for rec in self:
            rec.pti_ref = "%s%s" %(rec.purchase_id.sale_id.name if rec.purchase_id.sale_id else '', '('+rec.purchase_id.sale_id.transaction_method_id.name +')' if rec.purchase_id.sale_id.transaction_method_id else '')


class TransitHistory(models.Model):
    _name = 'transit.history'
    _description = "Transit History"
    _order = 'id asc'


    awb_transit_history_id  = fields.Many2one('awb.bl', string='Flight', ondelete='cascade')
    bl_transit_history_id  = fields.Many2one('awb.bl', string='Voyage', ondelete='cascade')
    carrier_name = fields.Char(string='Carrier')
    trasport_name = fields.Char(string='Transport Name')
    transport_number = fields.Char(string='Flight Number')
    departure = fields.Many2one('departure.arrival',string='Departure')
    destination = fields.Many2one('departure.arrival', string='Destination')
    final_destination = fields.Many2one('departure.arrival',string='Final Destination')
    departure_date = fields.Datetime(string='Departure', default=fields.Datetime.now) 
    arrival_date = fields.Datetime(string='Arrival') 
    remarks = fields.Text(string='Remarks')


    @api.onchange('departure_date','arrival_date')
    def onchange_etd_eta(self):
        for rec in self:
            if rec.arrival_date and rec.departure_date:
                if rec.arrival_date < rec.departure_date:
                    raise UserError(_("Not Allowed Arrival Date less than Departure Date."))


class DocumentChecklist(models.Model):
    _name = 'awb.bl.document'
    _description = "Document Checklist"
    _order = 'id asc'


    document_check_id  = fields.Many2one('document.checklist.type', string='Document Checklist')
    document_id  = fields.Many2one('awb.bl', string='Document Checklist', ondelete='cascade')
    remarks = fields.Char(string='Remarks/Subject')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    attachment = fields.Binary(string='Attachment')



class CommercialInvoice(models.Model):
    _name = 'commercial.invoice'
    _description = "Commercial Invoice No"
    _order = 'id asc'


    name = fields.Char(string='Commercial Invoice No.')
    pickup_goods_id = fields.Many2one('pickup.goods', string='Collection Order')
    purchase_id = fields.Many2one('purchase.order', string='PO#')


    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id,'%s' % (rec.name)))
        return res


    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        domain = args + [('name', operator, name)]
        return super(CommercialInvoice, self).search(domain, limit=limit).name_get()






