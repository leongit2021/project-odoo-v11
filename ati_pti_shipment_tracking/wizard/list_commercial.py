# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class ListCommercialWiz(models.TransientModel):
    _name           = "list.commercial.wizard"
    _description    = "List Commercial"

    instruction_id = fields.Many2one('goods.invoice', string='Shipping Instruction', default=lambda self: self.env.context.get('active_id'))
    commercial_invoice_ids = fields.Many2many('commercial.invoice', string="Commercial Invoice No.")


    @api.onchange('commercial_invoice_ids')
    def onchange_commercial_invoice_ids(self):
        instruction = self.env['goods.invoice'].sudo().browse(self.env.context.get('active_id'))
        commercial = self.env['commercial.invoice'].sudo().search([('pickup_goods_id','=',instruction.invoice_id.id)])
        ids = set(commercial.ids) - set(instruction.invoice_line_ids.mapped('commercial_invoice_id').ids)
        return {'domain':{'commercial_invoice_ids':[('id','in',list(ids))]}}
    

    def get_commercial(self):
        instruction_detail = self.env['goods.invoice.line'].sudo()
        for rec in self.commercial_invoice_ids:
            instruction_detail |= instruction_detail.sudo().create({
                'commercial_invoice_id': rec.id,
                'invoice_line_id': self.instruction_id.id,
                'partner_ref': rec.purchase_id.partner_ref or '',
                'customer_partner_ref': rec.purchase_id.x_client_order_ref or ''
            })

