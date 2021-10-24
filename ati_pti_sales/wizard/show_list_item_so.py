# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, AccessError
import math


class ShowListItemSOWizard(models.TransientModel):
    _name           = "show.item.so.wiz"
    _description    = "List Item Sales Order"


    skep_id = fields.Many2one('skep.pib', string='SKEP', default= lambda self: self.env.context.get('active_id'))
    order_ids = fields.One2many('show.item.so.line.wiz','item_id', string='Order Line')
    is_select = fields.Boolean('Select All/Not Select All?')
    

    @api.model
    def default_get(self,fields):
        active_id = self.env.context.get('active_id')
        skep = self.env['skep.pib'].browse(active_id)
        vals = []
        for line in skep.sale_id.order_line.sorted(key=lambda r: r.sequence2):
            val = {
                    'order_id'       : line.id or False,
                    'seq'            : line.sequence2 or 0,
                    'is_numbered'    : False,
                    'product_id'     : line.product_id and line.product_id.id or False,
                    'part_number'    : line.product_id and line.product_id.default_code or '',
                    'skep_pib_ids'   : [(6,0,line.skep_pib_ids.ids)],
                    'product_uom_qty': line.product_uom_qty or 0,
                    'outstanding_qty': self._get_outstanding_skep(line),
                    'product_uom'    : line.product_uom and line.product_uom.id or False,
                    'currency_id'    : line.currency_id and line.currency_id.id or False,
                    'price_unit'     : line.price_unit or 0,
                    # 'unit_skep_item_value'  : self._count_tkdn(sol=line)/line.product_uom_qty if line.product_uom_qty != 0 else 0,   
                    'unit_skep_item_value'  :  line.count_tkdn/line.product_uom_qty if line.product_uom_qty != 0 else 0,   
                    'count_tkdn'    : self._get_outstanding_skep(line) * line.count_tkdn/line.product_uom_qty if line.product_uom_qty != 0 else 0,
                    'price_subtotal' : line.price_subtotal or 0,
                    }
                    
            vals.append((0,0,val))

        result      = super(ShowListItemSOWizard, self).default_get(fields)
        result['order_ids'] = vals
        return result

    def _get_outstanding_skep(self,sol=False):
        skep_qty = 0
        if sol:
            for rec in self.env['skep.pib'].sudo().search([('sale_id','=',sol.order_id.id),('state','not in',('draft','cancelled'))]):
                skep_qty += sum(rec.skep_ids.filtered(lambda r: r.product_id.id == sol.product_id.id and r.seq == sol.sequence2).mapped('skep_qty'))

        return sol.product_uom_qty - skep_qty

    def _count_tkdn(self, sol=False):
        # 
        cust_group = sol.order_id.customer_group_id
        # exworks after dics
        exworks_after_disc,count_disc,count_tkdn = 0,0,0
        if cust_group.name in ('SKK','skk','Skk'):
            var_x = round((sol.product_id.standard_price * 10/100 * 100),2)
            exworks_after_disc = sol.product_id.standard_price - (math.ceil(var_x) / 100)
        elif cust_group.name in ('EXXON','Exxon','exxon'):
            var_y = round((sol.product_id.standard_price * 11.5/100 * 100),2)
            exworks_after_disc = sol.product_id.standard_price - (math.ceil(var_y) / 100)
        else :
            exworks_after_disc = sol.product_id.standard_price - 0.00
        
        # disc
        var_z = round((exworks_after_disc * 5/100 * 100),4)
        count_disc = (math.ceil(var_z) / 100)* sol.product_uom_qty
        # tkdn
        count_tkdn = sol.price_subtotal if sol.price_subtotal else 0 - count_disc if count_disc else 0

        return count_tkdn

    
    @api.onchange('is_select')
    def onchange_is_select(self):
        if self.is_select:
            for rec in self.order_ids:
                if rec.outstanding_qty != 0:
                    rec.is_numbered = True
        else:
            for rec in self.order_ids:
                rec.is_numbered = False


    @api.multi
    def set_number(self):
        skep_line = self.env['skep.line'].sudo()
        vals = []
        fix_skep = self.skep_id.skep_ids.filtered(lambda s: s.is_skep == True)
        update_skep = self.skep_id.skep_ids.filtered(lambda s: s.is_skep == False)
        seq_skep = max(self.skep_id.skep_ids.mapped('seq_skep'))
        for rec in self.order_ids.filtered(lambda r: r.is_numbered == True):
            if rec.seq not in fix_skep.mapped('seq') and rec.product_id.id not in fix_skep.mapped('product_id.id'):
                if rec.seq in update_skep.mapped('seq') and rec.product_id.id in update_skep.mapped('product_id.id'):
                    # update
                    new_update_skep = update_skep.filtered(lambda u: u.seq == rec.seq and u.product_id.id == rec.product_id.id)
                    new_update_skep.write({'is_skep': True,'skep_qty': rec.outstanding_qty,'skep_item_value': rec.outstanding_qty * rec.unit_skep_item_value})
                else:
                    # create 
                    seq_skep += 1
                    val = {
                            'skep_id': self.skep_id.id or False,
                            'is_skep': True,
                            'seq':rec.seq or 0, 
                            'seq_skep': seq_skep, 
                            'product_id':rec.product_id.id or False,
                            'skep_qty':rec.outstanding_qty or 0,
                            'unit_skep_item_value': rec.unit_skep_item_value or 0,
                            'skep_item_value':rec.outstanding_qty * rec.unit_skep_item_value or 0,
                            }
                    if val:
                        skep_line != skep_line.create(val)

        return {}

    
class ShowListItemSOLineWizard(models.TransientModel):
    _name           = "show.item.so.line.wiz"
    _description    = "Order Line"


    order_id            = fields.Many2one('sale.order.line', string='Sale Order Line')
    item_id             = fields.Many2one('show.item.so.wiz', string='Order', ondelete='cascade')
    seq                 = fields.Integer(string='Sequence SO')
    is_numbered         = fields.Boolean('Select?')
    product_id          = fields.Many2one('product.product', string='Product')
    part_number         = fields.Char(related='product_id.default_code', string='PN')
    skep_pib_ids        = fields.Many2many('skep.pib', string='SKEP/PIB')
    product_uom_qty     = fields.Float(string='Qty SO', digits=dp.get_precision('Product Unit of Measure'))
    outstanding_qty     = fields.Float(string='Outstanding SKEP', digits=dp.get_precision('Product Unit of Measure'), compute='')
    product_uom         = fields.Many2one('product.uom', string='Unit of Measure')
    currency_id         = fields.Many2one('res.currency', string='Currency')
    price_unit          = fields.Float('Unit Price', digits=dp.get_precision('Product Price'), default=0.0)
    unit_skep_item_value = fields.Monetary(string='Unit SKEP Amount') 
    count_tkdn          = fields.Monetary(string='SKEP Amount',compute='')
    price_subtotal      = fields.Monetary(string='Subtotal')



    @api.onchange('is_numbered')
    def onchange_is_numbered(self):
        for rec in self:
            if rec.outstanding_qty == 0:
                rec.is_numbered = False



