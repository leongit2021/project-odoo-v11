# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError
from odoo.addons import decimal_precision as dp


class NorValidateWiz(models.TransientModel):
    _name           = "nor.validate.wizard"
    _description    = "NOR Validate"


    nor_goods_id = fields.Many2one('nor.goods', string='NOR', default= lambda self: self.env.context.get('active_id')) 
    nor_ids = fields.One2many('nor.validate.wizard.line','nor_id', string='NOR')


    @api.model
    def default_get(self,fields):
        active_id = self.env.context.get('active_id')
        nor_goods = self.env['nor.goods'].sudo().browse(active_id)
        vals = []
        for valid in nor_goods.goods_ids.sorted(key=lambda r: r.sequence):
            nor = self.env['summary.nor.goods'].sudo().search([('sales_order_no','=',valid.sales_order_no),
                                                                ('item_code','=',valid.item_code),
                                                                ('position','=',valid.position),
                                                                ('initial_qty','!=',valid.nor_qty),
                                                                ('initial_qty','!=',0)
                                                                ],limit=1)
            if nor:
                val = {
                        'goods_id'  : valid.id,
                        'purchase_id': valid.purchase_id.id,
                        'sequence'  : valid.sequence,
                        'sales_order_no' : valid.sales_order_no,
                        'load_code' : valid.load_code,
                        'item_code' : valid.item_code,
                        'position'  : valid.position,
                        'nor_qty'   : valid.nor_qty,
                        'initial_qty' : nor.initial_qty,
                        'product_uom' : valid.product_uom,
                        }

                vals.append((0,0,val))

        result      = super(NorValidateWiz, self).default_get(fields)
        result['nor_ids'] = vals
        return result


    def validate(self):
        new_summary = self.env['summary.nor.goods'].sudo()
        for rec in self.nor_goods_id.goods_ids:
            if rec.sales_order_no == '' and rec.item_code == '':
                continue

            summary = self.env['summary.nor.goods'].sudo().search([
                                                                ('sales_order_no','=',rec.sales_order_no),
                                                                ('item_code','=',rec.item_code),
                                                                ('position','=',rec.position)
                                                                ])

            purchase_order_line = self.env['purchase.order.line'].sudo().search([
                                                                                ('order_id','=',rec.purchase_id.id),
                                                                                ('sequence','=',rec.position),
                                                                                ('product_id','=',rec.product_id.id),
                                                                                ], limit=1)
            # update purchase order line: wj
            purchase_order_line.write({'load_code':rec.load_code, 'nor_date':rec.nor_date})

            # update summary nor goods
            # update initial qty
            valid_nor_id = self.nor_ids.filtered(lambda r: r.goods_id.id == rec.id)
            val = {
                'purchase_id': rec.purchase_id and rec.purchase_id.id if rec.purchase_id else False,
                'product_id': rec.product_id and rec.product_id.id if rec.product_id else False,
                'item_desc': rec.item_desc or '',
                'initial_qty': rec.nor_qty if not valid_nor_id else valid_nor_id.nor_qty,
                'nor_qty': rec.nor_qty or 0,
                # 'buffer_qty': rec.nor_qty or 0,
                'product_uom': rec.product_uom or '',
                'currency_id': rec.currency_id or False,
                'sales_value': rec.sales_value or 0,
                'staged_dt': rec.staged_dt or False,
                'today': rec.today or False,
                'days_staged': rec.days_staged or 0,
                'load_code': rec.load_code or '',
                'nor_state': rec.nor_state or '',
                'nor_date': rec.nor_date or False,
                'nor_comment': rec.nor_comment or '',
            }
            # 
            if not summary:
                val.update({
                    'sales_order_no': rec.sales_order_no or '',
                    'position': rec.position or 0,
                    'item_code': rec.item_code or '',
                })
                new_summary |= new_summary.create(val)
            else:
                summary.write(val)

        return self.write({'state':'validate'})


class NorValidateLineWiz(models.TransientModel):
    _name           = "nor.validate.wizard.line"
    _description    = "List NOR"


    nor_id = fields.Many2one('nor.validate.wizard', string='List NOR', ondelete='cascade')
    goods_id = fields.Many2one('nor.goods.line', string='NOR Detail')
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order') 
    sequence = fields.Integer('Sequence')
    sales_order_no = fields.Char(string='SP Number')
    load_code = fields.Char(string='LOAD CODE')   
    item_code = fields.Char(string='Item Code')
    position = fields.Integer(string='Line')
    nor_qty     = fields.Float(string='Qty NOR', digits=dp.get_precision('Product Unit of Measure'))
    initial_qty     = fields.Float(string='Initial Qty', digits=dp.get_precision('Product Unit of Measure'))
    product_uom = fields.Char(string='UOM')
    


    @api.onchange('nor_qty')
    def onchange_nor_qty(self):
        for rec in self:
            if rec.nor_qty < 0:
                raise UserError(_("Not allowed: the Qty NOR less than zero(0)."))

            if rec.purchase_id:
                limit_purchase_order_line_qty = sum(rec.purchase_id.order_line.filtered(lambda r: r.product_id.default_code == rec.item_code and r.sequence == rec.position).mapped('product_qty'))
                if  limit_purchase_order_line_qty > 0 and limit_purchase_order_line_qty < rec.nor_qty:
                    raise UserError(_("Not allowed: the purchase order line Quantity: %d less than Qty NOR: %d." %(limit_purchase_order_line_qty,rec.nor_qty)))

