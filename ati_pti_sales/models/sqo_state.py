# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SalesQuotationOrderStatus(models.Model):
    _name = 'sqo.state'
    _description = "Sales Order Status"
    _order = 'sequence asc'

    name= fields.Char('Name')
    code= fields.Char('Code')
    sequence= fields.Integer('Sequence', default=5)
