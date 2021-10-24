# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError
from odoo.addons import decimal_precision as dp


class ListShippingInstruction(models.TransientModel):
    _name           = "list.shipping.instruction.wiz"
    _description    = "List Shipping Instruction"


    pickup_id = fields.Many2one('pickup.goods', string='Collect Order', default=lambda self: self.env.context.get('active_id'))
    invoice_id = fields.Many2one('goods.invoice', string='Shipping Instruction')
    instruction_ids = fields.One2many('list.shipping.instruction.line.wiz','instruction_id', string='Shipping Instruction')
    survey_ids = fields.One2many('survey.wiz','survey_id', string='Survey')
    partner_id = fields.Many2one('res.partner', string='Forwarder',  change_default=True, track_visibility='always')
    mode_transport = fields.Many2one('mode.transport', string='Mode Of Transport')
    departure = fields.Many2one('departure.arrival',string='Departure')
    arrival = fields.Many2one('departure.arrival',string='Arrival')


    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        active_id = self.env.context.get('active_id')
        pickup = self.env['pickup.goods'].sudo().browse(active_id)
        self.invoice_id = False
        self.instruction_ids, self.survey_ids = False, False
        vals_instruction, vals_survey = [], []
        for rec in pickup.invoice_ids.browse(max(pickup.invoice_ids.mapped('id'))):
            self.invoice_id = rec.id or False
            self.partner_id = rec.partner_id.id or False
            self.mode_transport = rec.mode_transport.id or False
            self.departure = rec.departure.id or False
            self.arrival = rec.arrival.id or False
            for inv in rec.invoice_line_ids:
                val_instruction = {
                    'commercial_invoice_id'  : inv.commercial_invoice_id.id,
                    'date': inv.date or False,
                    'purchase_id'  : inv.commercial_invoice_id.purchase_id.id,
                    'partner_ref' : inv.commercial_invoice_id.purchase_id.partner_ref,
                    'customer_partner_ref' : inv.commercial_invoice_id.purchase_id.x_client_order_ref,
                    'boxes_qty' : inv.boxes_qty,
                    'gross_lb'  : inv.gross_lb,
                    'gross_kg'   : inv.gross_kg,
                    }

                vals_instruction.append((0,0,val_instruction))

            for survey in rec.survey_ids:
                val_survey = {
                    'name'  : survey.name or '',
                    'sequence': survey.sequence or 0,
                    'date'  : survey.date or False,
                    'purchase_order_line_id' : survey.purchase_order_line_id.id or False,
                    'doc_survey' : survey.doc_survey,
                    }

                vals_survey.append((0,0,val_survey))

            # 
        self.instruction_ids = vals_instruction
        self.survey_ids = vals_survey


    @api.onchange('departure','arrival')
    def _warning_origin_destination(self):
        for rec in self:
            if rec.departure and rec.arrival and rec.departure.id == rec.arrival.id:
                raise UserError(_("Can not the same Departure and Arrival."))


    def set_shipping_instruction(self):
        shipping = self.env['goods.invoice'].sudo()
        vals = {
            'invoice_id': self.pickup_id.id or False,
            'partner_id': self.partner_id.id or False,
            'mode_transport': self.mode_transport.id or False,
            'departure': self.departure.id or False,
            'arrival': self.arrival.id or False,
            'invoice_line_ids': [(0,0,{'commercial_invoice_id': inv.commercial_invoice_id.id or False,'purchase_id': inv.purchase_id.id or False,'partner_ref': inv.partner_ref or '','customer_partner_ref': inv.customer_partner_ref or '', 'boxes_qty': inv.boxes_qty,'gross_lb': inv.gross_lb,'gross_lb': inv.gross_lb,'gross_kg': inv.gross_kg}) for inv in self.instruction_ids],
            'survey_ids': [(0,0,{'sequence': s.sequence,'name': s.name or '','purchase_order_line_id': s.purchase_order_line_id.id or False,'doc_survey': s.doc_survey}) for s in self.survey_ids],
        }

        shipping |= shipping.create(vals)

        return {}



class ListShippingInstructionLineWiz(models.TransientModel):
    _name           = "list.shipping.instruction.line.wiz"
    _description    = "List Shipping Instruction Detail"


    instruction_id = fields.Many2one('list.shipping.instruction.wiz', string='List Shipping Instruction', ondelete='cascade')
    commercial_invoice_id = fields.Many2one('commercial.invoice', string='Commercial Invoice No.')
    date = fields.Date(string='Invoice Date', default=fields.Datetime.now)
    purchase_id = fields.Many2one('purchase.order', string='PO Number', store=True)
    partner_ref = fields.Char(string='Internal Reference (SP#)') 
    customer_partner_ref = fields.Char(string='Customer Reference (Customer PO#)') 
    boxes_qty = fields.Float(string='Boxes Qty')
    gross_lb = fields.Float(string='Gross Weight (Lbs)')
    gross_kg = fields.Float(string='Gross Weight (Kg)')


class SurveyWiz(models.TransientModel):
    _name = 'survey.wiz'
    _description = 'Survey'


    name = fields.Char(string='Description')
    survey_id = fields.Many2one('list.shipping.instruction.wiz', string='Survey Detail', ondelete='cascade')
    sequence = fields.Integer(string='Sequence')
    date = fields.Date(string='Survey Date')
    purchase_order_line_id = fields.Many2one('purchase.order.line', string='Purchase Order Line')
    product_id = fields.Many2one('product.product', related='purchase_order_line_id.product_id', string='Product')
    purchase_id = fields.Many2one('purchase.order', related='purchase_order_line_id.order_id',string='PO Number')
    load_code = fields.Char(string='LOAD CODE/WJ', related='purchase_order_line_id.load_code')
    partner_ref = fields.Char(string='SP Number', related='purchase_order_line_id.partner_ref')
    doc_survey = fields.Binary(string='Attachment')
