# -*- coding: utf-8 -*-

from typing import Sequence
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class Stock(models.Model):
    _inherit = 'stock.picking'


    custom_clearance_id = fields.Many2one('custom.clearance', string='Custom Clearance')
    bc_two_eight_id = fields.Many2one('bc.two.eight', string='BC 2.8')
    sil_id = fields.Many2one('sil.sil', 'SIL')
    sequence = fields.Integer(string='Seq')
    sequence_ref =  fields.Integer(string='Sequence')
    

    
    @api.multi
    def button_validate(self):
        res = super(Stock, self).button_validate()
        # update state tracking
        for rec in self.custom_clearance_id.goods_detail_ids:
            rec.state_tracking = 'in_pti_warehouse'

        return res
    