# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time


class ShowSkepPib(models.TransientModel):
    _name           = "show.skep.pib.wizard"
    _description    = "Show Summary of SKEP/PIB"


    @api.model
    def _default_get(self):
        active_id = self.env.context.get('active_id')
        sol = self.env['sale.order.line'].browse(active_id)
        return self.env['skep.pib'].browse(sol.skep_pib_ids.ids).ids
    


    skep_pib_ids = fields.Many2many('skep.pib', string='SKEP/PIB', default=_default_get)


        
    
    