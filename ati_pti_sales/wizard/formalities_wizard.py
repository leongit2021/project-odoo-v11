# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, AccessError
import math


class FormalitiesWizard(models.TransientModel):
    _name           = "formalities.wiz"
    _description    = "Assignment of Formalities"


    sale_id = fields.Many2one('sale.order', string='Quotation/Sales', default= lambda self: self.env.context.get('active_id'))
    skep_pib_ids = fields.Many2one('skep.pib', string='SKEP')
    skep_date = fields.Date(string='SKEP Date')
    skep_recv_date = fields.Date(string='SKEP RECV DATE')
    skep_expiry_date = fields.Date(string='SKEP EXPIRY DATE')

    
    formalities_ids = fields.One2many('formalities.line.wiz','formalities_id', string='Formalities')
    skep_ids = fields.One2many('skep.line.wiz','skep_id', string='SKEP')
    pib_ids = fields.One2many('pib.line.wiz','pib_id', string='PIB')
    
    is_select = fields.Boolean('Select All/Not Select All?')
    is_add_skep = fields.Boolean('Add SKEP?')
    is_delete_skep = fields.Boolean('Delete All?')
    is_delete_pib = fields.Boolean('Delete ALL?')

    # pib_no = fields.Char(string='PIB NO')
    pib_id = fields.Many2one('pib.pib', string='PIB')
    skep_no = fields.Char(string='SKEP NO', related='pib_id.skep_no')
    pib_date = fields.Date(string='PIB Date')
    pib_expiry_date = fields.Date(string='PIB EXPIRY DATE')
    

    @api.model
    def default_get(self,fields):
        active_id = self.env.context.get('active_id')
        so = self.env['sale.order'].browse(active_id)
        vals = []
        for line in so.order_line.sorted(key=lambda r: r.sequence2):
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
                    'count_tkdn'     : self._count_tkdn(line),   
                    'price_subtotal' : line.price_subtotal or 0,
                    }
                    
            vals.append((0,0,val))

        result      = super(FormalitiesWizard, self).default_get(fields)
        result['formalities_ids'] = vals
        return result


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
        count_tkdn = sol.price_subtotal - count_disc

        return count_tkdn


    def _get_outstanding_skep(self,sol=False):
        skep_qty = 0
        if sol:
            for rec in sol.skep_pib_ids:
                skep_qty += sum(rec.skep_ids.filtered(lambda r: r.product_id.id == sol.product_id.id and r.seq == sol.sequence2).mapped('skep_qty'))

        return sol.product_uom_qty - skep_qty


    @api.onchange('formalities_ids','formalities_ids.is_numbered')
    def onchange_is_numbered(self):
        self.skep_ids = False
        # if self.skep_no and not self.skep_pib_ids:
        if self.skep_pib_ids and not self.skep_pib_ids.sale_id:
            vals = []
            seq_skep = 1
            for skep in self.formalities_ids.filtered(lambda r: r.is_numbered == True and r.outstanding_qty > 0).sorted(key=lambda s: s.seq):
                val = {'seq':skep.seq, 'seq_skep': seq_skep, 'product_id':skep.product_id.id or False,'skep_qty':skep.outstanding_qty or 0,'skep_item_value':skep.count_tkdn or 0}
                vals.append((0,0,val))
                seq_skep += 1
            self.skep_ids = vals

    
    @api.onchange('is_select')
    def onchange_is_select(self):
        self.skep_ids = False
        # if self.skep_no and not self.skep_pib_ids:
        if self.skep_pib_ids and not self.skep_pib_ids.sale_id:
            vals = []
            if self.is_select:
                for skep in self.formalities_ids.filtered(lambda r: r.outstanding_qty > 0).sorted(key=lambda s: s.seq):
                    skep.is_numbered = True
                    val = {'seq':skep.seq,'product_id':skep.product_id.id or False,'skep_qty':skep.outstanding_qty or 0,'skep_item_value':skep.count_tkdn or 0}
                    vals.append((0,0,val))
            else:
                for skep in self.formalities_ids.sorted(key=lambda s: s.seq):
                    skep.is_numbered = False
            self.skep_ids = vals
        

    @api.onchange('skep_pib_ids')
    def _get_skep_pib_line(self):
        skep_vals, pib_vals = [],[]
        self.skep_ids, self.pib_ids = False, False
        # reload skep
        for rec in self.skep_pib_ids:
            self.skep_date, self.skep_recv_date, self.skep_expiry_date = rec.skep_date or False, rec.skep_recv_date or False, rec.skep_expiry_date or False
            for skep in rec.skep_ids:
                skep_val = {
                    'seq'  : skep.seq or 0,
                    'seq_skep' : skep.seq_skep or 0,
                    'product_id': skep.product_id and skep.product_id.id or False,
                    'skep_qty' : skep.skep_qty or 0,
                    'skep_item_value': skep.skep_item_value or 0,
                }
                skep_vals.append((0,0,skep_val))

        self.skep_ids = skep_vals

    # reload pib
    @api.onchange('pib_id')
    def _get_pib_line(self):
        pib_vals = []
        self.pib_ids = False
        # reload pib
        for rec in self.pib_id:
            self.pib_date, self.pib_expiry_date = rec.pib_date or False, rec.pib_expiry_date or False
            for pib in rec.pib_line_ids:
                pib_val = {
                    'seq'  : pib.seq or 0,
                    'seq_pib': pib.seq_pib or 0,
                    'product_id': pib.product_id and pib.product_id.id or False,
                    'pib_qty': pib.pib_qty or 0,
                    'pib_item_values': pib.pib_item_values or 0,
                }
                pib_vals.append((0,0,pib_val))

        self.pib_ids = pib_vals
        

    # @api.multi
    def add_skep_item(self):
        pib_obj = self.env['pib.line.wiz'].sudo()
        # skep_current = [dict(is_pib = s.is_pib, pib_no_id=s.pib_no_id.id, seq = s.seq, product_id = s.product_id.id, skep_qty = s.skep_qty, skep_item_value = s.skep_item_value) for s in self.skep_pib_ids.skep_ids.sorted(key=lambda no: no.seq)]
        self.formalities_ids = False
        if self.skep_pib_ids:
            # reload
            self._get_skep_pib_line()
            vals = []
            seq_pib = 1
            for skep in self.skep_ids:
                current_qty = [sum(pibline.pib_line_ids.filtered(lambda r: r.seq == skep.seq and r.product_id.id == skep.product_id.id).mapped('pib_qty')) for pibline in self.skep_pib_ids.pib_ids]
                remaining_amount = skep.skep_qty - sum(current_qty)
                if remaining_amount > 0:
                    val = {
                            'seq'  : skep.seq or 0,
                            'seq_pib' : seq_pib,
                            'product_id':skep.product_id and skep.product_id.id or False,
                            'pib_qty':  remaining_amount or 0,
                            'pib_item_values': skep.skep_item_value or 0,
                            }
                    seq_pib += 1
                    pib_obj |= pib_obj.create(val)
        # else:
        #     vals = []
        #     for skep in self.skep_ids:
        #         remaining_amount = skep.skep_qty - sum(self.pib_ids.filtered(lambda r: r.seq == skep.seq and r.product_id.id == skep.product_id.id).mapped('pib_qty'))
        #         if remaining_amount > 0:
        #             val = {
        #                     'seq'  : skep.seq or 0,
        #                     'is_pib':False,
        #                     'product_id':skep.product_id and skep.product_id.id or False,
        #                     'pib_qty':  remaining_amount or 0,
        #                     'pib_item_values': skep.skep_item_value or 0,
        #                     }

        #             pib_obj |= pib_obj.create(val)
        
        if pib_obj:
            self.write({'pib_ids': [(4,pib.id) for pib in pib_obj]})
        
        vals_ol = []
        for line in self.sale_id.order_line.sorted(key=lambda r: r.sequence2):
            val_ol = {
                    'order_id'       : line.id or False,
                    'seq'           : line.sequence2 or 0,
                    'is_numbered'    : False,
                    'product_id'     : line.product_id and line.product_id.id or False,
                    'skep_pib_ids'   : [(6,0,line.skep_pib_ids.ids)],
                    'product_uom_qty': line.product_uom_qty or 0,
                    'outstanding_qty': self._get_outstanding_skep(line),
                    'product_uom'    : line.product_uom and line.product_uom.id or False,
                    'currency_id'    : line.currency_id and line.currency_id.id or False,
                    'price_unit'     : line.price_unit or 0,
                    'count_tkdn'     : self._count_tkdn(line),
                    'price_subtotal' : line.price_subtotal or 0,
                    }
                    
            vals_ol.append((0,0,val_ol))

        self.write({'formalities_ids': vals_ol})

        return {'type':'ir.actions.do_nothing'}


    @api.onchange('is_add_skep')
    def onchange_is_add_skep(self):
        pib_obj = self.env['pib.line.wiz'].sudo()
        if self.skep_pib_ids and self.is_add_skep:
            # reload
            # self._get_skep_pib_line()
            vals = []
            seq_pib = 1
            for skep in self.skep_ids:
                current_qty = [sum(pibline.pib_line_ids.filtered(lambda r: r.seq == skep.seq and r.product_id.id == skep.product_id.id).mapped('pib_qty')) for pibline in self.skep_pib_ids.pib_ids]
                remaining_amount = skep.skep_qty - sum(current_qty)
                print('-----remaining ', current_qty, remaining_amount)
                if remaining_amount > 0:
                    val = {
                            'seq'  : skep.seq or 0,
                            'seq_pib' : seq_pib,
                            'product_id':skep.product_id and skep.product_id.id or False,
                            'pib_qty':  remaining_amount or 0,
                            'pib_item_values': skep.skep_item_value or 0,
                            }
                    seq_pib += 1
                    vals.append((0,0,val))

            self.pib_ids = vals

    
    @api.onchange('is_delete_skep')
    def onchange_is_delete_skep(self):
        if self.is_delete_skep:
            self.skep_ids = False

    @api.onchange('is_delete_pib')
    def onchange_is_delete_pib(self):
        if self.is_delete_pib:
            self.pib_ids = False        

    @api.multi
    def set_number(self):
        if not self.skep_pib_ids:
            return {}
        # new skep/pib
        if self.skep_pib_ids and not self.skep_pib_ids.sale_id:
            skep_pib_obj = self.env['skep.pib'].sudo()
            pib_obj = self.env['pib.pib'].sudo()
            header_val = {
                'sale_id': self.sale_id.id or False,
                'skep_date': self.skep_date or False,
                'skep_recv_date': self.skep_recv_date or False,
                'skep_expiry_date': self.skep_expiry_date or False,
            }

            skep_vals = []
            for skep in self.skep_ids:
                skep_val = {
                    'seq'  : skep.seq or 0,
                    'seq_skep' : skep.seq_skep,
                    'product_id': skep.product_id and skep.product_id.id or False,
                    'skep_qty' : skep.skep_qty or 0,
                    'skep_item_value': skep.skep_item_value or 0,
                }
                skep_vals.append((0,0,skep_val))

            pib_vals = []
            for pib in self.pib_ids:
                pib_val = {
                    'seq'  : pib.seq or 0,
                    'seq_pib': pib.seq_pib, 
                    'product_id': pib.product_id and pib.product_id.id or '',
                    'pib_qty': pib.pib_qty or 0,
                    'pib_item_values': pib.pib_item_values or 0,
                }
                pib_vals.append((0,0,pib_val))
            # 
            # update pib
            self.pib_id.write({'pib_id': self.skep_pib_ids and self.skep_pib_ids.id, 'pib_date': self.pib_date or False, 'pib_expiry_date': self.pib_expiry_date or False})
            # 
            header_val.update(skep_ids=skep_vals)
            # 
            sol = self.sale_id.order_line.sorted(key=lambda r: r.sequence2)
            formalities = self.formalities_ids

            # 
            self.skep_pib_ids.write(header_val)
            # 
            # self.skep_pib_ids.write({'sale_id':self.sale_id and self.sale_id.id})
            # 
            reference_product, reference_sequence = self.skep_pib_ids.skep_ids.mapped('product_id.id'),self.skep_pib_ids.skep_ids.mapped('seq')
            for line in sol.sorted(key=lambda r: r.sequence2):
                if line.product_id.id in reference_product and line.sequence2 in reference_sequence:
                    line.write({'skep_pib_ids': [(4,self.skep_pib_ids.id)]})
        else:
            header_val = {
                'skep_date': self.skep_date or False,
                'skep_recv_date': self.skep_recv_date or False,
                'skep_expiry_date': self.skep_expiry_date or False,
            }
            self.skep_pib_ids.write(header_val)
            pib_obj = self.env['pib.line'].sudo()
            pib_vals = []
            for pib in self.pib_ids:
                pib_val = {
                    'seq'            : pib.seq or 0,
                    'seq_pib'        : pib.seq_pib or 0,
                    'pib_id'         : self.skep_pib_ids.id or False,
                    'product_id'     : pib.product_id and pib.product_id.id or False,
                    'pib_qty'        : pib.pib_qty or 0,
                    'pib_item_values': pib.pib_item_values or 0,
                }
                pib_vals.append((0,0,pib_val))
                # pib_obj |= pib_obj.create(pib_val)
            self.pib_id.write({'pib_date': self.pib_date or False, 'pib_expiry_date': self.pib_expiry_date or False, 'pib_line_ids':pib_vals, 'pib_id': self.skep_pib_ids and self.skep_pib_ids.id or False})
            #  for pib_update in self.skep_pib_ids:
            #      pib_update.write({'pib_ids': pib_vals})
            # pib_obj |= pib.create()

        return {}

            
    
