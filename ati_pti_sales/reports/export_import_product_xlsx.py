# -*- coding: utf-8 -*-

from odoo import api, models, fields
# from report_xlsx.report.report_xlsx import ReportXlsx
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta



class export_import_product_xlsx(models.AbstractModel):
    _name = 'report.ati_pti_sales.export_import_product_xlsx'
    _inherit = 'report.report_xlsx.abstract'



    def _get_product(self, objects):
        if objects.product_ids:
            return objects.product_ids
        else:
            return self.env['product.template'].sudo().search([('categ_id','=',objects.categ_id.id)])
    

    # @api.model
    def generate_xlsx_report(self, workbook, data, objects):
        sheet_name = 'Export Product'
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.set_footer('&R&6&"Courier New,Italic"Page &P of &N', {'margin': 0.25})
        column_width = [15, 30] + [30]*20
        column_width = column_width
        for col_pos in range(0,len(column_width)):
            sheet.set_column(col_pos, col_pos, column_width[col_pos])


        # TITLE
        t_cell_format = {'font_name': 'Arial', 'font_size': 12, 'bold': True, 'valign': 'vcenter', 'align': 'center'}
        t_style = workbook.add_format(t_cell_format)
        # default h_style
        h_cell_format = {'font_name': 'Arial', 'font_size': 10, 'bold': True, 'valign': 'vcenter', 'align': 'center', 'border': 1, 'bg_color':'#00aaff'}
        h_style = workbook.add_format(h_cell_format)
        # h_style line
        hline_cell_format = {'font_name': 'Arial', 'font_size': 8, 'bold': True, 'valign': 'vcenter', 'align': 'center', 'border': 1}
        hline_style = workbook.add_format(hline_cell_format)


        # default
        c_cell_format = {'font_name': 'Arial', 'font_size': 9, 'valign': 'top', 'align': 'left', 'border':1}
        c_style = workbook.add_format(c_cell_format)
        # line
        cline_left_cell_format = {'font_name': 'Arial', 'font_size': 8, 'valign': 'top', 'align': 'left', 'border':1}
        cline_left_style = workbook.add_format(cline_left_cell_format)

        cline_center_cell_format = {'font_name': 'Arial', 'font_size': 8, 'valign': 'top', 'align': 'center', 'border':1}
        cline_center_style = workbook.add_format(cline_center_cell_format)

        cline_right_cell_format = {'font_name': 'Arial', 'font_size': 8, 'valign': 'top', 'align': 'right', 'border':1}
        cline_right_style = workbook.add_format(cline_right_cell_format)

        
        # default number
        num_cell_format = c_cell_format.copy()
        num_cell_format.update({'align': 'right', 'num_format':'#,##0.##;-#,##0.##;-'})
        num_style = workbook.add_format(num_cell_format)
        # num style if detail
        num_cell_detail_format = c_cell_format.copy()
        num_cell_detail_format.update({'align': 'right', 'num_format':'#,##0.##;-#,##0.##;-', 'bg_color':'#ffff00'})
        num_detail_style = workbook.add_format(num_cell_detail_format)
        # subtotal text
        t_subtotal_cell_format = c_cell_format.copy()
        t_subtotal_cell_format.update({'font_name': 'Arial', 'font_size': 10, 'bold': True, 'valign': 'vcenter', 'align': 'center','border':1,'bg_color':'#f0f5f3'})
        t_subtotal_style = workbook.add_format(t_subtotal_cell_format)
        # subtotal
        num_subtotal_cell_format = c_cell_format.copy()
        num_subtotal_cell_format.update({'align': 'right', 'bold':True, 'num_format':'#,##0.##;-#,##0.##;-','bg_color':'#f0f5f3'})
        num_subtotal_style = workbook.add_format(num_subtotal_cell_format)
        

        h_row, h_col = 0, 0
        sheet.write(h_row, h_col, "PRODUCT ID", h_style)
        h_col += 1
        sheet.write(h_row, h_col, "PN", h_style)
        h_col += 1
        sheet.write(h_row, h_col, "PRODUCT NAME", h_style)
        h_col += 1
        sheet.write(h_row, h_col, "UOM", h_style)
        h_col += 1
        sheet.write(h_row, h_col, "PURCHASE UOM", h_style)
        h_col += 1
        sheet.write(h_row, h_col, "COST(EX WORKS)", h_style)
        h_col += 1
        sheet.write(h_row, h_col, "CATEGORY", h_style)
        h_col += 1
        sheet.write(h_row, h_col, "LARTAS", h_style)
        h_col += 1
        sheet.write(h_row, h_col, "HS CODE", h_style)
        h_col += 1
        sheet.write(h_row, h_col, "ADP", h_style)
        h_col += 1
        sheet.write(h_row, h_col, "TYPE", h_style)
        h_col += 1
        sheet.write(h_row, h_col, "DIM(LENGTH)", h_style)
        h_col += 1
        sheet.write(h_row, h_col, "DIM(WIDTH)", h_style)
        h_col += 1
        sheet.write(h_row, h_col, "DIM(HEIGHT)", h_style)
        h_col += 1
        sheet.write(h_row, h_col, "DIM(UOM)", h_style)
        h_col += 1

        sheet.panes_frozen = True
        sheet.freeze_panes(1, 3)


        row = 1
        for pro in self._get_product(objects):
            sheet.write(row, 0, pro.id, c_style)
            sheet.write(row, 1, pro.default_code or '', c_style)
            sheet.write(row, 2, pro.name or '', c_style)
            sheet.write(row, 3, pro.uom_id.name or '', cline_center_style)
            sheet.write(row, 4, pro.uom_po_id.name or '', cline_center_style)
            sheet.write(row, 5, pro.standard_price or 0, c_style)
            sheet.write(row, 6, pro.categ_id.name or '', c_style)
            sheet.write(row, 7, pro.product_lartas or '', c_style)
            sheet.write(row, 8, pro.hs_code or '', c_style)
            sheet.write(row, 9, pro.product_adp or '', c_style)
            product_type = {'consu': 'Consumable', 'service': 'Service', 'product': 'Stockable Product'}
            sheet.write(row, 10, product_type[pro.type] if pro.type  else '', c_style)
            sheet.write(row, 11, pro.product_length or 0, c_style)
            sheet.write(row, 12, pro.product_width or 0, c_style)
            sheet.write(row, 13, pro.product_height or 0, c_style)
            sheet.write(row, 14, pro.product_dimension.name or '', c_style)
            
            row += 1
