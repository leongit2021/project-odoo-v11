# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError
from odoo.addons import decimal_precision as dp


class PackageNumberWiz(models.TransientModel):
    _name           = "package.number.wiz"
    _description    = "Package Number"


    goods_invoice_id = fields.Many2one('goods.invoice', string='Goods Invoice', default= lambda self: self.env.context.get('active_id'))
    packing_list_id = fields.Many2one('packing.list', string='Packing List No.')
    package_ids = fields.One2many('package.number.line.wiz','package_id', string='Package Number')


    @api.model
    def default_get(self,fields):
        active_id = self.env.context.get('active_id')
        goods_invoice = self.env['goods.invoice'].sudo().browse(active_id)
        vals = []
        for line in goods_invoice.invoice_line_ids.sorted(key=lambda r: r.sequence):
            val = {
                    'invoice_line_id'   : line.id or False,
                    'is_number'         : True,
                    'sequence'          : line.sequence or 0,
                    'product_id'        : line.product_id and line.product_id.id or False,
                    'packing_list_id'   : line.packing_list_id and line.packing_list_id.id or False,
                    'part_number'       : line.part_number or '',
                    'hts_number'        : line.hts_number or '',
                    'product_qty'       : line.product_qty or 0,
                    'product_uom'       : line.product_uom or '',
                    'currency_id'       : line.currency_id and line.currency_id.id or False,
                    'unit_price'        : line.unit_price or 0,
                    'extended_price'    : line.extended_price or 0,
                    }

            vals.append((0,0,val))

        result      = super(PackageNumberWiz, self).default_get(fields)
        result['package_ids'] = vals
        return result


    def set_number(self):
        for rec in self.package_ids:
            if rec.is_number:
                rec.invoice_line_id.write({'packing_list_id': self.packing_list_id and self.packing_list_id.id or False})
            
        return {}

class PackageNumberLineWiz(models.TransientModel):
    _name           = "package.number.line.wiz"
    _description    = "Package Number Detail"


    package_id = fields.Many2one('package.number.wiz', string='Package Number', ondelete='cascade')
    invoice_line_id = fields.Many2one('goods.invoice.line', string='Invoice Line')

    is_number = fields.Boolean('Numbered?', default=True)
    sequence = fields.Integer(string='Line')
    product_id = fields.Many2one('product.product', string='Product')
    packing_list_id = fields.Many2one('packing.list', string='Package Number')
    part_number = fields.Text(string='Part Number')
    hts_number = fields.Text(string='HTS Number')
    product_qty = fields.Text(string='QTY')
    # # product_uom = fields.Many2one('product.uom', string='UOM')
    product_uom = fields.Char(string='UOM')
    currency_id  = fields.Many2one('res.currency', string='Currency')
    unit_price = fields.Monetary(string='Unit Price')
    extended_price = fields.Monetary(string='Extended Price')    
    