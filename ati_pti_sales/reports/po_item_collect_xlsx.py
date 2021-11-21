# -*- coding: utf-8 -*-

from typing import Sequence
from odoo import api, models, fields
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class po_item_collect_xlsx(models.AbstractModel):
    _name = 'report.ati_pti_sales.po_item_collect_xlsx'
    _inherit = 'report.report_xlsx.abstract'


    def _get_po(self, objects):
        domain = [('state','!=','cancel')]
        if objects.date_from and objects.date_to:
            domain += [('create_date','>=',objects.date_from),('create_date','<=',objects.date_to)]
        if objects.team_ids:
            domain += [('x_team_id','=',objects.team_ids.id)]

        return self.env['purchase.order'].sudo().search(domain)

    def _get_skep_info(self, so=False, pol=False):
        skep_no, skep_line_no, skep_date, skep_recv_date, skep_validity_date = '','','', '',''
        pib_no,pib_item_no,pib_values = '', '', ''

        for s in so.order_line.sorted(key=lambda q: (q['sequence2'])):
            for d in s.skep_pib_ids:
                # skep
                skep_no += '%s' % ('/'+d.skep_no if d.skep_no else '')
                skep_date += '%s' %(','+ datetime.strptime(d.skep_date,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y") if d.skep_date else '')
                skep_recv_date += '%s' %(','+ datetime.strptime(d.skep_recv_date,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y") if d.skep_recv_date else '')
                skep_validity_date += '%s' %(','+ datetime.strptime(d.skep_expiry_date,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y") if d.skep_expiry_date else '')
                for l in d.skep_ids.filtered(lambda r: r.seq == pol.sequence and r.product_id.default_code == pol.product_id.default_code):
                    # skep_line_no
                    skep_line_no += '%s' %(','+str(l.seq_skep) if l.seq_skep else '')    
                # pib
                for pib in d.pib_ids:
                    pib_no += '%s' % ('/'+pib.pib_no if pib.pib_no else '')
                    for pl in pib.pib_line_ids.filtered(lambda s: s.product_id.default_code == pol.product_id.default_code):
                        pib_item_no += '%s' %(','+str(pl.seq_pib) if pl.seq_pib else '')
                        pib_values += '%s' %(','+str(pl.pib_item_values) if pl.pib_item_values else '')
        # 
        return skep_no, skep_line_no, skep_date, skep_recv_date, skep_validity_date, pib_no,pib_item_no,pib_values
    

    def _get_nor_to_duedate(self, nor_date=False,sol_pol=False):
        days = 0
        grouping = 'N/A'

        if nor_date and sol_pol and sol_pol.requested_date:
            days = (fields.Datetime.from_string(nor_date) - fields.Datetime.from_string(sol_pol.requested_date)).days
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

        return days, grouping


    def _get_collected_status(self, po=False, pol=False, objects=False):
        actual_item_to_be_collected_status = 'N/A'
        status = 'N/A'
        # a. Not Ready From Solar =  Jika belum melewati RTS dan belum ada NoR
        # b. Ready to Collect = Jika item sudah ada NoR nya
        # c. Collected = Ketika barang sudah diambil dari warehouse Solar dan sedang menuju Jakarta.
        # d. RTS Overdue : Jika sudah melewati tanggal RTS namun masih belum ada NoR
        summary_nor_goods = self.env['summary.nor.goods'].sudo().search([('purchase_id','=',po.id),('position','=',pol.sequence),('product_id.default_code','=',pol.product_id.default_code)], limit=1)
        if summary_nor_goods:
            if summary_nor_goods.nor_state == 'no':
                status ='NO'
                if pol and pol.rts_date:
                    if pol.rts_date <= objects.date_as:
                        actual_item_to_be_collected_status = 'Not Ready From Solar'
                    elif pol.rts_date > objects.date_as:
                        actual_item_to_be_collected_status = 'RTS Overdue'
                else:
                    actual_item_to_be_collected_status = 'N/A'
                return actual_item_to_be_collected_status, status

            elif summary_nor_goods.nor_state == 'yes':
                status = 'YES'
                pickup_goods_line = self.env['pickup.goods.line'].sudo().search([('purchase_order_line_id','=',pol.id)], limit=1) 
                if pickup_goods_line and pickup_goods_line.pickup_id.state == 'confirmed':
                    actual_item_to_be_collected_status = 'Collected'
                elif summary_nor_goods.nor_state == 'yes':
                    actual_item_to_be_collected_status = 'Ready To Collect'
                else:
                    actual_item_to_be_collected_status = 'N/A'

                return actual_item_to_be_collected_status, status

        return actual_item_to_be_collected_status, status


    # @api.model
    def generate_xlsx_report(self, workbook, data, objects):
        sheet_name = 'Item To Be Collect Report'
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
        sheet.merge_range(1,0,1,9, 'ITEM TO BE COLLECT REPORT : %s' %(objects.team_ids.name), t_style)
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
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER ORDER NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PTI IQOZ SO NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER ITEM LINE DUEDATE DELIVERY", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "RTS", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SOLAR PO NO (SP)", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SP - LINE ITEM NUMBER", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Item Code", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "DESC", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "QTY PO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "UOM PO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CURRENCY", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "VALUES", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "OLD P/N", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "P/N PO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "BATCH DELIVERY", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SP DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SP SOLAR ITEM LINE NUMBER", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "DAP SUPPORTING DOC", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "DAP SUPPORTING DOC SUBMIT DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SKEP NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SKEP line NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SKEP DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SKEP RECV DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SKEP VALIDITY DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PIB NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PIB ITEM NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PIB VALUES", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "P/L NO - SOLAR LOAD CODE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "NOR", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "NOR DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "REMAINING DAYS OF NOR TO PO DUE DATE DELIVERY", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "REMAINING DAYS GROUPING", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ACTUAL ITEM TO BE COLLECTED STATUS", h_style)
        h_col += 1
        
        
        sheet.panes_frozen = True
        sheet.freeze_panes(6, 4)
        
        row = 6
        seq = 1
        for order in self._get_po(objects):            
            for pol in order.order_line.filtered(lambda r: r.product_id.type != 'service').sorted(key=lambda r: (r['sequence'])): 
                sheet.write(row, 0, seq or '', c_style) #No.
                sheet.write(row, 1, order.sale_id.partner_id.name or '', c_style) #CUSTOMER NAME
                sheet.write(row, 2, order.name or '', c_style) #CUSTOMER ORDER NO
                sheet.write(row, 3, order.sale_id.name or '', c_style) #PTI IQOZ SO NO
                sheet.write(row, 4, datetime.strptime(pol.date_planned,DEFAULT_SERVER_DATETIME_FORMAT).strftime("%d-%m-%Y") if pol.date_planned else '', c_style) #CUSTOMER ITEM LINE DUEDATE DELIVERY
                sheet.write(row, 5, datetime.strptime(pol.rts_date,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y") if pol.rts_date else '', c_style) #RTS
                sheet.write(row, 6, order.partner_ref or  '', c_style) #SOLAR PO NO (SP)
                sheet.write(row, 7, pol.sequence or 0, cline_center_style) #SP - LINE ITEM NUMBER
                sheet.write(row, 8, pol.product_id.default_code or '', c_style) #Item Code
                sheet.write(row, 9, pol.name or '', c_style) #DESC
                sheet.write(row, 10, pol.product_qty or 0, cline_center_style) #QTY PO
                sheet.write(row, 11, pol.product_uom.name or '', cline_center_style) #UOM PO
                sheet.write(row, 12, pol.currency_id.name if pol.currency_id else '', c_style) #CURRENCY
                sheet.write(row, 13, pol.price_subtotal or 0, num_style) #VALUES
                sheet.write(row, 14, pol.product_id.history_replacement_ids[0].default_code if pol.product_id.history_replacement_ids else '', c_style) #OLD P/N
                sheet.write(row, 15, pol.product_id.default_code or '', c_style) #P/N PO
                sheet.write(row, 16, order.sale_id.batch_delivery_so.name or '', c_style) #BATCH DELIVERY
                sheet.write(row, 17, datetime.strptime(order.vendor_date,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y") if order.vendor_date else '', c_style) #SP DATE
                sheet.write(row, 18, pol.sequence or 0, cline_center_style) #SP SOLAR ITEM LINE NUMBER
                sheet.write(row, 19, 'YES' if order.sale_id.dap_doc == 'yes' else 'NO' if order.sale_id.dap_doc == 'no' else '', c_style) #DAP SUPPORTING DOC
                sheet.write(row, 20, datetime.strptime(order.sale_id.dap_doc_date,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y") if order.sale_id and order.sale_id.dap_doc_date else '', c_style) #DAP SUPPORTING DOC SUBMIT DATE
                skep_no, skep_line_no, skep_date, skep_recv_date, skep_validity_date, pib_no, pib_item_no,pib_values = self._get_skep_info(so=order.sale_id, pol=pol)                
                sheet.write(row, 21, skep_no, c_style) #SKEP NO
                sheet.write(row, 22, skep_line_no, cline_center_style) #SKEP line NO
                sheet.write(row, 23, skep_date, c_style) #SKEP DATE
                sheet.write(row, 24, skep_recv_date, c_style) #SKEP RECV DATE
                sheet.write(row, 25, skep_validity_date, c_style) #SKEP VALIDITY DATE

                sheet.write(row, 26, pib_no,c_style) #PIB NO
                sheet.write(row, 27, pib_item_no, cline_center_style) #PIB ITEM NO
                sheet.write(row, 28, pib_values, c_style) #PIB VALUES

                sheet.write(row, 29, pol.load_code or '', c_style) #P/L NO - SOLAR LOAD CODE
                actual_item_to_be_collected_status, nor_status = self._get_collected_status(po=order, pol=pol, objects=objects)
                sheet.write(row, 30, nor_status, c_style) #NOR
                sheet.write(row, 31, datetime.strptime(pol.nor_date,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y") if pol.nor_date else '', c_style) #NOR DATE
                remaining_days_nor_to_due, nor_due_grouping = self._get_nor_to_duedate(nor_date=pol.nor_date,sol_pol=order.sale_id.order_line.filtered(lambda l: l.sequence2 == pol.sequence and l.product_id.default_code == pol.product_id.default_code))
                sheet.write(row, 32, remaining_days_nor_to_due, c_style) #REMAINING DAYS OF NOR TO PO DUE DATE DELIVERY
                sheet.write(row, 33, nor_due_grouping, c_style) #REMAINING DAYS GROUPING
                sheet.write(row, 34, actual_item_to_be_collected_status, c_style) #ACTUAL ITEM TO BE COLLECTED STATUS

                row += 1
                seq += 1