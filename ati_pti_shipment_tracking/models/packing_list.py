# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons import decimal_precision as dp

_TYPE = [
    ("yes", "YES"),
    ("no", "NO"),
]


class PackingList(models.Model):
    _name = 'packing.list'
    _description = "Packing List"
    _order = 'id asc'


    name = fields.Char(string='Packing List No.')
    code = fields.Char(string='Code')
    parent_id = fields.Many2one('packing.list',string='Parent')
    packing_list_type = fields.Many2one('packing.list.type',string='Type')
    

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id,'%s' % (rec.name)))
        return res


class PackingListType(models.Model):
    _name = 'packing.list.type'
    _description = "Packing List Type"
    _order = 'id asc'


    name = fields.Char(string='Type')
