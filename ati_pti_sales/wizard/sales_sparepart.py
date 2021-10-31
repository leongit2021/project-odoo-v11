# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date, datetime, timedelta, time
from odoo.exceptions import Warning, UserError
from odoo.addons import decimal_precision as dp
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.base_import.models.base_import import xlrd
from base64 import decodestring
import xlsxwriter


class SalesSparepartWizard(models.TransientModel):
    _name           = "sales.sparepart.wizard"
    _description    = "Sales sparepart"
    
    date_from = fields.Date('Date From', required=True, default=fields.Datetime.now)
    date_to = fields.Date('Date To', required=True)
    so_ids = fields.Many2many('sale.order', string="Sales Quotation/Order Group")
    # state_ids = fields.Many2many("sqo.state.wizard",string="Sales Status")
    # is_detail = fields.Boolean(string="Detail show?")


    @api.constrains('date_from','data_to')
    def warning_date(self):
        if self.date_from >= self.date_to:
            raise UserError(_("You can not allowed Date From is greater than or equal to Date To."))


    @api.multi
    def generate(self):
        return self.env.ref('ati_pti_sales.sales_sparepart_xlsx').report_action(self.ids, config=False)


class SkepPibImport(models.TransientModel):
    _name = "update.import.skep.line"
    _description = "SKEP Line Import"

    file = fields.Binary(string='File', required=True)
    filename = fields.Char('File Name', default='import.xls')
    skep_id = fields.Many2one('skep.pib', 'SKEP',
                              required=False, ondelete='cascade')

    @api.multi
    def action_update_import_confirm(self):
        if not bool(self.file):
            raise UserError(_("Please upload file to continue!"))
        wb = xlrd.open_workbook(file_contents=decodestring(self.file))
        try:
            ws = wb.sheet_by_index(0)
            for row in range(1, ws.nrows):
                skep_line_id = self.env['skep.line']
                skep_line = skep_line_id.search([('skep_id.skep_no', '=', ws.cell(row, 1).value), ('seq', '=', ws.cell(row, 0).value)], limit=1)
                for rec in skep_line:
                    rec.update({
                        'skep_qty': ws.cell(row, 2).value,
                        'skep_item_value': ws.cell(row, 3).value,
                    })

        except Exception as err:
            import traceback
            raise UserError(_('Import file gagal!\n\n%s\n\n\nDetail:\n%s' %
                              (err, traceback.format_exc())))
 


