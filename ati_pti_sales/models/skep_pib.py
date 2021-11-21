# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError
import math


_STATES = [
    ("draft", "Draft"),
    # ("skep", "SKEP Progress"),
    ("pib", "PIB Progress"),
    ("done", "Done"),
    ("cancelled", "Cancelled"),
]


class SkepPib(models.Model):
    _name = 'skep.pib'
    _description = "SKEP"
    _order = 'id asc'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    skep_no = fields.Char(string='SKEP NO.', index=True, track_visibility='onchange')
    sale_id = fields.Many2one('sale.order', string='Quotation/Sales', copy=False)
    currency_rate = fields.Float(related='sale_id.currency_rate', string='Currency Rate', default=1, digits=0, readonly=True)
    # currency_rate = fields.Float(string='Currency Rate', default=1, digits=0, readonly=False)
    currency_id   = fields.Many2one(related='sale_id.currency_id', store=True, string='Currency', readonly=True)
    # currency_id   = fields.Many2one('res.currency', string='Currency', readonly=False)
    skep_date = fields.Date(string='SKEP Date')
    skep_recv_date = fields.Date(string='SKEP RECV DATE')
    skep_expiry_date = fields.Date(string='SKEP EXPIRY DATE')
    skep_ids = fields.One2many('skep.line','skep_id', string='SKEP')
    pib_ids = fields.One2many('pib.pib','pib_id', string='PIB')
    state = fields.Selection()
    state = fields.Selection(selection=_STATES,string="Status",index=True,track_visibility="onchange",copy=False,default="draft")

    is_select  = fields.Boolean('Select All/Not Select All ?', default=True)

    def action_draft(self):
        return self.write({'state':'draft'})

    # def action_skep(self):
    #     if len(self.skep_ids) < 1:
    #         raise UserError(_("Can not found SKEP detail."))
    #     for rec in self.sale_id.order_line:
    #         if rec.sequence2 in self.skep_ids.mapped('seq') and rec.product_id.id in self.skep_ids.mapped('product_id.id'):
    #             rec.write({'skep_pib_ids': [(4,self.id)]})
    #     return self.write({'state':'skep'})

    @api.multi
    def update_skep_lines(self):
        return {
            'name': _('Import SKEP Lines'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'update.import.skep.line',
            'target': 'new',
            'context': {
                'default_skep_id': self.ids[0],
            }
        }
    
    def action_pib(self):
        for rec in self.sale_id.order_line:
            if rec.sequence2 in self.skep_ids.mapped('seq') and rec.product_id.id in self.skep_ids.mapped('product_id.id'):
                rec.write({'skep_pib_ids': [(4,self.id)]})
        return self.write({'state':'pib'})

    def action_done(self):
        if len(self.pib_ids) < 1:
            raise UserError(_("Can not found PIB."))
            
        return self.write({'state':'done'})
    
    def action_cancel(self):
        for rec in self.sale_id.order_line:
            if rec.sequence2 in self.skep_ids.mapped('seq') and rec.product_id.id in self.skep_ids.mapped('product_id.id'):
                rec.write({'skep_pib_ids': [(3,self.id)]})
        return self.write({'state':'cancelled'})

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Can not deleted if state not draft."))
                
        return super(SkepPib, self).unlink()
    
    
    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id,'%s' % (rec.skep_no if rec.skep_no else '')))
        return res

    @api.constrains('skep_date','skep_recv_date')
    def _warning_complete(self):
        if self.skep_date and self.skep_recv_date:
            if self.skep_date > self.skep_recv_date:
                raise UserError(_("Not allowed SKEP DATE greater than SKEP RECV DATE."))

        if self.skep_date and self.skep_expiry_date:
            if self.skep_date > self.skep_expiry_date:
                raise UserError(_("Not allowed SKEP DATE greater than SKEP EXPIRY DATE."))

        if self.skep_recv_date and self.skep_expiry_date:  
            if self.skep_recv_date > self.skep_expiry_date:
                raise UserError(_("Not allowed SKEP RECV DATE greater than SKEP EXPIRY DATE."))
        
        if not self.skep_date and self.skep_recv_date:
            raise UserError(_("Not allowed SKEP DATE is Empty."))

    # @api.multi
    # def add_skep_item(self):
    #     pib_obj = self.env['pib.line'].sudo()
    #     for rec in self:
    #         if not rec.id:
    #             return {}

    #         for skep in rec.skep_ids:
    #             val = {'is_pib':False,
    #                     'pib_no_id':False,
    #                     'product_id':skep.product_id and skep.product_id.id or False,
    #                     'pib_id': rec.id}
    #             pib_obj |= pib_obj.create(val)

    #         if pib_obj:
    #             rec.write({'pib_ids': [(4,pib.id) for pib in pib_obj]})
    #     return {}


    @api.model
    def create(self, vals):
        res = super(SkepPib, self).create(vals)
        if res:
            for delete in res.skep_ids:
                if not delete.is_skep:
                    delete.unlink()
        return res

    @api.multi
    def write(self, vals):
        res = super(SkepPib, self).write(vals)
        for rec in self.skep_ids:
            if not rec.is_skep:
                rec.unlink()
        return res


    def _current_skep_qty(self, sol = False):
        current_skep = self.env['skep.pib'].sudo().search([('sale_id','=',self.sale_id.id),('state','not in',('draft','cancelled'))])
        current_qty = 0
        for rec in current_skep:
            current_qty +=  sum(rec.skep_ids.filtered(lambda r: r.seq == sol.sequence2 and r.product_id.id == sol.product_id.id).mapped('skep_qty'))

        return current_qty


    
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

    
    
    @api.onchange('sale_id')
    def onchange_sale_id(self):
        self.skep_ids = False
        vals = []
        seq_skep = 1
        for rec in self.sale_id.order_line.sorted(key=lambda r: r.sequence2):
            remaining_amount = rec.product_uom_qty - self._current_skep_qty(rec)
            if remaining_amount > 0:
                val = {
                        'is_skep': True,
                        'seq':rec.sequence2 or 0, 
                        'seq_skep': seq_skep, 
                        'product_id':rec.product_id.id or False,
                        'skep_qty':remaining_amount or 0,
                        # 'unit_skep_item_value':self._count_tkdn(rec)/rec.product_uom_qty if rec.product_uom_qty != 0 else 0
                        'unit_skep_item_value': rec.count_tkdn/rec.product_uom_qty if rec.product_uom_qty != 0 and rec.count_tkdn else 0,
                        'skep_item_value': self._round_up_two_decimal(num = rec.count_tkdn) if rec.currency_id.name in ('USD','Usd','usd') else self._round_up_two_decimal(num = rec.count_tkdn * self.currency_rate),
                        # 'skep_item_value': rec.count_tkdn,
                        }
                vals.append((0,0,val))
                seq_skep += 1

        self.skep_ids = vals

    

    @api.onchange('is_select')
    def onchange_is_select(self):
        if self.is_select:
            for rec in self.skep_ids:
                rec.is_skep = True
        else:
            for rec in self.skep_ids:
                rec.is_skep = False


    def _round_up_two_decimal(self, num=0):
        return math.ceil(num*100)/100



