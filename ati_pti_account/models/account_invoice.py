# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'


    faktur_single_line_ids = fields.One2many('account.move.faktur.sl', 'invoice_id', string='Faktur Single Line')
    picking_ids = fields.Many2many('stock.picking', string='DO')
    


class AccountInvoiceFakturSl(models.Model):
    _name = 'account.move.faktur.sl'


    name = fields.Text(string='Description')
    invoice_id = fields.Many2one('account.invoice', string='Faktur Single Line',ondelete='cascade', index=True)
    currency_id = fields.Many2one('res.currency',string='Currency', store=True)
    amount_untaxed = fields.Monetary(string='Total',store=True)


    @api.onchange('name')
    def _get_total(self):
        if self.invoice_id:
            self.currency_id = self.invoice_id.currency_id and self.invoice_id.currency_id.id or False 
            self.amount_untaxed = self.invoice_id.amount_untaxed or 0

    

