# -*- coding: utf-8 -*-

from typing import Sequence
from odoo import api, models, fields
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class item_arriving_xlsx(models.AbstractModel):
    _name = 'report.ati_pti_sales.item_arriving_xlsx'
    _inherit = 'report.report_xlsx.abstract'


    def _get_shipment(self, objects):
        domain = []
        if objects.date_from and objects.date_to:
            domain += [('create_date','>=',objects.date_from),('create_date','<=',objects.date_to)]

        return self.env['awb.bl'].sudo().search(domain)

    def _get_custom_clearance(self):
        domain = []
        return self.env['custom.clearance'].sudo().search(domain)

    def _get_departure_or_arrival_date(self, awbbl=False):
            departure,arrival,final_port_dest = '','','N/A'
            if awbbl.bill_type == 'awb':
                departure = ','.join([datetime.strptime(rec.departure_date,DEFAULT_SERVER_DATETIME_FORMAT).strftime("%d-%m-%Y") for rec in awbbl.awb_transit_history_ids if rec.departure_date])
                arrival = ','.join([datetime.strptime(rec.arrival_date,DEFAULT_SERVER_DATETIME_FORMAT).strftime("%d-%m-%Y") for rec in awbbl.awb_transit_history_ids if rec.arrival_date])
            elif awbbl.bill_type == 'bl':
                departure = ','.join([datetime.strptime(rec.departure_date,DEFAULT_SERVER_DATETIME_FORMAT).strftime("%d-%m-%Y") for rec in awbbl.bl_transit_history_ids if rec.departure_date])
                arrival = ','.join([datetime.strptime(rec.arrival_date,DEFAULT_SERVER_DATETIME_FORMAT).strftime("%d-%m-%Y") for rec in awbbl.bl_transit_history_ids if rec.arrival_date])
                final_port_dest = ','.join([rec.final_destination.name for rec in awbbl.bl_transit_history_ids if rec.final_destination])
            else:
                departure, arrival = 'N/A','N/A'

            return departure, arrival, final_port_dest

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

    def _get_cc_1(self, awbbl=False):
        customs_storage_clearance,eta_customs_bc16, actual_arrival_date_custom_bc16 = 'N/A','N/A','N/A'
        custom_clearance = self.env['custom.clearance'].sudo().search([('awb_bl_id','=',awbbl.id),('state','!=','cancelled')])
        customs_storage_clearance = ','.join([rec.hoarding_place for rec in custom_clearance])
        eta_customs_bc16 = ','.join([datetime.strptime(rec.arrival_date,DEFAULT_SERVER_DATETIME_FORMAT).strftime("%d-%m-%Y") for rec in custom_clearance if rec.arrival_date])
        actual_arrival_date_custom_bc16 = ','.join([datetime.strptime(rec.arrival_date,DEFAULT_SERVER_DATETIME_FORMAT).strftime("%d-%m-%Y") for rec in custom_clearance if rec.arrival_date])
        return customs_storage_clearance, eta_customs_bc16, actual_arrival_date_custom_bc16


    def _get_cc_2(self, awbbl=False, purchase=False):
        custom_clearance = self.env['custom.clearance'].sudo().search([('awb_bl_id','=',awbbl.id),('state','!=','cancelled')])
        return custom_clearance

    def _get_wh(self, picking=False, pol=False):
        self._get_wh(picking=goods.purchase_id.picking_ids.filtered(lambda k: k.state != 'cancel' and k.custom_clearance_id.id == cc.id), pol=goods.purchase_order_line_id)

        return
    
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
        sheet_name = 'Item Arriving To Narogong Report'
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
        sheet.merge_range(1,0,1,9, 'ITEM ARRIVING TO NAROGONG REPORT : %s' %(objects.team_ids.name), t_style)
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
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Shipment Ref No.", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Shipment Ref Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "APPLIED AIR / SEA FREIGHT SHIPMENT", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Number of Airway Bill / Bill of Lading", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Actual Time Flight Departure", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Actual Time Flight Arrival", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER NAME", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "P/L NO (WJ)", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Partial or Complete Items Shipping", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER ORDER NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PTI IQOZ SO NO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SOLAR PO NO (SP)", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "VALUES", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "FINAL PORT DESTINATION", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMS STORAGE FOR CLEARENCE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ETA TO CUSTOMS BC.16 STORAGE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ACTUAL ARRIVAL DATE TO CUSTOMS BC.16 STORAGE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SKEP AVAILABLE", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "COMPLETE OR PARTIAL APPROVED ITEMS ON SKEP", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "BC.28 CLEARENCE RELEASED ITEMS", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ETA AT NAROGONG WH", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ACTUAL RECEIVING DATE AT NAROGONG WH", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ACTUAL PARTIAL OR COMPLETE RECEIVED AT NAROGONG WH", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ETA REMAINING DAYS AT NAROGONG WH", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ETA REMAINING DAYS GROUPING AT NAROGONG WH", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "ACTUAL CARGO HANDLING STATUS", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Cargo Handling REMARKS", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER ITEM LINE DUEDATE DELIVERY", h_style)
        h_col += 1
        
        sheet.panes_frozen = True
        sheet.freeze_panes(6, 4)
        
        row = 6
        seq = 1
        for awbbl in self._get_shipment(objects):
            for inv in awbbl.awb_bl_line_ids:            
                sheet.write(row, 0, seq or '', c_style) #No.
                sheet.write(row, 1, awbbl.job_ref or '', c_style) #Shipment Ref No.
                sheet.write(row, 2, datetime.strptime(awbbl.document_date,DEFAULT_SERVER_DATE_FORMAT).strftime("%d-%m-%Y") if awbbl.document_date else '', c_style) #Shipment Ref Date
                sheet.write(row, 3, awbbl.mode_transport.name or '', c_style) #APPLIED AIR / SEA FREIGHT SHIPMENT
                sheet.write(row, 4, awbbl.name or '', c_style) #Number of Airway Bill / Bill of Lading
                departure, arrival,final_port_dest = self._get_departure_or_arrival_date(awbbl=awbbl)
                sheet.write(row, 5, departure, c_style) #Actual Time Flight Departure
                sheet.write(row, 6, arrival, c_style) #Actual Time Flight Arrival
                sheet.write(row, 7, inv.purchase_id.sale_id.partner_id.name or '', c_style) #CUSTOMER NAME
                sheet.write(row, 8, inv.box_id.commercial_invoice_id.name or '', c_style) #P/L NO (WJ)
                status_shipping = self._get_status_shipping(po=inv.purchase_id)
                sheet.write(row, 9, status_shipping, c_style) #Partial or Complete Items Shipping
                sheet.write(row, 10, inv.client_order_ref or '', c_style) #CUSTOMER ORDER NO
                sheet.write(row, 11, inv.purchase_id.sale_id.name or '', c_style) #PTI IQOZ SO NO
                sheet.write(row, 12, inv.partner_ref or '', c_style) #SOLAR PO NO (SP)
                sheet.write(row, 13, awbbl.total_amount or 0, num_style) #VALUES
                sheet.write(row, 14, final_port_dest, c_style) #FINAL PORT DESTINATION
                custom_storage_clearance, eta_customs_bc16, actual_arrival_date_custom_bc16 = self._get_cc_1(awbbl=awbbl)
                sheet.write(row, 15, custom_storage_clearance or '', c_style) #CUSTOMS STORAGE FOR CLEARENCE
                sheet.write(row, 16, eta_customs_bc16, c_style) #ETA TO CUSTOMS BC.16 STORAGE
                sheet.write(row, 17, actual_arrival_date_custom_bc16, c_style) #ACTUAL ARRIVAL DATE TO CUSTOMS BC.16 STORAGE
                for cc in self._get_cc_2(awbbl=awbbl, purchase=inv.purchase_id):
                    for goods in cc.goods_detail_ids.sorted(key=lambda r: r.sequence):
                        sheet.write(row, 18, goods.skep_pib_id.skep_no or '', c_style) #SKEP AVAILABLE
                        warehourse = self._get_wh(picking=goods.purchase_id.picking_ids.filtered(lambda k: k.state != 'cancel' and k.custom_clearance_id.id == cc.id), pol=goods.purchase_order_line_id)
                        sheet.write(row, 19, '', c_style) #COMPLETE OR PARTIAL APPROVED ITEMS ON SKEP
                        sheet.write(row, 20, '', c_style) #BC.28 CLEARENCE RELEASED ITEMS
                        # skep_no, skep_line_no, skep_date, skep_recv_date, skep_validity_date, pib_no, pib_item_no,pib_values = self._get_skep_info(so=order.sale_id, pol=pol)                
                        # sheet.write(row, 21, skep_no, c_style) #ETA AT NAROGONG WH
                        # sheet.write(row, 22, skep_line_no, cline_center_style) #ACTUAL RECEIVING DATE AT NAROGONG WH
                        # sheet.write(row, 23, skep_date, c_style) #ACTUAL PARTIAL OR COMPLETE RECEIVED AT NAROGONG WH
                        # sheet.write(row, 24, skep_recv_date, c_style) #ETA REMAINING DAYS AT NAROGONG WH
                        # sheet.write(row, 25, skep_validity_date, c_style) #ETA REMAINING DAYS GROUPING AT NAROGONG WH
                        # sheet.write(row, 26, pib_no,c_style) #ACTUAL CARGO HANDLING STATUS
                        # sheet.write(row, 27, pib_item_no, cline_center_style) #Cargo Handling REMARKS
                        # sheet.write(row, 28, pib_values, c_style) #CUSTOMER ITEM LINE DUEDATE DELIVERY

                        row += 1
                        seq += 1