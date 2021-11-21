# -*- coding: utf-8 -*-

from typing import Sequence
from odoo import api, models, fields
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class management_xlsx(models.AbstractModel):
    _name = 'report.ati_pti_sales.management_xlsx'
    _inherit = 'report.report_xlsx.abstract'


    def _get_so(self, objects):
        domain = [('state','!=','cancel')]
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


    def _get_po(self, order):
        return self.env['purchase.order'].sudo().search([('sale_id','=',order.id),('state','!=','cancel')])

    def _get_skep_and_nor_to_due_date(self, nor_date=False,sol_pol=False):
        skep_no = ''
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
            
        # skep
        for s in sol_pol:
            for d in s.skep_pib_ids:
                skep_no += d.skep_no

        return skep_no, days, grouping

    def _get_collected_status(self, po=False, pol=False, objects=False):
        actual_item_to_be_collected_status = 'N/A'
        # a. Not Ready From Solar =  Jika belum melewati RTS dan belum ada NoR
        # b. Ready to Collect = Jika item sudah ada NoR nya
        # c. Collected = Ketika barang sudah diambil dari warehouse Solar dan sedang menuju Jakarta.
        # d. RTS Overdue : Jika sudah melewati tanggal RTS namun masih belum ada NoR
        summary_nor_goods = self.env['summary.nor.goods'].sudo().search([('purchase_id','=',po.id),('position','=',pol.sequence),('product_id.default_code','=',pol.product_id.default_code)], limit=1)
        if summary_nor_goods:
            if summary_nor_goods.nor_state == 'no':
                if pol and pol.rts_date:
                    if pol.rts_date <= objects.date_as:
                        actual_item_to_be_collected_status = 'Not Ready From Solar'
                    elif pol.rts_date > objects.date_as:
                        actual_item_to_be_collected_status = 'RTS Overdue'
                else:
                    actual_item_to_be_collected_status = 'N/A'
                return actual_item_to_be_collected_status

            elif summary_nor_goods.nor_state == 'yes':
                pickup_goods_line = self.env['pickup.goods.line'].sudo().search([('purchase_order_line_id','=',pol.id)], limit=1) 
                if pickup_goods_line and pickup_goods_line.pickup_id.state == 'confirmed':
                    actual_item_to_be_collected_status = 'Collected'
                elif summary_nor_goods.nor_state == 'yes':
                    actual_item_to_be_collected_status = 'Ready To Collect'
                else:
                    actual_item_to_be_collected_status = 'N/A'

                return actual_item_to_be_collected_status

        return actual_item_to_be_collected_status

    def _get_pararam_whin(self, arrival_date=False, date_as=False, receive_date=False):
        eta_remaining, eta_remaining_grouping,days_staged, days_staged_grouping = 0, 'N/A', 0, 'N/A'
        if arrival_date and date_as:
            eta_remaining = (fields.Datetime.from_string(arrival_date) - fields.Datetime.from_string(date_as)).days
            if eta_remaining >= -15:
                eta_remaining_grouping = '0-15 Days at Narogong'
            elif -30 <= eta_remaining < -15:
                eta_remaining_grouping = '16-30 Days at Narogong'
            elif -90 <= eta_remaining < -30:
                eta_remaining_grouping = '31-90 Days at Narogong'
            elif -180 < eta_remaining < -90:
                eta_remaining_grouping = '91-180 Days at Narogong'
            elif eta_remaining < -180:
                eta_remaining_grouping = '>180 Days at Narogong'
            else:
                eta_remaining_grouping = 'N/A'

        if receive_date and date_as:
            days_staged = (fields.Datetime.from_string(receive_date) - fields.Datetime.from_string(date_as)).days
            
            if days_staged >= -15:
                days_staged_grouping = '0-15 Days at Narogong'
            elif -30 <= days_staged < -15:
                days_staged_grouping = '16-30 Days at Narogong'
            elif -90 <= days_staged < -30:
                days_staged_grouping = '31-90 Days at Narogong'
            elif -180 < days_staged < -90:
                days_staged_grouping = '91-180 Days at Narogong'
            elif days_staged < -180:
                days_staged_grouping = '>180 Days at Narogong'
            else:
                days_staged_grouping = 'N/A'

        return eta_remaining, eta_remaining_grouping,days_staged, days_staged_grouping

    def _get_actual_inventory_status(self, po=False,pol=False,so=False,pick_moveline=False):
        # Delivered = ketika barang sudah keluar/dikirimkan dari narogong ke customer >> Qty Delivered = Qty Order di di SO Line
        # Partial Delivery = ketika barang sudah keluar/dikirimkan dari narogong ke customer >> Qty Delivered < Qty Order di di SO Line
        # Prepare = ketika barang sudah ada di Narogong/warehouse namun belum dikirim ke customer >> WH/IN Qty Done > 0 atau Qty Received > 0 di PO Line
        # Not Ready (default state)
        actual_inventory_status = 'Not Ready'
        sol = so.order_line.filtered(lambda s: s.product_id.default_code == pol.product_id.default_code and s.sequence2 == pol.sequence)
        if sol:
            if sol.product_uom_qty == sol.qty_delivered:
                actual_inventory_status = 'Delivered'
            elif sol.product_uom_qty > sol.qty_delivered:
                actual_inventory_status = 'Partial Delivery'
            elif pick_moveline.quantity_done > 0 or pol.qty_received > 0:
                actual_inventory_status = 'Prepare'
            else:
                actual_inventory_status = 'Not Ready'
        return actual_inventory_status 
    
    def _get_actual_item_tobe_deliver_status(self, so=False, doline=False):
        # Delivered = ketika barang sudah keluar/dikirimkan dari narogong ke customer >> Qty Delivered = Qty Order di di SO Line
        # Partial Delivery = ketika barang sudah keluar/dikirimkan dari narogong ke customer >> Qty Delivered < Qty Order di di SO Line
        # Prepare = ketika barang sudah ada di Narogong/warehouse namun belum dikirim ke customer >> WH/IN Qty Done > 0 atau Qty Received > 0 di PO Line
        # Not Ready (default state)
        actual_item_tobe_deliver_status = 'Not Ready'
        sol = so.order_line.filtered(lambda s: s.product_id.default_code == doline.product_id.default_code and s.sequence2 == doline.move_picking_sequence)
        po = self.env['purchase.order'].sudo().search([('sale_id','=',so.id)], limit=1)
        pol = po.order_line.filtered(lambda p: p.product_id.default_code == doline.product_id.default_code and p.sequence == doline.move_picking_sequence)
        if sol:
            if sol.product_uom_qty == sol.qty_delivered:
                actual_item_tobe_deliver_status = 'Delivered'
            elif sol.product_uom_qty > sol.qty_delivered:
                actual_item_tobe_deliver_status = 'Partial Delivery'
            elif pol.qty_received > 0:
                actual_item_tobe_deliver_status = 'Prepare'
            else:
                actual_item_tobe_deliver_status = 'Not Ready'

        return actual_item_tobe_deliver_status

    def _get_param_whout(self, scheduled_date = False, date_as = False):
        do_remaining, do_remaining_grouping = 0,'N/A'
        if scheduled_date and date_as:
            do_remaining = (fields.Datetime.from_string(scheduled_date) - fields.Datetime.from_string(date_as)).days
            if 0 < do_remaining <= 90:
                do_remaining_grouping = '0-90 Days'
            elif 90 < do_remaining <= 120: 
                do_remaining_grouping = '91-120 Days'
            elif do_remaining > 120:
                do_remaining_grouping = '>120 Days'
            else:
                do_remaining_grouping = 'N/A'            

        return do_remaining, do_remaining_grouping

    def _get_value_invoice(self, do=False, dol=False, so=False, date_as=False):
        value_invoice, due_date_invoice, invoice_remaining_days, invoice_remaining_days_grouping = 0, False, 0, 'N/A' 
        if dol and so:
            sol = so.order_line.filtered(lambda r: r.sequence2 == dol.move_picking_sequence and r.product_id.default_code == dol.product_id.default_code)
            value_invoice = dol.quantity_done * sol.price_unit

        # due_date_invoice
        if do.signed_do_date:
            due_date_invoice = datetime.strptime(do.signed_do_date,DEFAULT_SERVER_DATE_FORMAT) + timedelta(days=90)
        # invoice due date
        if date_as and due_date_invoice:
            invoice_remaining_days = (fields.Datetime.from_string(fields.Datetime.to_string(due_date_invoice)) - fields.Datetime.from_string(date_as)).days  

        # grouping
        if 1 <= invoice_remaining_days <= 15:
            invoice_remaining_days_grouping = '1 - 15'
        elif 15 < invoice_remaining_days <= 30:
            invoice_remaining_days_grouping = '16 - 30'
        elif 30 < invoice_remaining_days <= 60:
            invoice_remaining_days_grouping = '31 - 60'
        elif 60 < invoice_remaining_days <= 90:
            invoice_remaining_days_grouping = '61 - 90'
        elif 90 < invoice_remaining_days <= 120:
            invoice_remaining_days_grouping = '91 - 120'
        elif invoice_remaining_days > 120:
            invoice_remaining_days_grouping = '121 ABOVE'
        elif invoice_remaining_days < 1:
            invoice_remaining_days_grouping = '0 Days: OVERDUE'
        else:
            invoice_remaining_days_grouping = 'N/A'

        return value_invoice, due_date_invoice, invoice_remaining_days, invoice_remaining_days_grouping

    def _get_status_shipping(self,po=False):
        status_shipping = 'N/A'

        if po:
            if all([p.load_code != False and p.load_code != '' for p in po.order_line]):
                status_shipping = 'COMPLETE'
            elif any([p.load_code != False and p.load_code != '' for p in po.order_line]):
                status_shipping = 'PARTIAL'
            else:
                status_shipping = 'N/A'

        return status_shipping 

    def  _get_actual_invoice_status(self, do=False,invoice=False):
        # Paid  = Ketika customer sudah melakukan pembayaran invoice >> Status AR = Paid
        # ??? Paid Partial = Ketika customer sudah melakukan pembayaran invoice >> Status AR = Open, ada payment dan juga masih ada Amount Due
        # Done = Ketika invoice sudah dibuat dan disubmit ke customer melalui finance >> AR Sudah di Validate >> Status AR = Open
        # Prepare Invoice = Ketika invoice sedang proses dipersiapkan untuk diberikan customer (reconcile supporting document) >> Status AR = Draft
        # Not Ready (default state)
        actual_invoice_status = 'Not Ready'
        ids = []
        for inv in invoice:
            for d in inv.picking_ids:
                if d.id == do.id:
                    if inv.state == 'paid':
                        actual_invoice_status = 'Paid'
                    elif inv.state == 'open':
                        actual_invoice_status = 'Done'
                    elif inv.state == 'draft':
                        actual_invoice_status = 'Prepare Invoice'
                    else:
                        actual_invoice_status = 'Not Ready'

        return actual_invoice_status 


    # @api.model
    def generate_xlsx_report(self, workbook, data, objects):
        sheet_name = 'Management Report'
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
        sheet.merge_range(1,0,1,9, 'MANAGEMENT REPORT : %s' %(objects.team_ids.name), t_style)
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
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PTI QUOT NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER NAME.", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER ORDER NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "INQUIRY DUE DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "INQUIRY REMAINING DAYS", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "INQUIRY REMAINING DAYS", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "QUOTATION STATUS", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "YEAR", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER ORDER DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PTI IQOZ SO NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "INCOTERM", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SEQUENCE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PN", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "QTY", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "UOM", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER ITEM LINE DUE DATE DELIVERY", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO REMAINING/OVERDUE DAYS TO DELIVER TO CUSTOMER", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO DELIVERY DATE GROUPING", h_style)
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
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "RTS", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SOLAR PO NO (SP)", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "DESC", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SEQUENCE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "P/N PO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "QTY", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "UOM", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SKEP NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "P/L NO - SOLAR LOAD CODE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "NOR DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "REMAINING DAYS OF NOR TO PO DUE DATE DELIVERY", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "REMAINING DAYS GROUPING", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ACTUAL ITEM TO BE COLLECTED STATUS", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PARTIAL OR COMPLETE ITEMS SHIPPING", h_style)
        h_col += 1

        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SEQUENCE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "P/N", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "QTY DONE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "UOM", h_style)
        h_col += 1
        
        
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ETA AT NAROGONG WH", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ETA REMAINING DAYS AT NAROGONG WH", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ETA REMAINING DAYS GROUPING AT NAROGONG WH", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ACTUAL RECEIVING DATE AT NAROGONG WH", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "DAYS STAGED AT NAROGONG", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "DAYS STAGED AT NAROGONG (GROUPING)", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ACTUAL INVENTORY STATUS", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "DESC", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PTI DO NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SEQUENCE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "P/N", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "QTY DONE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "UOM", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ESTIMATED WH-OUT DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ITEM TO BE DELIVER REMAINING DAYS", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ITEM TO BE DELIVER REMAINING DAYS GROUPING", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ACTUAL ITEM TO BE DELIVER STATUS", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "VALUE INVOICE (IDR)", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "VALUE INVOICE (USD)", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "DO RECV DATE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "DUE DATE INVOICE (90 DAYS AFTER DO SIGNED)", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "INVOICE REMAINING DAYS", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "INVOICE REMAINING DAYS GROUPING", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ACTUAL INVOICE STATUS", h_style)
        h_col += 1

        sheet.panes_frozen = True
        sheet.freeze_panes(6, 4)
        
        row = 6
        seq = 1
        count_row_so = {'sol': 0,'pol': 0, 'rec': 0, 'formalities': 0, 'do': 0,'inv': 0}
        for order in self._get_so(objects):            
            count_row_so = {'sol': 0,'pol': 0, 'rec': 0,'formalities': 0,'do': 0,'inv': 0}
            sheet.write(row, 0, seq or '', c_style) #Number
            # so line
            # count_row_so['sol'] = len(order.order_line)
            count_row_so['sol'] = len(order.order_line.filtered(lambda r: r.product_id.type != 'service'))
            rowline = row
            for sol in order.order_line.filtered(lambda r: r.product_id.type != 'service').sorted(key=lambda r: (r['sequence2'])): 
                sheet.write(rowline, 12, sol.sequence2  or 0, cline_center_style) # SEQUENCE
                sheet.write(rowline, 13, sol.product_id and sol.product_id.default_code or '', c_style) # PN
                sheet.write(rowline, 14, sol.product_uom_qty or 0, cline_center_style) # QTY
                sheet.write(rowline, 15, sol.product_uom.name or '', cline_center_style) # UOM
                sheet.write(rowline, 16, datetime.strptime(sol.requested_date,DEFAULT_SERVER_DATETIME_FORMAT).strftime("%d-%m-%Y") if sol.requested_date else '', c_style) # CUSTOMER ITEM LINE DUE DATE DELIVERY
                po_remaining, po_remaining_grouping, po_remaining_grouping_monthly,po_overdue_category, actual_po_delivery_status  = self._get_po_remaining(order_line=sol, due_date_delivery=sol.requested_date, date_as = objects.date_as)
                # po requested date line ???
                sheet.write(rowline, 17, po_remaining or 0, cline_center_style) # PO REMAINING/OVERDUE DAYS TO DELIVER TO CUSTOMER
                sheet.write(rowline, 18, po_remaining_grouping , cline_center_style) # PO DELIVERY DATE GROUPING
                sheet.write(rowline, 19, po_remaining_grouping_monthly, cline_center_style) # DELIVERY DATE GROUPING(MONTHLY)
                sheet.write(rowline, 20, po_overdue_category, cline_center_style) # PO OVERDUE CATEGORY
                sheet.write(rowline, 21, actual_po_delivery_status, c_style) # ACTUAL PO DELIVERY STATUS

                sheet.write(rowline, 22, sol.currency_id.name if sol.currency_id else '', c_style) # USD/IDR
                sheet.write(rowline, 23, sol.price_subtotal if sol.currency_id.name in ('IDR','idr','Idr') else 0, num_style) # VALUE (IDR)
                sheet.write(rowline, 24, sol.price_subtotal if sol.currency_id.name in ('USD','usd','Isd') else 0, num_style) # VALUE (USD)
                # sheet.write(rowline, 25, datetime.strptime(sol.requested_date,"%Y-%m-%d").strftime("%d-%m-%Y") if sol.requested_date else '', c_style) # RTS

                rowline += 1

            # # -------po-----------
            count_row_so['pol'] = 0
            # # count_row_so['fomalities'] = 0
            # # so: requested date vs po: rt date
            rowpo = row
            rowpoline = row
            rowpickline = row
            for p in self._get_po(order):
                # 
                len_max_pline_or_whinline = max([
                                                len(p.order_line.filtered(lambda t: t.product_id.type != 'service')),
                                                sum([len(whin.move_lines) for whin in p.picking_ids])
                                                ])

                
                # count_row_so['pol'] += len(p.order_line)
                # exception product type : service
                # count_row_so['pol'] += len(p.order_line.filtered(lambda t: t.product_id.type != 'service'))
                count_row_so['pol'] += len_max_pline_or_whinline
                for pline in p.order_line.filtered(lambda t: t.product_id.type != 'service').sorted(key=lambda r: (r['sequence'])):
                    # 
                    sheet.write(rowpoline, 25,datetime.strptime(pline.rts_date,"%Y-%m-%d").strftime("%d-%m-%Y") if pline.rts_date else '', c_style) # RTS
                    sheet.write(rowpoline, 26, '%s ' %(pline.partner_ref or ''), c_style) # SOLAR PO NO (SP)
                    sheet.write(rowpoline, 27, '%s ' %(pline.name or ''), c_style) # DESC
                    sheet.write(rowpoline, 28, '%s ' %(pline.sequence or 0), cline_center_style) # SEQUENCE
                    sheet.write(rowpoline, 29, '%s ' %(pline.product_id.default_code or ''), c_style) # P/N PO
                    sheet.write(rowpoline, 30, '%s ' %(pline.product_qty or ''), cline_center_style) # QTY
                    sheet.write(rowpoline, 31, '%s ' %(pline.product_uom.name or ''), cline_center_style) # UOM
                    skep_no, remaining_days_nor_to_due, nor_due_grouping = self._get_skep_and_nor_to_due_date(nor_date=pline.nor_date,sol_pol=p.sale_id.order_line.filtered(lambda l: l.sequence2 == pline.sequence and l.product_id.default_code == pline.product_id.default_code))
                    sheet.write(rowpoline, 32, skep_no, c_style) # SKEP NO
                    sheet.write(rowpoline, 33, '%s ' %(pline.load_code or ''), c_style) # P/L NO - SOLAR LOAD CODE
                    sheet.write(rowpoline, 34, datetime.strptime(pline.nor_date,"%Y-%m-%d").strftime("%d-%m-%Y") if pline.nor_date else '', c_style) # NOR DATE
                    sheet.write(rowpoline, 35, remaining_days_nor_to_due, c_style) # REMAINING DAYS OF NOR TO PO DUE DATE DELIVERY
                    sheet.write(rowpoline, 36, nor_due_grouping, c_style) # REMAINING DAYS GROUPING
                    actual_item_to_be_collected_status = self._get_collected_status(po=p, pol=pline, objects=objects)
                    sheet.write(rowpoline, 37, actual_item_to_be_collected_status, c_style) # ACTUAL ITEM TO BE COLLECTED STATUS
                    status_shipping = self._get_status_shipping(po=p)
                    sheet.write(rowpoline, 38, status_shipping, c_style) # PARTIAL OR COMPLETE ITEMS SHIPPING

                    rowpoline += 1
        
                # WH/IN
                for picking in p.picking_ids.filtered(lambda s: s.state != 'cancel'):
                    count_row_so['rec'] += len(picking.move_lines.filtered(lambda wh: wh.quantity_done != 0))
                    for pick_moveline in picking.move_lines.filtered(lambda wh: wh.quantity_done != 0):
                        sheet.write(rowpickline, 39, pick_moveline.move_picking_sequence or 0, cline_center_style) # SEQUENCE
                        sheet.write(rowpickline, 40, pick_moveline.product_id.default_code or '', c_style) # P/N
                        sheet.write(rowpickline, 41, pick_moveline.quantity_done or 0, cline_center_style) # QTY DONE
                        sheet.write(rowpickline, 42, pick_moveline.product_uom.name or '', cline_center_style) # UOM
                
                        sheet.write(rowpickline, 43, datetime.strptime(picking.custom_clearance_id.arrival_date,DEFAULT_SERVER_DATETIME_FORMAT).strftime("%d-%m-%Y") if picking.custom_clearance_id and picking.custom_clearance_id.arrival_date else '', c_style) # ETA AT NAROGONG WH
                        eta_remaining, eta_remaining_grouping,days_staged, days_staged_grouping = self._get_pararam_whin(arrival_date = picking.custom_clearance_id.arrival_date, date_as = objects.date_as, receive_date=picking.scheduled_date) 
                        sheet.write(rowpickline, 44, eta_remaining, c_style) # ETA REMAINING DAYS AT NAROGONG WH
                        sheet.write(rowpickline, 45, eta_remaining_grouping, c_style) # ETA REMAINING DAYS GROUPING AT NAROGONG WH
                        sheet.write(rowpickline, 46, datetime.strptime(picking.custom_clearance_id.arrival_date,DEFAULT_SERVER_DATETIME_FORMAT).strftime("%d-%m-%Y") if picking.custom_clearance_id and picking.custom_clearance_id.arrival_date else '', c_style) # ACTUAL RECEIVING DATE AT NAROGONG WH
                        sheet.write(rowpickline, 47, days_staged, c_style) # DAYS STAGED AT NAROGONG
                        sheet.write(rowpickline, 48, days_staged_grouping, c_style) # DAYS STAGED AT NAROGONG (GROUPING)
                        actual_inventory_status = self._get_actual_inventory_status(po=p,pol=pick_moveline.purchase_line_id,so=p.sale_id, pick_moveline=pick_moveline)
                        sheet.write(rowpickline, 49, actual_inventory_status, c_style) # ACTUAL INVENTORY STATUS
                        sheet.write(rowpickline, 50, pick_moveline.name or '', c_style) # DESC

                        rowpickline += 1
                
                rowpo = rowpoline = rowpickline = max([rowpo,rowpoline,rowpickline])
            
            # -----------WH/OUT : DO
            count_row_so['do'] = 0
            
            # exception return do and wh/in
            except_return_do_ids = []
            for erd in order.picking_ids.filtered(lambda rdo: rdo.name[0:5] in ('WH/IN','Wh/In','wh/in')):
                except_return_do_ids.append(erd.id)
                for erdwhin in order.picking_ids.filtered(lambda rdor: rdor.name == erd.origin.split()[-1]): 
                    except_return_do_ids.append(erdwhin.id)

            rowdo = row
            rowdoline = row
            for do in order.picking_ids.filtered(lambda d: d.id not in except_return_do_ids and d.state != 'cancel'):
                # for len_do in range(len(do.move_lines)):
                #     sheet.write(rowdo, 60, '%s ' % (do.name or ''), c_style) # PTI DO NO
                #     rowdo += 1
                count_row_so['do'] += len(do.move_lines.filtered(lambda rdol: rdol.quantity_done != 0))
                for doline in do.move_lines.filtered(lambda rdol: rdol.quantity_done != 0).sorted(key=lambda r: r.move_picking_sequence):
                    sheet.write(rowdoline, 51, '%s ' % (do.name or ''), c_style) # PTI DO NO
                    sheet.write(rowdoline, 52, doline.move_picking_sequence or 0, c_style) # SEQUENCE
                    sheet.write(rowdoline, 53, doline.product_id.default_code or '', c_style) # P/N
                    sheet.write(rowdoline, 54, doline.quantity_done or 0, c_style) # QTY DONE
                    sheet.write(rowdoline, 55, doline.product_uom.name or '', c_style) # UOM
                    sheet.write(rowdoline, 56, datetime.strptime(do.scheduled_date,DEFAULT_SERVER_DATETIME_FORMAT).strftime("%d-%m-%Y") if do.scheduled_date else '', c_style) # ESTIMATED WH-OUT DATE
                    do_remaining, do_remaining_grouping = self._get_param_whout(scheduled_date=do.scheduled_date, date_as = objects.date_as)
                    sheet.write(rowdoline, 57, do_remaining, c_style) # ITEM TO BE DELIVER REMAINING DAYS
                    sheet.write(rowdoline, 58, do_remaining_grouping, c_style) # ITEM TO BE DELIVER REMAINING DAYS GROUPING
                    actual_item_tobe_deliver_status = self._get_actual_item_tobe_deliver_status(so=order, doline=doline)
                    sheet.write(rowdoline, 59, actual_item_tobe_deliver_status, c_style) # ACTUAL ITEM TO BE DELIVER STATUS
                    value_invoice, due_date_invoice, invoice_remaining_days, invoice_remaining_days_grouping  = self._get_value_invoice(do=do,dol=doline, so=order, date_as=objects.date_as)
                    sheet.write(rowdoline, 60, value_invoice if doline.currency_id.name in ('IDR','idr','Idr') else 0, num_style) # VALUE INVOICE (IDR)
                    sheet.write(rowdoline, 61, value_invoice if doline.currency_id.name in ('USD','usd','Usd') else 0, num_style) # VALUE INVOICE (USD)
                    sheet.write(rowdoline, 62,  datetime.strptime(do.signed_do_date,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y") if do.signed_do_date else '', c_style) # DO RECV DATE
                    sheet.write(rowdoline, 63,  datetime.strptime( fields.Datetime.to_string(due_date_invoice),DEFAULT_SERVER_DATETIME_FORMAT).strftime("%d-%m-%Y") if due_date_invoice else '', c_style) # DUE DATE INVOICE (90 DAYS AFTER DO SIGNED)
                    sheet.write(rowdoline, 64,  invoice_remaining_days, c_style) # INVOICE REMAINING DAYS
                    sheet.write(rowdoline, 65,  invoice_remaining_days_grouping, c_style) # INVOICE REMAINING DAYS GROUPING
                    actual_invoice_status = self._get_actual_invoice_status(do=do,invoice=order.invoice_ids)
                    sheet.write(rowdoline, 66, actual_invoice_status, c_style) # ACTUAL INVOICE STATUS

                    rowdoline += 1


            rowheadso = row
            for len_sol in range(max([v for k,v in count_row_so.items()])):
                sheet.write(rowheadso, 1, order.quotation_number or '', c_style) # PTI QUOT NO
                sheet.write(rowheadso, 2, order.partner_id.name or '', c_style) # CUSTOMER NAME
                sheet.write(rowheadso, 3, order.client_order_ref or '', c_style) # CUSTOMER ORDER NO
                sheet.write(rowheadso, 4, datetime.strptime(order.inquiry_due_date,"%Y-%m-%d").strftime("%d-%m-%Y") if order.inquiry_due_date else '', c_style) # INQUIRY DUE DATE
                inquiry_remaining_days, inquiry_remaining_days_grouping, quotation_status = self._get_inquiry_remaining_days_grouping(so = order, inquiry_due_date = order.inquiry_due_date, date_as = objects.date_as, client_order_date_ref = order.client_order_date_ref)
                sheet.write(rowheadso, 5, inquiry_remaining_days or 0, c_style) # INQUIRY REMAINING DAYS
                sheet.write(rowheadso, 6, inquiry_remaining_days_grouping or '', c_style) # INQUIRY REMAINING DAYS GROUPING
                sheet.write(rowheadso, 7, quotation_status or '', c_style) # QUOTATION STATUS
                sheet.write(rowheadso, 8, datetime.strptime(order.create_date, DEFAULT_SERVER_DATETIME_FORMAT).year if order.create_date else '', c_style) # YEAR
                sheet.write(rowheadso, 9, datetime.strptime(order.client_order_date_ref,"%Y-%m-%d").strftime("%d-%m-%Y") if order.client_order_date_ref else '', c_style) # CUSTOMER ORDER DATE
                sheet.write(rowheadso, 10, order.name or '', c_style) # PTI IQOZ SO NO
                sheet.write(rowheadso, 11, order.transaction_method_id.name or '', c_style) # INCOTERM
                
                rowheadso += 1
            # 
            count_row = max([v for k,v in count_row_so.items()])
            # sheet.merge_range(row, 0, row, 62, '', cboard_style)       
            row += count_row
            seq += 1

