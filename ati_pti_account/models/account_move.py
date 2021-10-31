# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'


    is_arrange = fields.Boolean(string='Arrange?', default=False)
    is_sequence_before = fields.Boolean(string='Is Sequence Before')
    

    def action_arrange(self):
        if not self.is_sequence_before:
            self.set_sequence_before()

        if not self.is_arrange:
            seq = 0
            xx = self.line_ids.filtered(lambda r: r.debit != 0)
            # debit and credit = 0
            existing_sequence = self.line_ids.filtered(lambda e: abs(e.debit) == abs(e.credit)).mapped('sequence_before') 
            for rec in self.line_ids.filtered(lambda r: r.debit != 0).sorted(key=lambda d: d.debit, reverse=True):
                for line in self.line_ids.filtered(lambda x: x.id == rec.id or abs(x.credit) == abs(rec.debit)).sorted(key=lambda s: s.debit, reverse=True):                
                    seq += 1
                    if seq in existing_sequence:
                        seq += 2
                    line.sequence = seq

            return self.write({'is_arrange': True})
        else:
            for r in self.line_ids.sorted(key=lambda r: r.debit, reverse=True):
                r.sequence = r.sequence_before

            return self.write({'is_arrange': False})


    def set_sequence_before(self):
        numb = 0
        for r in self.line_ids.sorted(key=lambda r: r.debit, reverse=True):
            numb += 1
            r.sequence_before = numb
            # update label: PO n SO
            if r.invoice_id.type == 'out_invoice' and r.account_id.id in r.invoice_id.invoice_line_ids.mapped('account_id').ids + r.invoice_id.account_id.ids:
                r.name = r.invoice_id.client_order_ref or r.invoice_id.name
            if r.invoice_id.type == 'in_invoice' and r.account_id.id in r.invoice_id.invoice_line_ids.mapped('account_id').ids + r.invoice_id.account_id.ids:
                r.name = r.invoice_id.name or ''


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'


    sequence = fields.Integer(string='Sequence')
    sequence_before = fields.Integer(string="Sequence Before")


    

