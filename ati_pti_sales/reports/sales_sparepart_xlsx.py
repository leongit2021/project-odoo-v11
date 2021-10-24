# -*- coding: utf-8 -*-

from odoo import api, models, fields
# from report_xlsx.report.report_xlsx import ReportXlsx
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class sales_sparepart_xlsx(models.AbstractModel):
    _name = 'report.ati_pti_sales.sales_sparepart_xlsx'
    _inherit = 'report.report_xlsx.abstract'


    def _get_so(self, objects):
        so = self.env['sale.order'].sudo().search([('create_date','>=',objects.date_from),
                                                    ('create_date','<=',objects.date_to),
                                                    ])

        return so

    def _get_po(self, order):
        po = self.env['purchase.order'].sudo().search([('sale_id','=',order.id)])

        return po

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


    # @api.model
    def generate_xlsx_report(self, workbook, data, objects):
        so = self._get_so(objects) 
        sheet_name = 'Div 21 Sparepart'
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.set_footer('&R&6&"Courier New,Italic"Page &P of &N', {'margin': 0.25})
        column_width = [6, 20, 20, 20, 20, 20, 20, 20, 20, 20] + [20]*60
        column_width = column_width
        for col_pos in range(0,len(column_width)):
            sheet.set_column(col_pos, col_pos, column_width[col_pos])


        # TITLE
        t_cell_format = {'font_name': 'Arial', 'font_size': 12, 'bold': True, 'valign': 'vcenter', 'align': 'center'}
        t_style = workbook.add_format(t_cell_format)
        sheet.merge_range(0,0,0,9, 'PT. INDOTURBINE', t_style)
        sheet.merge_range(1,0,1,9, 'Report Div-21 Sparepart: '+ str(datetime.strptime(objects.date_from,"%Y-%m-%d").strftime("%d-%m-%Y")) +' until '+ str(datetime.strptime(objects.date_to,"%Y-%m-%d").strftime("%d-%m-%Y")), t_style)
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


        h_row, h_col = 3, 0
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "No.", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Year", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Customer Name.", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Inq. Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Inq. No.", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Inq. Closing Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "File Number", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Quot Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Quot Validity", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "QUOT_CURRENCY", h_style)
        # 
        sheet.merge_range(h_row, h_col+1, h_row,h_col+2, "Nilai Penawaran", h_style)
        h_col += 1
        sheet.write_string(h_row+1, h_col, "IDR VALUES", h_style)
        h_col += 1
        sheet.write_string(h_row+1, h_col, "USD VALUES", h_style)
        # 
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SO DATE", h_style)
        # 
        sheet.merge_range(h_row, h_col+1, h_row,h_col+2, "Nilai SO", h_style)
        h_col += 1
        sheet.write_string(h_row+1, h_col, "IDR VALUES", h_style)
        h_col += 1
        sheet.write_string(h_row+1, h_col, "USD VALUES", h_style)
        # 
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Job Description", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Category", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Parts No", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Parts Description", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Customer PO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Delivery Terms", h_style)
        h_col += 1

        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SKEP NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SKEP DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PIB NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PIB DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO Due Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Qty Cust. PO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Ccy", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Cust. PO Amount", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "QS SOLAR", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "QS DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO To Solar", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Solar PO Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Solar PO Available", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PN PO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Qty. Solar PO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CS/SP Values", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Stock Qty", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Qty Slr - Qty Cust", h_style)
        h_col += 1
        
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "WH/IN Reference/Status", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Packing List No.", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PL Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Scheduled Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PL Qty", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "WH/POINT", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Receive From Solar", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "O/S fm Slr", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Date Receive From Solar", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Values Received WH", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Picking List Date", h_style)
        h_col += 1
        # sheet.merge_range(h_row, h_col, h_row+1,h_col, "Qty Slr - Qty Cust", h_style)
        # h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PTI DO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "DO Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Product", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Qty Delivery To Customer", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Cust. Delivery Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Rect Dt By Cust.", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "VALUES DO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Invoice No.", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Invoice Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Product", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Invoice Amt", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Qty. Invoice To Cust.", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Point of Delivery", h_style)
        h_col += 1

        sheet.panes_frozen = True
        sheet.freeze_panes(5, 3)

        row = 5
        seq = 1
        count_row = {'rowline':0,'rowpo':0,'rowpoline':0,'rowpick':0,'rowpickline':0,'rowdo': 0,'rowdoline':0,'rowinv':0,'rowinvline':0}
        # for order in so.sorted(key=lambda r: (r['create_date'])):
        for order in objects.so_ids.sorted(key=lambda r: (r['create_date'])):
            sheet.write(row, 0, seq or '', c_style)
            sheet.write(row, 1, datetime.strptime(order.create_date, DEFAULT_SERVER_DATETIME_FORMAT).year or '', c_style)
            sheet.write(row, 2, order.partner_id.name or '', c_style)
            sheet.write(row, 3, order.inquery_bid_date or '', c_style)
            sheet.write(row, 4, order.inquery_bid_number or '', c_style)
            sheet.write(row, 5, order.validity_date or '', c_style) # Inq Closing Date
            sheet.write(row, 6, order.projects_id.name or '', c_style) # pti_reff
            sheet.write(row, 7, order.client_order_date_ref or '', c_style) # quo_date?
            sheet.write(row, 8, order.validity_date or '', c_style) # quot_validity
            sheet.write(row, 9, order.currency_id.name.upper() or '', c_style) # quot_currecy
            sheet.write(row, 10, order.amount_total if order.currency_id.name.upper() == 'IDR' else '', num_style) # IDR VALUES
            sheet.write(row, 11, order.amount_total if order.currency_id.name.upper() == 'USD' else '', num_style) # USD VALUES
            sheet.write(row, 12, order.name or '', c_style) # so
            sheet.write(row, 13, order.date_order or '', c_style) # SO DATE
            sheet.write(row, 14, order.amount_total if order.currency_id.name.upper() == 'IDR' else '', num_style) # IDR VALUES
            sheet.write(row, 15, order.amount_total if order.currency_id.name.upper() == 'USD' else '', num_style) # USD VALUES
            sheet.write(row, 16, order.job_title or '', c_style) # Job Description
            so_state = [sos for sos in self._get_state() if sos['code'] == order.state]
            sheet.write(row, 17, so_state[0]['name'] or '', c_style) # Job Description
            rowline = row
            # so line
            for line in order.order_line.sorted(key=lambda r: (r['sequence2'])):
                sheet.write(rowline, 18, '%s: %s' % (line.product_id.default_code or '', line.product_id.name or ''), c_style) # Product Line
                sheet.write(rowline, 19, line.name or '', c_style) # Description
                sheet.write(rowline, 20, order.client_order_ref or '', c_style) # Customer PO
                sheet.write(rowline, 21, line.customer_lead or 0, c_style) # Delivery Terms
                sheet.write(rowline, 22, order.client_order_date_ref or '', c_style) # PO Date
                sheet.write(rowline, 23, line.skep_no or '', c_style) # SKEP NO
                sheet.write(rowline, 24, line.skep_date or '', c_style) # SKEP DATE
                sheet.write(rowline, 25, line.pib_no or '', c_style) # PIB NO
                sheet.write(rowline, 26, line.pib_date or '', c_style) # PIB DATE
                sheet.write(rowline, 27, order.validity_date or '', c_style) # PO Due Date
                sheet.write(rowline, 28, line.product_uom_qty or 0, c_style) # Qty. Cust PO
                sheet.write(rowline, 29, line.currency_id.name.upper() or '', c_style) # PO Due Date
                sheet.write(rowline, 30, line.price_subtotal or '', num_style) # Cust PO Amount
                sheet.write(rowline, 31, '' or '', c_style) # QS Solar
                sheet.write(rowline, 32, '' or '', c_style) # QS Date
                rowline += 1 
            # 
            count_row['rowline'] = rowline  

            # -------po-----------
            po = self._get_po(order)
            rowpo = row
            for p in po.sorted(key=lambda r: (r['create_date'])):
                # ------inisiatif : insert status PO 
                sheet.write(rowpo, 33, '%s ' %(p.name or ''), c_style) # NO PO
                sheet.write(rowpo, 34,  p.vendor_date or '', c_style) # Solar PO Date
                sheet.write(rowpo, 35, p.date_order or '', c_style) # Solar PO Available
                rowpoline = rowpo
                poline_price_subtotal = 0
                for pline in p.order_line.sorted(key=lambda r: (r['sequence'])):
                    sheet.write(rowpoline, 36, '%s: %s' %(pline.product_id.default_code or '', pline.product_id.name or ''), c_style) # PN
                    # -----inisiatif: Quantity, Received Qty, Billed Qty.
                    sheet.write(rowpoline, 37, '%d/%d/%d' %(pline.product_qty or 0,pline.qty_received or 0,pline.qty_invoiced or 0), cline_center_style) # Qty Solar PO
                    sheet.write(rowpoline, 38, pline.price_subtotal or 0, num_style) # CS/SP Values
                    poline_price_subtotal += pline.price_subtotal
                    # stock qty
                    sheet.write(rowpoline, 39, 0 or 0, cline_center_style) # Stock Qty
                    sheet.write(rowpoline, 40, 0 or 0, cline_center_style) # Qty Slr - Qty Cust
                    rowpoline += 1

                sheet.write(rowpoline, 38, poline_price_subtotal or 0, subtot_style) # total CS/SP Values
                rowpoline += 1
                  
                #
                count_row['rowpoline'] = rowpoline  
                # ----------receipt: WH/IN
                rowpick = rowpo
                for pick in p.picking_ids:
                    # ------inisiatif: Reference, Status
                    sheet.write(rowpick, 41,'Reference: %s' %(pick.name or ''), c_style)
                    sheet.write(rowpick, 42, pick.carrier_tracking_ref or '', c_style) # Packing List No.
                    sheet.write(rowpick, 43, pick.scheduled_date or '', c_style) # PL Date
                    rowpickline = rowpick
                    for mline in pick.move_lines:
                        # ------inisiatif: Product
                        sheet.write(rowpickline, 44, '%s :%s '% (mline.product_id and mline.product_id.default_code or '', pick.product_id and pick.product_id.name or ''), c_style) # Scheduled Date
                        sheet.write(rowpickline, 45, '%d/%d' %(mline.product_uom_qty or 0,mline.reserved_availability or 0), cline_center_style) # PL Qty
                        sheet.write(rowpickline, 46, 'WH/POINT', c_style) # WH/POINT
                        sheet.write(rowpickline, 47, mline.quantity_done or 0, cline_center_style) # Receive From Solar
                        sheet.write(rowpickline, 48, 'O/S fm Slr', c_style) # O/S fm Slr
                        sheet.write(rowpickline, 49, pick.qc_date or '', c_style) # Date Receive From Solar
                        sheet.write(rowpickline, 50, 'VALUES RECEIVED W/H', c_style) # VALUES RECEIVED WH
                        sheet.write(rowpickline, 51, pick.qc_date or '', c_style) # Picking List Date
                        rowpickline += 1

                    rowpick = rowpickline + 1

                rowpo = rowpick if rowpick > rowpoline else rowpoline + 1
            # 
            count_row['rowpo'] = rowpo
                    
            # -----------WH/OUT
            rowdo = row
            for do in order.picking_ids :
                sheet.write(rowdo, 52, '%s ' % (do.name or ''), c_style) # PTI DO
                sheet.write(rowdo, 53, do.qc_date or '', c_style) # DO Date
                rowdoline = rowdo
                for doline in do.move_lines:
                    # -------inisiatif: Product
                    sheet.write(rowdoline, 54, doline.product_id and doline.product_id.name or '', c_style) # Product
                    sheet.write(rowdoline, 55, '%d/%d/%d' %(doline.product_uom_qty or 0, doline.reserved_availability or 0, doline.quantity_done or 0), cline_center_style) # Qty Delivery To Customer: product_uom_qty/reserved_availability/quantity_done
                    sheet.write(rowdoline, 56, do.scheduled_date or '', c_style) # Cust. Delivery Date
                    sheet.write(rowdoline, 57, do.signed_do_date or '', c_style) # Rect Dt By Cust.
                    sheet.write(rowdoline, 58, doline.quantity_done or 0, cline_center_style) # VALUES DO
                    rowdoline += 1

                rowdo = rowdoline + 1
            # 
            count_row['rowdo'] = rowdo
        
            # -----------Invoice
            rowinv = row
            for inv in order.invoice_ids:
                sheet.write(rowinv, 59, '%s/%s ' % (inv.number or '', inv.move_id and inv.move_id.name or ''), c_style) # Invoice No.
                sheet.write(rowinv, 60, inv.date_invoice or '', c_style) # Invoice Date
                rowinvline = rowinv
                invline_price_subtotal = 0
                for invline in inv.invoice_line_ids:
                    # -------inisiatif: Product
                    sheet.write(rowinvline, 61, invline.product_id and invline.product_id.name or '', c_style) # Product
                    sheet.write(rowinvline, 62, invline.price_subtotal or 0, num_style) # Invoice Amt
                    invline_price_subtotal += invline.price_subtotal
                    sheet.write(rowinvline, 63, invline.quantity or 0, cline_center_style) # Qty. Invoice To Cust.
                    sheet.write(rowinvline, 64, '' or '', c_style) # Point of Delivery
                    rowinvline += 1
                    
                sheet.write(rowinvline, 62, invline_price_subtotal or 0, subtot_style) #Total Invoice Amt
                rowinvline += 1
                
                
                rowinv = rowinvline + 1
            # 
            count_row['rowinv'] = rowinv
            # 
            row = max([v for k,v in count_row.items()])
            sheet.merge_range(row, 0, row, 64, '', cboard_style)
            row += 1
            seq += 1
