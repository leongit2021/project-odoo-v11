from odoo import fields, models, api, _
from datetime import date, datetime
from odoo.exceptions import UserError
 

class AccountGLByRangeWizard(models.TransientModel):
    _inherit = "account.finglreport.wizard"


    account_id_from = fields.Many2one('account.account', string='Account From',help="Search account from .")
    account_id_to = fields.Many2one('account.account', string='Account To',help="Search account to .")
    is_range = fields.Boolean(string="Is By Range?")
    filter = fields.Selection([
        ('no', 'No Filter'),
        ('account', 'By Account'),
        ('account_group', 'By Account Group'),
        ('journal', 'By Journal'),
    ], 'Filter', default='no', required=True)


    @api.onchange('account_id_from','account_id_to','is_range','filter')
    def onchange_by_range(self):
        account_obj = self.env['account.account'].sudo().search([])
        for rec in self:
            if not rec.is_range:
                rec.account_ids = False
                return {}
            if rec.filter != 'account':
                rec.is_range = False
                rec.account_ids = False
                rec.account_id_to = False

            rec.account_ids = False
            if rec.account_id_from and rec.account_id_to:
                if int(rec.account_id_from.code) >= int(rec.account_id_to.code):
                    raise UserError(_("You can not allowed Account From code greater than or equal to Account To code."))

                data = account_obj.filtered(lambda r: int(r.code) >= int(rec.account_id_from.code) and int(r.code) <= int(rec.account_id_to.code))
                if data:
                    rec.account_ids = data.ids


        # USD = self.env['res.currency'].search([('name', '=', 'USD')])
        # IDR = self.env['res.currency'].search([('name', '=', 'IDR')])
        # print('-----1',IDR.compute(78342972251, USD))
        # print('-----2',IDR.compute(86150904729, USD))
        # print('-----3',USD.compute(1, IDR)) # 1 USD = 15597.0 IDR







    