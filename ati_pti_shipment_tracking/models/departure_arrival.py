# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons import decimal_precision as dp


class DepartureArrival(models.Model):
    _name = 'departure.arrival'
    _description = "Departure/Arrival"
    _order = 'id asc'


    name = fields.Char(string='Port Name')
    code = fields.Char(string='Port Code')
    port_type = fields.Many2one('mode.transport', string='Port Type')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country')
    

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id,'%s%s' % (rec.code or '','-'+rec.city if rec.city else '')))
        return res

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        domain = args + ['|', ('name', operator, name), ('code', operator, name)]
        return super(DepartureArrival, self).search(domain, limit=limit).name_get()


    @api.onchange('country_id')
    def onchange_country(self):
        return {'domain': {'state_id': [('country_id','=',self.country_id.id)]}}


