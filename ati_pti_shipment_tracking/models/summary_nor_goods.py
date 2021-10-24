# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons import decimal_precision as dp

_NOR = [
    ("yes", "YES"),
    ("no", "NO"),
]


class SummaryNorGoods(models.Model):
    _name = 'summary.nor.goods'
    _description = "Summary NOR Goods Collect"
    _order = 'id asc'


    sales_order_no = fields.Char(string='SP Number')
    purchase_id = fields.Many2one('purchase.order',string='PO Number')
    position = fields.Integer(string='Position')
    product_id = fields.Many2one('product.product', string='Product')
    item_code = fields.Char(string='Item Code')
    item_desc = fields.Char(string='Item Description')
    nor_qty     = fields.Float(string='Qty NOR', digits=dp.get_precision('Product Unit of Measure'))
    pickup_qty     = fields.Float(string='Qty Picked Up', digits=dp.get_precision('Product Unit of Measure'))
    buffer_qty     = fields.Float(string='Qty Oustanding', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_buffer_qty')
    initial_qty     = fields.Float(string='Initial Qty', digits=dp.get_precision('Product Unit of Measure'))
    product_qty     = fields.Float(string='Product Qty', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_product_qty')
    remaining_product_qty     = fields.Float(string='Remaining Product Qty', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_product_qty')
    # product_uom = fields.Many2one('product.uom', string='UOM')
    product_uom = fields.Char(string='UOM')
    currency_id = fields.Many2one('res.currency', string='Currency')
    sales_value = fields.Monetary(string='Sales Value')
    staged_dt = fields.Date(string='STAGED DT')
    # today = fields.Date('Today', default=fields.Datetime.now)
    today = fields.Date('Today', compute='_get_today')
    days_staged = fields.Float(string='Days Qty')
    load_code = fields.Char(string='LOAD CODE')
    nor_state = fields.Selection(selection=_NOR,string='NOR')
    nor_date = fields.Date('NOR DATE')
    nor_comment = fields.Char(string='NOR COMMENT')

    @api.depends('today')
    def _get_today(self):
        for rec in self:
            rec.today = fields.Datetime.now()

    @api.depends('nor_qty','pickup_qty')
    def _compute_buffer_qty(self):
        for rec in self:
            rec.buffer_qty = rec.nor_qty - rec.pickup_qty

    @api.depends('purchase_id','product_id','product_qty','nor_qty')
    def _compute_product_qty(self):
        for rec in self:
            if rec.purchase_id and rec.product_id:
                rec.product_qty = sum(rec.purchase_id.order_line.sudo().filtered(lambda r: r.product_id.id == rec.product_id.id and r.sequence == rec.position).mapped('product_qty'))
                rec.remaining_product_qty = rec.product_qty - rec.nor_qty


    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id,'%s/%s' % (rec.load_code,rec.sales_order_no)))
        return res


    # overridden to allow searching both on model name (field 'model') and model
    # description (field 'name')
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        domain = args + ['|', ('sales_order_no', operator, name), ('load_code', operator, name)]
        return super(SummaryNorGoods, self).search(domain, limit=limit).name_get()

