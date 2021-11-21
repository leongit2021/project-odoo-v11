# -*- coding: utf-8 -*-

from typing import Sequence
from odoo import api, models, fields
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class rfq_detail_xlsx(models.AbstractModel):
    _name = 'report.ati_pti_sales.rfq_detail_xlsx'
    _inherit = 'report.report_xlsx.abstract'


    def _get_so(self, objects):
        domain = [('state','in',('draft','waiting','approved_sbu','approved_manager','approved','sent','accepted'))]
        if objects.date_from and objects.date_to:
            domain += [('team_id','=',objects.team_ids.id),('create_date','>=',objects.date_from),('create_date','<=',objects.date_to)]
        else:
            domain += [('team_id','=',objects.team_ids.id)]

        return self.env['sale.order'].sudo().search(domain).sorted(key=lambda r: (r.name))

    def _get_inquiry_remaining_days_grouping(self, so = False, inquiry_due_date = False, date_as = False, client_order_date_ref=False):
        days, grouping, status = 0, 'inquiry date is null', 'N/A'
        if inquiry_due_date and date_as:
            days = (fields.Datetime.from_string(inquiry_due_date) - fields.Datetime.from_string(date_as)).days
            if 0 <= days <= 7:
                grouping = '0 - 7 Days'
            elif 7 < days <= 14:
                grouping = '8 - 14 Days'
            elif 14 < days <= 30:
                grouping = '15 - 30 Days'
            elif days > 30:
                grouping = '> 30 Days'
            else:
                grouping = 'N/A'
        
        if so.state in ('draft','waiting','approved_sbu','approved_manager','approved','sent','accepted'):
            status = 'On Progress'
        elif so.state in ('sale','delivery','waiting_invoice','waiting_payment','done'):
            status = 'Done'
        elif so.state in ('cancel'):
            status = 'Cancel'
        else:
            status = 'N/A'        
            
        return days, grouping, status


    # @api.model
    def generate_xlsx_report(self, workbook, data, objects):
        sheet_name = 'RFQ Detail Report'
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.set_footer('&R&6&"Courier New,Italic"Page &P of &N', {'margin': 0.25})
        column_width = [6, 20, 50, 25, 15, 25, 25, 30, 30, 20] + [30]*75
        column_width = column_width
        for col_pos in range(0,len(column_width)):
            sheet.set_column(col_pos, col_pos, column_width[col_pos])


        # TITLE
        t_cell_format = {'font_name': 'Arial', 'font_size': 12, 'bold': True, 'valign': 'vcenter', 'align': 'left'}
        t_style = workbook.add_format(t_cell_format)
        sheet.merge_range(0,0,0,9, 'PT. INDOTURBINE', t_style)
        sheet.merge_range(1,0,1,9, 'RFQ Detail REPORT : %s' %(objects.team_ids.name), t_style)
        sheet.merge_range(2,0,2,9, 'DATE :        ' + str(datetime.strptime(objects.date_as,"%Y-%m-%d").strftime("%d-%m-%Y")), t_style)
        # default h_style
        h_cell_format = {'font_name': 'Arial', 'font_size': 10, 'bold': True, 'valign': 'vcenter', 'align': 'center', 'border': 1, 'bg_color':'#00aaff'}
        h_style = workbook.add_format(h_cell_format)
        # h_style line
        hline_cell_format = {'font_name': 'Arial', 'font_size': 8, 'bold': True, 'valign': 'vcenter', 'align': 'center', 'border': 1, 'bg_color':'#ffff00'}
        hline_style = workbook.add_format(hline_cell_format)


        # default
        c_cell_format = {'font_name': 'Arial', 'font_size': 9, 'valign': 'top', 'align': 'left'}
        c_style = workbook.add_format(c_cell_format)
        # line
        cline_left_cell_format = {'font_name': 'Arial', 'font_size': 9, 'valign': 'top', 'align': 'left'}
        cline_left_style = workbook.add_format(cline_left_cell_format)

        cline_center_cell_format = {'font_name': 'Arial', 'font_size': 9, 'valign': 'top', 'align': 'center'}
        cline_center_style = workbook.add_format(cline_center_cell_format)

        cline_right_cell_format = {'font_name': 'Arial', 'font_size': 9, 'valign': 'top', 'align': 'right'}
        cline_right_style = workbook.add_format(cline_right_cell_format)


        # selection
        c_style_tot_format = c_cell_format.copy()
        c_style_tot_format.update({'bold':True,'bg_color':'#ffff00'})
        c_style_tot = workbook.add_format(c_style_tot_format)
        
        # default
        num_cell_format = c_cell_format.copy()
        num_cell_format.update({'align': 'right', 'num_format':'#,##0.##;-#,##0.##;-'})
        num_style = workbook.add_format(num_cell_format)
        # subtotal
        subtot_num_cell_format = c_cell_format.copy()
        subtot_num_cell_format.update({'align': 'right', 'bold':True, 'num_format':'#,##0.##;-#,##0.##;-'})
        subtot_style = workbook.add_format(subtot_num_cell_format)
        # board_style
        cboard_cell_format = {'font_name': 'Arial', 'font_size': 9, 'valign': 'top', 'align': 'left','bg_color':'#f0f5f3'}
        cboard_style = workbook.add_format(cboard_cell_format)


        h_row, h_col = 4, 0

        sheet.merge_range(h_row, h_col, h_row+1,h_col, "No.", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "QU/SO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Customer", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "NO PO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "LINE ITEM", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "QTY", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "UOM", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PRICE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "RECEIVE DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Validity Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "REMAINING DAYS", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "REMAINING DAYS GROUPING", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "STATUS", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "YEAR", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER INQUIRY BID DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "INQUIRY BID NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "INQUIRY UNIT PRICE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "INQUIRY TOTAL AMOUNT ", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PTI QUOT DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PTI FINAL QUOT NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PTI FINAL QUOT DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PTI FINAL QUOT AMOUNT", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER ORDER DATE", h_style)
        h_col += 1
        
        sheet.panes_frozen = True
        sheet.freeze_panes(6, 4)
        
        row = 6
        seq = 1
        for order in self._get_so(objects):            
            # so line
            for sol in order.order_line.filtered(lambda r: r.product_id.type != 'service').sorted(key=lambda r: (r['sequence2'])): 
                sheet.write(row, 0, seq or '', c_style) #No.
                sheet.write(row, 1, order.name or '', c_style) #QU/SO
                sheet.write(row, 2, order.partner_id.name or '', c_style) #Customer
                sheet.write(row, 3, order.client_order_ref or '', c_style) #NO PO
                sheet.write(row, 4, sol.sequence2 or 0, c_style) #LINE ITEM
                sheet.write(row, 5, sol.product_uom_qty or 0, c_style) #QTY
                sheet.write(row, 6, sol.product_uom.name or '', c_style) #UOM
                sheet.write(row, 7, sol.price_unit or 0, num_style) #PRICE
                sheet.write(row, 8, datetime.strptime(order.inquiry_receive_date,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y") if order.inquiry_receive_date else '', c_style) #RECEIVE DATE
                sheet.write(row, 9, datetime.strptime(order.inquiry_due_date,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y") if order.inquiry_due_date else '', c_style) #Validity Date
                inquiry_remaining_days, inquiry_remaining_days_grouping, quotation_status = self._get_inquiry_remaining_days_grouping(so= order, inquiry_due_date= order.inquiry_due_date, date_as= objects.date_as, client_order_date_ref= order.client_order_date_ref)
                sheet.write(row, 10, inquiry_remaining_days or 0, c_style) #REMAINING DAYS
                sheet.write(row, 11, inquiry_remaining_days_grouping or '', c_style) #REMAINING DAYS GROUPING
                sheet.write(row, 12, quotation_status or '', c_style) #STATUS
                sheet.write(row, 13, datetime.strptime(order.create_date, DEFAULT_SERVER_DATETIME_FORMAT).year if order.create_date else '', c_style) #YEAR
                sheet.write(row, 14, datetime.strptime(order.inquery_bid_date,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y") if order.inquery_bid_date else '', c_style) #CUSTOMER INQUIRY BID DATE
                sheet.write(row, 15, order.inquery_bid_number or '', c_style) #INQUIRY BID NO
                sheet.write(row, 16, sol.price_unit or 0, num_style) #INQUIRY UNIT PRICE
                sheet.write(row, 17, sol.price_subtotal or 0, num_style) #INQUIRY TOTAL AMOUNT
                # ???
                sheet.write(row, 18, datetime.strptime(order.final_quotasion_date,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y") if order.final_quotasion_date else '', c_style) #PTI QUOT DATE
                sheet.write(row, 19, order.final_quotasion_no or '', c_style) #PTI FINAL QUOT NO
                sheet.write(row, 20, datetime.strptime(order.final_quotasion_date,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y") if order.final_quotasion_date else '', c_style) #PTI FINAL QUOT DATE
                sheet.write(row, 21, order.final_quotasion_amount or 0, c_style) #PTI FINAL QUOT AMOUNT
                sheet.write(row, 22, datetime.strptime(order.client_order_date_ref,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y") if order.client_order_date_ref else '', c_style) #CUSTOMER ORDER DATE

                row += 1
                seq += 1