class SkepLine(models.Model):
    _name = 'skep.line'
    _description = "SKEP LINE"
    _order = 'id asc'


    skep_id = fields.Many2one('skep.pib', string='SKEP Item', ondelete='cascade')
    is_skep = fields.Boolean('Locked?', default=True)
    seq = fields.Integer(string='Sequence SO')
    seq_skep = fields.Integer(string='Sequence SKEP')
    product_id = fields.Many2one('product.product', string='Product')
    part_number = fields.Char(related='product_id.default_code', string='PN')
    skep_qty     = fields.Float(string='Qty SKEP')
    currency_id   = fields.Many2one(related='skep_id.currency_id', store=True, string='Currency', readonly=True)
    # currency_id   = fields.Many2one('res.currency', string='Currency', readonly=False)
    unit_skep_item_value = fields.Monetary(string='Unit SKEP Amount')
    skep_item_value = fields.Monetary(string='SKEP Amount', compute="")


    @api.onchange('skep_qty','unit_skep_item_value')
    def onchange_skep_qty(self):
        for rec in self:
            if rec.skep_id:
                sol = rec.skep_id.sale_id.order_line.filtered(lambda r: r.sequence2 == rec.seq and r.product_id.id == rec.product_id.id)
                remaining_qty = sum(sol.mapped('product_uom_qty')) - self._count_current_skep_qty(sol=sol)
                if rec.skep_qty <= 0 or rec.skep_qty > remaining_qty:
                    raise UserError(_("Not allowed QTY SKEP less than or equal zero (0) or greater than Qty Outstanding: %d." % (remaining_qty)))

                rec.skep_item_value = rec._round_up_two_decimal(num = rec.skep_qty * rec.unit_skep_item_value) if rec.currency_id.name in ('USD','Usd','usd') else rec._round_up_two_decimal(num = rec.skep_qty * rec.unit_skep_item_value * rec.skep_id.currency_rate)
                # rec.skep_item_value = rec.skep_qty * rec.unit_skep_item_value


    def _count_current_skep_qty(self, sol = False):
        current_skep = self.env['skep.pib'].sudo().search([('sale_id','=',self.skep_id.sale_id.id),('state','not in',('draft','cancelled'))])
        current_qty = 0
        for rec in current_skep:
            current_qty +=  sum(rec.skep_ids.filtered(lambda r: r.seq == sol.sequence2 and r.product_id.id == sol.product_id.id).mapped('skep_qty'))

        return current_qty
        

    @api.onchange('skep_item_value')
    def onchange_skep_item_value(self):
        for rec in self:
            if rec.skep_item_value <= 0:
                raise UserError(_("Not allowed SKEP Amount less than or equal zero (0) ."))

    @api.model
    def create(self, vals):
        res = super(SkepLine, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        res = super(SkepLine, self).write(vals)

        return res

    def _round_up_two_decimal(self, num=0):
        return math.ceil(num*100)/100


class PibPib(models.Model):
    _name = 'pib.pib'
    _description = "PIB"
    _order = 'id asc'

    pib_no = fields.Char(string='PIB NO', index=True, track_visibility='onchange')
    # is_pib = fields.Boolean('Locked?', default=True)
    pib_id = fields.Many2one('skep.pib', string='SKEP', ondelete='cascade', default=lambda self: self.env.context.get('active_id'))
    skep_no = fields.Char(string='SKEP NO', related='pib_id.skep_no')
    pib_date = fields.Date(string='PIB Date')
    pib_expiry_date = fields.Date(string='PIB EXPIRY DATE')
    pib_line_ids = fields.One2many('pib.line','pib_line_id', string='PIB Line')
    # currency_id   = fields.Many2one(related='pib_id.currency_id', store=True, string='Currency', readonly=True)
    currency_id   = fields.Many2one('res.currency', string='Currency', readonly=False)

    

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id,'%s' % (rec.pib_no if rec.pib_no else '')))
        return res


    def _current_pib_qty(self, skepline=False):
        current_pib_qty = 0
        for rec in self.pib_id.pib_ids:
            current_pib_qty += sum(rec.pib_line_ids.filtered(lambda r: r.seq == skepline.seq and r.product_id.id == skepline.product_id.id).mapped('pib_qty'))
        return current_pib_qty


    @api.onchange('pib_id')
    def onchange_pib_id(self):
        self.pib_line_ids = False
        vals = []
        seq_pib = 1
        for rec in self.pib_id.skep_ids:
            remaining_amount = rec.skep_qty - self._current_pib_qty(skepline=rec)
            if remaining_amount > 0:
                val = {
                        'is_pib_line': True,
                        'seq':rec.seq or 0, 
                        'seq_pib': seq_pib, 
                        'product_id':rec.product_id.id or False,
                        'reference_product_id': rec.product_id.id or False,
                        'pib_qty':remaining_amount or 0,
                        'reference_pib_qty': remaining_amount or 0,
                        'unit_pib_item_values':rec.unit_skep_item_value or 0,
                        # 'pib_item_values': remaining_amount * rec.unit_skep_item_value if rec.currency_id.name in ('USD','Usd','usd') else remaining_amount * rec.unit_skep_item_value * self.pib_id.currency_rate,
                        'pib_item_values': self._round_up_two_decimal(num=remaining_amount * rec.unit_skep_item_value),
                        }
                vals.append((0,0,val))
                seq_pib += 1

        self.pib_line_ids = vals

    
    def update_pib(self):
        # print('------update pib', self.pib_id)
        pass

    def _round_up_two_decimal(self, num=0):
        return math.ceil(num*100)/100



