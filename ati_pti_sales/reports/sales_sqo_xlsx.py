# -*- coding: utf-8 -*-

from odoo import api, models, fields
# from report_xlsx.report.report_xlsx import ReportXlsx
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

class sales_sqo_xlsx(models.AbstractModel):
    _name = 'report.ati_pti_sales.sales_sqo_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    
    def _get_state(self):
        state = [
                {'sequence':1,'code':'draft','name':'Draft'},
                {'sequence':2,'code':'waiting','name':'Waiting Approval Division Manager'},
                {'sequence':3,'code':'approved_sbu','name':'Waiting Approval SBU Director'},
                {'sequence':4,'code':'approved_manager','name':'Waiting Approval President Director'},
                {'sequence':5,'code':'approved','name':'Approved'},
                {'sequence':6,'code':'sent','name':'Sent To Customer'},
                {'sequence':7,'code':'accepted','name':'Accepted By Customer'},
                {'sequence':8,'code':'sale','name':'Waiting For Delivery'},
                {'sequence':9,'code':'delivery','name':'Delivery Process'},
                {'sequence':10,'code':'waiting_invoice','name':'Waiting Invoice'},
                {'sequence':11,'code':'waiting_payment','name':'Waiting Payment'},
                {'sequence':12,'code':'done','name':'Done'},
                {'sequence':13,'code':'cancel','name':'Cancel'},
                ]
        return state

    def _get_so(self, objects):
        domain = [('create_date','>=',objects.date_from),('create_date','<=',objects.date_to)]
        if objects.team_ids:
            domain += [('team_id','in',objects.team_ids.ids)]
        if objects.partner_ids:
            domain += [('partner_id','in',objects.partner_ids.ids)]
        if objects.status_ids:
            domain += [('state','in',objects.status_ids.mapped('code'))]

        so = self.env['sale.order'].sudo().search(domain)
        
        return so


    # @api.model
    def generate_xlsx_report(self, workbook, data, objects):
        status_ids = objects.status_ids
        so = self._get_so(objects) 
        sheet_name = 'Detail contract customer'
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.set_footer('&R&6&"Courier New,Italic"Page &P of &N', {'margin': 0.25})
        column_width = [6, 25, 25, 20, 20, 30, 35, 25, 25, 20, 20]
        column_width = column_width
        for col_pos in range(0,len(column_width)):
            sheet.set_column(col_pos, col_pos, column_width[col_pos])


        # TITLE
        t_cell_format = {'font_name': 'Arial', 'font_size': 12, 'bold': True, 'valign': 'vcenter', 'align': 'center'}
        t_style = workbook.add_format(t_cell_format)
        sheet.merge_range(0,0,0,9, 'PT. INDOTURBINE', t_style)
        sheet.merge_range(1,0,1,9, 'Based on created date: '+ str(datetime.strptime(objects.date_from,"%Y-%m-%d").strftime("%d-%m-%Y")) +' until '+ str(datetime.strptime(objects.date_to,"%Y-%m-%d").strftime("%d-%m-%Y")), t_style)
        # default h_style
        h_cell_format = {'font_name': 'Arial', 'font_size': 10, 'bold': True, 'valign': 'vcenter', 'align': 'center', 'border': 1, 'bg_color':'#00aaff'}
        h_style = workbook.add_format(h_cell_format)
        # h_style line
        hline_cell_format = {'font_name': 'Arial', 'font_size': 8, 'bold': True, 'valign': 'vcenter', 'align': 'center', 'border': 1}
        hline_style = workbook.add_format(hline_cell_format)


        # default
        c_cell_format = {'font_name': 'Arial', 'font_size': 9, 'valign': 'top', 'align': 'left', 'border':1}
        c_style = workbook.add_format(c_cell_format)
        # sales channel
        c_sc_cell_format = {'font_name': 'Arial', 'font_size': 11, 'bold':True, 'valign': 'top', 'align': 'center', 'border':1, 'bg_color':'#64ff33'}
        c_sc_style = workbook.add_format(c_sc_cell_format)
        # customer
        c_cust_cell_format = {'font_name': 'Arial', 'font_size': 11, 'bold':True, 'valign': 'top', 'align': 'center', 'border':1, 'bg_color':'#33ffba'}
        c_cust_style = workbook.add_format(c_cust_cell_format)
        # state
        cstate_cell_format = {'font_name': 'Arial', 'font_size': 11, 'bold':True, 'valign': 'top', 'align': 'center', 'border':1, 'bg_color':'#ffb3d1'}
        cstate_style = workbook.add_format(cstate_cell_format)
        # style if detail
        c_cell_detail_format = {'font_name': 'Arial', 'font_size': 9, 'bold':True, 'valign': 'top', 'align': 'left', 'border':1, 'bg_color':'#ffff00'}
        c_detail_style = workbook.add_format(c_cell_detail_format)
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
        

        h_row, h_col = 3, 0
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "DIVISION", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "QU NO.", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SO NO.", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PROJECT NUMBER.", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "JOB DESCRIPTION", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER REFERENCE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER ORDER DATE", h_style)
        sheet.merge_range(h_row, h_col+1, h_row,h_col+2, "AMOUNT", h_style)
        h_col += 1
        sheet.write_string(h_row+1, h_col, "USD", h_style)
        h_col += 1
        sheet.write_string(h_row+1, h_col, "IDR", h_style)

        row = 5
        seq = 1
        for wiz in objects.wiz_line_ids:
            for team in wiz.team_ids:
                sheet.merge_range(row,0,row,len(column_width)-1, 'Sales Channel :%s' % (team and team.name or ''), c_sc_style)
                row +=1
                for partner in wiz.partner_ids:
                    sheet.merge_range(row,0,row,len(column_width)-1, 'Customer :%s' % (partner and partner.name or ''), c_cust_style)
                    row += 1
                    so_partner = wiz.so_ids.filtered(lambda r: r.partner_id.id == partner.id)
                    sss = list(set(so_partner.mapped('state')))
                    so_partner_state = [gs for gs in self._get_state() if gs['code'] in sss]
                    for state in so_partner_state:
                        sheet.merge_range(row,0,row,len(column_width)-1, 'Status :%s' % (state['name'] or ''), cstate_style)
                        row +=1
                        subtotal_usd, subtotal_idr = 0,0
                        # 
                        selected_style =  c_style if not objects.is_detail else c_detail_style
                        selected_num_style = num_style if not objects.is_detail else num_detail_style
                        for sop in so_partner.filtered(lambda s: s.state == state['code']).sorted(key=lambda ss: (ss['create_date'])):
                            sheet.write(row, 0, seq or '', selected_style)
                            sheet.write(row, 1, sop.team_id.name or '', selected_style)
                            sheet.write(row, 2, sop.quotation_number or '', selected_style)
                            sheet.write(row, 3, sop.name or '', selected_style)
                            sheet.write(row, 4, sop.projects_id and sop.projects_id.name or '', selected_style)
                            sheet.write(row, 5, sop.partner_id.name or '', selected_style)
                            sheet.write(row, 6, sop.job_title or '', selected_style)
                            sheet.write(row, 7, sop.client_order_ref or '', selected_style)
                            sheet.write(row, 8, sop.client_order_date_ref or '', selected_style)
                            sheet.write(row, 9, sop.amount_total if sop.currency_id.name.upper() == 'USD' else '', selected_num_style)
                            sheet.write(row, 10, sop.amount_total if sop.currency_id.name.upper() == 'IDR' else '', selected_num_style)
                            subtotal_usd += sop.amount_total if sop.currency_id.name.upper() == 'USD' else 0
                            subtotal_idr += sop.amount_total if sop.currency_id.name.upper() == 'IDR' else 0
                            row +=1 
                            seq +=1
                            if objects.is_detail:
                                # ----------------header line------------------
                                sheet.write_string(row, 0, "Seq.", hline_style)
                                sheet.write_string(row, 1, "PN", hline_style)
                                sheet.merge_range(row, 2, row, 3, "Product", hline_style)
                                sheet.merge_range(row, 4, row, 5, "Section", hline_style)
                                sheet.write_string(row, 6, "Ordered Qty.", hline_style)
                                sheet.write_string(row, 7, "Delivered/To Invoice/Invoiced", hline_style)
                                sheet.write_string(row, 8, "UoM", hline_style)
                                sheet.write_string(row, 9, "Unit Price.", hline_style)
                                sheet.write_string(row, 10, "Subtotal", hline_style)
                                row +=1
                                seq_line = 1
                                subtotal_line = 0
                                for line in sop.order_line:
                                    # -------------------line------------------------
                                    sheet.write(row, 0, "%d" % (line.sequence2 or 0), cline_left_style)
                                    sheet.write(row, 1, line.product_id.default_code or '', cline_left_style)
                                    sheet.merge_range(row, 2, row, 3, line.product_id.name or '', cline_left_style)
                                    sheet.merge_range(row, 4, row, 5, line.layout_category_id.name or '', cline_center_style)
                                    sheet.write(row, 6, line.product_uom_qty or 0, cline_center_style)
                                    sheet.write(row, 7, "%d/%d/%d" % (line.qty_delivered or 0,line.qty_to_invoice or 0,line.qty_to_invoice or 0), cline_center_style)
                                    sheet.write(row, 8, line.product_uom.name or '', cline_center_style)
                                    sheet.write(row, 9, line.price_unit or 0, num_style)
                                    sheet.write(row, 10, line.price_subtotal or 0, num_style)
                                    subtotal_line += line.price_subtotal
                                    seq_line += 1
                                    row += 1

                                # subtotal line
                                sheet.merge_range(row,0,row,9, 'Total Product', t_subtotal_style)
                                sheet.write(row,10, subtotal_line, num_subtotal_style)
                                row +=1

                        sheet.merge_range(row,0,row,8, 'Subtotal', t_subtotal_style)
                        sheet.write(row,9, subtotal_usd, num_subtotal_style)
                        sheet.write(row,10, subtotal_idr, num_subtotal_style)
                        row +=1

                    row +=1
                row +=1   

