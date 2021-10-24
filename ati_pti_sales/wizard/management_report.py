# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError



class ManagementReportWizard(models.TransientModel):
    _name           = "management.report.wizard"
    _description    = "Management Report"
    
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    date_as = fields.Date('Reported as of', default=fields.Datetime.now)
    team_ids = fields.Many2one('crm.team', string='Sales Channel', default= lambda self: self.env['crm.team'].search([('name','like','21 - Sparepart')], limit=1))
    

    @api.constrains('date_from','data_to')
    def warning_date(self):
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise UserError(_("You can not allowed Date From is greater than Date To."))


    @api.multi
    def generate(self):
        return self.env.ref('ati_pti_sales.management_xlsx').report_action(self.ids, config=False)
 


