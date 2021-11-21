# -*- coding: utf-8 -*-

from typing import Sequence
from odoo import api, models, fields
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class po_detail_so_xlsx(models.AbstractModel):
    _name = 'report.ati_pti_sales.po_detail_so_xlsx'
    _inherit = 'report.report_xlsx.abstract'


    def _get_so(self, objects):
        domain = [('state','not in',('cancel','draft','waiting','approved_sbu','approved_manager','approved','sent','accepted'))]
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

    def _get_po_remaining(self,order_line=False, due_date_delivery = False, date_as = False):
        grouping='N/A'
        days = 0
        grouping_monthly = 'N/A'
        po_overdue_category = '-'
        actual_po_delivery_status = 'N/A'
        if order_line:
            if order_line.product_uom_qty == order_line.qty_delivered:
                actual_po_delivery_status = 'Done'
            elif order_line.product_uom_qty > order_line.qty_delivered:
                actual_po_delivery_status = 'On Progress'
            else:
                actual_po_delivery_status = 'N/A'

        if due_date_delivery and date_as:
            days = (fields.Datetime.from_string(due_date_delivery) - fields.Datetime.from_string(date_as)).days
            if 1 <= days <= 15:
                grouping = '1 - 15'
            elif 15 < days <= 30:
                grouping = '16 - 30'
            elif 30 < days <= 60:
                grouping = '31 - 60'
            elif 60 < days <= 90:
                grouping = '61 - 90'
            elif 90 < days <= 120:
                grouping = '91 - 120'
            elif days > 120:
                grouping = '121 ABOVE'
            elif days < 1:
                grouping = '0 Days: OVERDUE'
            else:
                grouping = 'N/A'
            
            # grouping monthly
            if 0 < days <= 30:
                grouping_monthly = 'GROUP 30 DAYS : 0-30'
            elif 30 < days <= 60:
                grouping_monthly = 'GROUP 60 DAYS : 31 - 60'
            elif 60 < days <= 90:
                grouping_monthly = 'GROUP 90 DAYS : 61 - 90'
            elif 90 < days <= 120:
                grouping_monthly = 'GROUP 120 DAYS : 91 - 120'
            elif days > 120:
                grouping_monthly = 'GROUP > 120 DAYS : 121 ABOVE'
            elif days <= 0:
                grouping_monthly = 'GROUP <= 0 DAYS : OVERDUE'
            else:
                grouping_monthly = 'N/A'
            
            # overdue category
            if 0 > days >= -30:
                po_overdue_category = 'GROUP 30 DAYS : 0-30 (- dari due Date)'
            elif -30 > days >= -60:
                po_overdue_category = 'GROUP 60 DAYS : 31 - 60 (- dari due Date)'
            elif -60 > days >= -90:
                po_overdue_category = 'GROUP 90 DAYS : 61 - 90 (- dari due Date)'
            elif -90 > days >= -120:
                po_overdue_category = 'GROUP 120 DAYS : 91 - 120 (- dari due Date)'
            elif days < -120:
                po_overdue_category = 'GROUP > 120 DAYS : 121 ABOVE (- dari due Date)'
            elif days >= 0:
                po_overdue_category = '-'
            else:
                po_overdue_category = 'N/A'


            return days, grouping, grouping_monthly,po_overdue_category, actual_po_delivery_status
        return days, grouping, grouping_monthly,po_overdue_category, actual_po_delivery_status


    # @api.model
    def generate_xlsx_report(self, workbook, data, objects):
        sheet_name = 'PO Detail Report'
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
        sheet.merge_range(1,0,1,9, 'PO Detail REPORT : %s' %(objects.team_ids.name), t_style)
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
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER NAME", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PTI QUOT NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER ORDER NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PTI IQOZ SO NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO ITEM LINE NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "INCOTERM", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER ITEM LINE DUEDATE DELIVERY", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO REMAINING / OVERDUE DAYS TO DELIVER TO CUSTOMER", h_style)
        h_col += 1

        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO DELIVERY DATE GROUPING)", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "DELIVERY DATE GROUPING (MONTHLY)", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO OVERDUE CATEGORY", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ACTUAL PO DELIVERY STATUS", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "USD/IDR", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "VALUE (IDR)", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "VALUE (USD)", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "DIVISION", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PTI IQO SO NO (OLD SYSTEM)", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER PIC NAME", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "MEDIA (EMAIL, FAX, WA, other)", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER PO AMANDMEND", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO HARD COPY RECV (Y/N)", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO HARD COPY RECV DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PTI IQOZ SO Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "BATCH DELIVERY", h_style)
        h_col += 1
        
        sheet.panes_frozen = True
        sheet.freeze_panes(6, 4)
        
        row = 6
        seq = 1
        for order in self._get_so(objects):            
            # so line
            for sol in order.order_line.filtered(lambda r: r.product_id.type != 'service').sorted(key=lambda r: (r['sequence2'])): 
                sheet.write(row, 0, seq or '', c_style) #No.
                sheet.write(row, 1, order.partner_id.name or '', c_style) #CUSTOMER NAME
                sheet.write(row, 2, order.name or '', c_style) #PTI QUOT NO
                sheet.write(row, 3, order.client_order_ref or '', c_style) #CUSTOMER ORDER NO
                sheet.write(row, 4, order.name or '', c_style) #PTI IQOZ SO NO
                sheet.write(row, 5, sol.sequence2 or 0, c_style) #PO ITEM LINE NO
                sheet.write(row, 6, order.transaction_method_id.name or '', c_style) #INCOTERM
                sheet.write(row, 7, datetime.strptime(sol.requested_date,DEFAULT_SERVER_DATETIME_FORMAT).strftime("%d-%m-%Y") if sol.requested_date else '', c_style) #CUSTOMER ITEM LINE DUE DATE DELIVERY
                po_remaining, po_remaining_grouping, po_remaining_grouping_monthly,po_overdue_category, actual_po_delivery_status  = self._get_po_remaining(order_line=sol, due_date_delivery=sol.requested_date, date_as = objects.date_as)
                sheet.write(row, 8, po_remaining, cline_center_style) #PO REMAINING / OVERDUE DAYS TO DELIVER TO CUSTOMER
                sheet.write(row, 9, po_remaining_grouping , cline_center_style) #PO DELIVERY DATE GROUPING)
                sheet.write(row, 10, po_remaining_grouping_monthly, cline_center_style) #DELIVERY DATE GROUPING (MONTHLY)
                sheet.write(row, 11, po_overdue_category, cline_center_style) #PO OVERDUE CATEGORY
                sheet.write(row, 12, actual_po_delivery_status, c_style) #ACTUAL PO DELIVERY STATUS
                sheet.write(row, 13, sol.currency_id.name if sol.currency_id else '', c_style) #USD/IDR
                sheet.write(row, 14, sol.price_subtotal if sol.currency_id.name in ('IDR','idr','Idr') else 0, num_style) #VALUE (IDR)
                sheet.write(row, 15, sol.price_subtotal if sol.currency_id.name in ('USD','usd','Isd') else 0, num_style) #VALUE (USD)
                sheet.write(row, 16, order.team_id.name or '', c_style) #DIVISION
                sheet.write(row, 17, order.number or '', c_style) #PTI IQO SO NO (OLD SYSTEM)
                sheet.write(row, 18, order.partner_pic.name or '', c_style) #CUSTOMER PIC NAME
                sheet.write(row, 19, order.media or '', c_style) #MEDIA (EMAIL, FAX, WA, other)
                # ???
                sheet.write(row, 20, '', c_style) #CUSTOMER PO AMANDMEND
                sheet.write(row, 21, 'YES' if order.hard_copy_recv == 'yes' else 'NO' if order.hard_copy_recv == 'no' else '', c_style) #PO HARD COPY RECV (Y/N)
                sheet.write(row, 22, datetime.strptime(order.hard_copy_date,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y") if order.hard_copy_date else '', c_style) #PO HARD COPY RECV DATE
                # ???
                sheet.write(row, 23, '', c_style) #PTI IQOZ SO Date
                sheet.write(row, 24, order.batch_delivery_so.name or '', c_style) #BATCH DELIVERY

                row += 1
                seq += 1