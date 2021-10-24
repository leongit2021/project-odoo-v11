# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time


class SalesDeliveryOrderWizard(models.TransientModel):
    _name           = "sales.delivery.order.wizard"
    _description    = "Sales Delivery Order"
    

    # so_ids = fields.Many2many('sale.order', string="Sales Order Group")
    crm_team_ids = fields.Many2many('crm.team', string="Sales Channels", default=lambda self: self.env['crm.team'].search([('name','like','21 - Sparepart')], limit=1).ids)
    date = fields.Date('Report as of', required=True, default=fields.Datetime.now)
    # selected
    is_choice_1 = fields.Boolean('0 - 14 Days', default=True)
    is_choice_2 = fields.Boolean('15 - 30 Days', default=True)
    is_choice_3 = fields.Boolean('31 - 60 Days', default=True)
    is_choice_4 = fields.Boolean('61 - 90 Days', default=True)
    is_choice_5 = fields.Boolean('> 90 Days', default=True)
    is_choice_6 = fields.Boolean('Overdue', default=True)
    is_done = fields.Boolean('Include Status Done')
    # range number
    range_1_from = fields.Integer(string='Range 1 From', default=0) 
    range_1_to = fields.Integer(string='Range 1 To', default=14) 
    range_2_from = fields.Integer(string='Range 2 From', default=15) 
    range_2_to = fields.Integer(string='Range 2 To', default=30) 
    range_3_from = fields.Integer(string='Range 3 From', default=31) 
    range_3_to = fields.Integer(string='Range 3 To', default=60) 
    range_4_from = fields.Integer(string='Range 4 From', default=61) 
    range_4_to = fields.Integer(string='Range 4 To',default=90) 
    range_5_from = fields.Integer(string='Range 5 From',default=90) 
    

    @api.multi
    def generate(self):
        return self.env.ref('ati_pti_sales.sales_due_delivery_xlsx').report_action(self.ids, config=False)