class FormalitiesLineWizard(models.TransientModel):
    _name           = "formalities.line.wiz"
    _description    = "List of Formalities"


    order_id            = fields.Many2one('sale.order.line', string='Sale Order Line')
    formalities_id      = fields.Many2one('formalities.wiz', string='SKEP/PIB Lines', ondelete='cascade')
    seq                 = fields.Integer(string='Sequence SO')
    is_numbered         = fields.Boolean('Tick?')
    product_id          = fields.Many2one('product.product', string='Product')
    part_number         = fields.Char(related='product_id.default_code', string='PN')
    skep_pib_ids        = fields.Many2many('skep.pib', string='SKEP/PIB')
    product_uom_qty     = fields.Float(string='Qty SO', digits=dp.get_precision('Product Unit of Measure'))
    outstanding_qty     = fields.Float(string='Outstanding SKEP', digits=dp.get_precision('Product Unit of Measure'), compute='')
    product_uom         = fields.Many2one('product.uom', string='Unit of Measure')
    currency_id         = fields.Many2one('res.currency', string='Currency')
    price_unit          = fields.Float('Unit Price', digits=dp.get_precision('Product Price'), default=0.0)
    count_tkdn          = fields.Monetary(string='SKEP Amount')
    price_subtotal      = fields.Monetary(string='Subtotal')



