# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError
import math



class HistoryReplacement(models.Model):
    _name = 'product.history.replacement'
    _description = "History Replacement"
    _order = 'id asc'

    # sequence = fields.Integer(string="No.")
    desc = fields.Text('Description')
    product_tmpl_id = fields.Many2one('product.template', string='Product', ondelete='cascade')
    default_code = fields.Char(string="PN", related='product_id.default_code')
    product_id = fields.Many2one('product.product', string='Product')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    is_replacement = fields.Boolean(string="Active?")


    @api.onchange('start_date','end_date')
    def _onchange_date(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                if rec.start_date > rec.end_date:
                    raise UserError(_("Not Allowed, Start Date greater than End Date."))



class ProductTemplate(models.Model):
    _inherit = 'product.template'


    history_replacement_ids = fields.One2many('product.history.replacement', 'product_tmpl_id', string="History Replacement")
   


