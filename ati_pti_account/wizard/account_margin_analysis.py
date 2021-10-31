# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time


class AccountMarginAnalysisWizard(models.TransientModel):
    _name           = "account.margin.analysis.wizard"
    _description    = "Account Margin Analysis"
    
    name = fields.Char(string="Name", compute='get_file_name')
    date_from = fields.Date('Date From', required=True, default=fields.Datetime.now)
    date_to = fields.Date('Date To', required=True)
    project_ids = fields.Many2many("project.project",string="Projects")
    # partner_ids = fields.Many2many('res.partner', string='Customer', index=True)
    report_format = fields.Selection([
        ('summary', 'Summany'),
        ('detail', 'Detail'),
    ], string='Report Format', default='summary')
    is_manual_selected = fields.Boolean('Search any project in the date interval?')

    @api.constrains('date_from','data_to')
    def warning_date(self):
        if self.date_from >= self.date_to:
            raise UserError(_("You can not allowed Date From is greater than or equal to Date To."))

    def _get_aml(self):
        projects = self.env['project.project'].sudo()
        domain = [('date','>=',self.date_from),('date','<=',self.date_to)]
        aml_code_3_until_9 = self.env['account.move.line'].sudo().search(domain).filtered(lambda r: str(r.account_id.code[0]) in ('3','4','5','6') and r.move_id.state == 'posted')
        aml = aml_code_3_until_9.filtered(lambda a: str(a.account_id.code[0]) == '3' or str(a.account_id.code[:2]) in ('41','42') or str(a.account_id.code[:3]) == '526' or str(a.account_id.code[:3]) == '440' or str(a.account_id.code[:3]) == '441')
        # penjualan, hpp, penalty,b.angkot,asuransi
        projects |= aml.mapped('invoice_id').mapped('project_id')
        # project from analytic account, account: 451-458, 510-518,52,5**-6** 
        aml_analytic_account = aml.filtered(lambda a: str(a.account_id.code[:3]) in (str(c) for c in range(451,458)) or str(a.account_id.code[0]) in ('5','6'))
        project_by_karyawan = aml_analytic_account.mapped('analytic_account_id.project_ids')
        projects |= project_by_karyawan
        return projects.filtered(lambda r: r.name not in ('GENERAL','GEN','GENERA','General','Gen'))
    
    # @api.onchange('date_from','date_to')
    def onchange_date(self):
        self.project_ids = False
        if not self.date_from or not self.date_to:
            return {}
        self.project_ids = self._get_aml().ids or False
        # 
        # res = {}
        # res['domain'] = {'project_ids':[('id','in',self.project_ids.ids)]}
        # return res
    
    @api.onchange('is_manual_selected')
    def onchange_manual_selected(self):
        if not self.is_manual_selected:
            self.project_ids = False
        if self.date_from and self.date_to and self.is_manual_selected:
            self.onchange_date()

    @api.depends('report_format')
    def get_file_name(self):
        self.name = 'Detail Margin Analysis' if self.report_format == 'detail' else 'Summary Margin Analysis'  
        return self.name
    

    @api.multi
    def generate(self):
        return self.env.ref('ati_pti_account.margin_analysis_xlsx').report_action(self.ids, config=False)

 