class SkepLineWizard(models.TransientModel):
    _name = 'skep.line.wiz'
    _description = "SKEP LINE"


    skep_id         = fields.Many2one('formalities.wiz', string='SKEP Line', ondelete='cascade')
    seq       = fields.Integer(string='Sequence SO')
    seq_skep         = fields.Integer(string='Sequence SKEP')
    product_id      = fields.Many2one('product.product', string='Product')
    part_number     = fields.Char(related='product_id.default_code', string='PN')
    skep_qty        = fields.Float(string='Qty SKEP', digits=dp.get_precision('Product Unit of Measure'), store=True)
    skep_item_value = fields.Float(string='SKEP Amount')


    @api.onchange('skep_qty')
    def onchange_validate(self):
        for rec in self:
            reference = rec.skep_id.formalities_ids.filtered(lambda r: r.product_id.id == rec.product_id.id and r.seq == rec.seq)
            if rec.skep_qty > reference.outstanding_qty:
                rec.skep_qty = reference.outstanding_qty
    

class PibLineWizard(models.TransientModel):
    _name = 'pib.line.wiz'
    _description = "PIB LINE"


    pib_id = fields.Many2one('formalities.wiz', string='PIB Line', ondelete='cascade')
    seq = fields.Integer(string='Sequence SO')
    seq_pib         = fields.Integer(string='Sequence PIB')
    product_id = fields.Many2one('product.product', string='Product', compute='')
    part_number = fields.Char(related='product_id.default_code', string='PN')
    pib_qty     = fields.Float(string='Qty PIB', digits=dp.get_precision('Product Unit of Measure'), store=True)
    pib_item_values = fields.Float(string='PIB Amount')


    