class PibLine(models.Model):
    _name = 'pib.line'
    _description = "PIB LINE"
    _order = 'id asc'


    pib_line_id = fields.Many2one('pib.pib', string='PIB Item Line', ondelete='cascade')
    is_pib_line = fields.Boolean('Locked?', default=True)
    seq  = fields.Integer(string='Sequence SO')
    seq_pib = fields.Integer(string='Sequence PIB')
    product_id = fields.Many2one('product.product', string='Product', compute='')
    reference_product_id = fields.Many2one('product.product', string='Product', compute='')
    part_number = fields.Char(related='product_id.default_code', string='PN')
    pib_qty     = fields.Float(string='Qty PIB')
    reference_pib_qty     = fields.Float(string='Qty PIB')
    currency_id         = fields.Many2one('res.currency', string='Currency')
    unit_pib_item_values = fields.Monetary(string='Unit PIB Amount')
    pib_item_values = fields.Monetary(string='PIB Amount', compute='')
    # currency_id   = fields.Many2one(related='pib_line_id.currency_id', store=True, string='Currency', readonly=True)

    
    # @api.depends('pib_qty','unit_pib_item_values')
    # def onchange_pib_tkdn(self):
    #     for rec in self:
    #         rec.pib_item_values = rec.pib_qty * rec.unit_pib_item_values


    @api.onchange('pib_qty','unit_pib_item_values')
    def onchange_pib_qty(self):
        for rec in self:
            if rec.pib_qty <= 0 or rec.pib_qty > rec.reference_pib_qty:
                raise UserError(_("Not allowed Qty PIB less than or equal zero (0) or greater than Qty Outstanding: %d." % (rec.reference_pib_qty)))

            if rec.unit_pib_item_values < 0:
                raise UserError(_("Not allowed Qty PIB less than or equal zero (0) ."))

            # rec.pib_item_values = rec.pib_qty * rec.unit_pib_item_values if rec.currency_id.name in ('USD','Usd','usd') else rec.pib_qty * rec.unit_pib_item_values * rec.pib_line_id.pib_id.currency_rate
            rec.pib_item_values = rec._round_up_two_decimal(num = rec.pib_qty * rec.unit_pib_item_values)

    @api.onchange('product_id')
    def onchange_product_id(self):
        for rec in self:
            if rec.product_id.id != rec.reference_product_id.id:
                raise UserError(_("Not allowed change PN: %s ." %(rec.reference_product_id and rec.reference_product_id.default_code or '')))


    @api.onchange('pib_item_values')
    def onchange_pib_item_values(self):
        for rec in self:
            if rec.pib_item_values <= 0:
                raise UserError(_("Not allowed PIB Amount less than or equal zero (0) ."))

    def _round_up_two_decimal(self, num=0):
        return math.ceil(num*100)/100


