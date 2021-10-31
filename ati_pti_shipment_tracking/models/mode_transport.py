# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons import decimal_precision as dp


class ModeTransport(models.Model):
    _name = 'mode.transport'
    _description = "Mode Transport"
    _order = 'id asc'


    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id,'%s' % (rec.name)))
        return res


