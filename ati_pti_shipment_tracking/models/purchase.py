# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons import decimal_precision as dp

_STATES_BEFORE_CO = [
    ("not_ready", "Not Ready"),
    ("ready", "Ready To Collect"),
]


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    
    picked_qty = fields.Float(string='Picked Up Qty', digits=dp.get_precision('Product Unit of Measure'))
    buffer_qty = fields.Float(string='OS Qty', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_pol_buffer_qty')
    # product_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)
    load_code = fields.Char(string='LOAD CODE/WJ')
    nor_date = fields.Date('NOR DATE')
    pickup_id = fields.Many2one('pickup.goods', string="Collect Goods", copy=False)
    partner_ref = fields.Char(string='SP Number',related='order_id.partner_ref', store=True)
    customer_partner = fields.Char(related='order_id.sale_id.partner_id.name', string='Customer')
    sales_channel = fields.Char(related='order_id.sale_id.team_id.name', string='Sales Channel')
    transaction_method = fields.Char(related='order_id.sale_id.transaction_method_id.name', string='Transaction Method')
    skep_pib_id = fields.Many2one('skep.pib', string='SKEP')
    state_before_co = fields.Selection(selection=_STATES_BEFORE_CO,string="Status Ready",index=True,track_visibility="onchange",copy=False,default="not_ready")


    @api.depends('product_qty','buffer_qty')
    def _compute_pol_buffer_qty(self):
        for rec in self:
            rec.buffer_qty = rec.product_qty - rec.picked_qty


    def _check_goods_readiness(self):
        pol = self.env['purchase.order.line'].sudo().search([('state_before_co','=','not_ready'),('rts_date','!=',False)])
        today = fields.Datetime.now()
        for line in pol:
            if line.rts_date and line.rts_date <= today:
                line.state_before_co = 'ready'




