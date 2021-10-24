# -*- coding: utf-8 -*-

from odoo import api, models, fields
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class management_xlsx(models.AbstractModel):
    _name = 'report.ati_pti_sales.management_xlsx'
    _inherit = 'report.report_xlsx.abstract'


    def _get_so(self, objects):
        if objects.date_from and objects.date_to:
            domain = [('team_id','=',objects.team_ids.id),('create_date','>=',objects.date_from),('create_date','<=',objects.date_to)]
        else:
            domain = [('team_id','=',objects.team_ids.id)]

        return self.env['sale.order'].sudo().search(domain).sorted(key=lambda r: (r.name))

    def _get_inquiry_remaining_days_grouping(self, inquiry_due_date = False, date_as = False, client_order_date_ref=False):
        days, grouping, status = 0, 'inquiry date is null', ''
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
                grouping = 'Others'
        
        if inquiry_due_date:
            if date_as <= inquiry_due_date and not client_order_date_ref:
                status = 'On-Progress'
            elif  date_as > inquiry_due_date and not client_order_date_ref:
                status = 'Overdue'
            elif client_order_date_ref:
                status = 'Done'
            else:
                status = 'Others'
            
        return days, grouping, status


    # def _get_po(self, order):
    #     return self.env['purchase.order'].sudo().search([('sale_id','=',order.id),('state','!=','cancel')])

    # # def _get_skep_pib(self,formalities=False):
    # def _get_skep_pib(self,order=False,pline=False):
    #     skep_no, skep_line_no, pib_no, pib_item_no, pib_values = '', '', '', '', 0
    #     # if formalities:
    #     #     skep_no, skep_line_no, pib_no, pib_item_no, pib_values = formalities.skep_no or '', formalities.skep_line_no or '', formalities.pib_no or '', formalities.pib_line_no or '', formalities.pib_nilai_barang or 0
    #     return skep_no, skep_line_no, pib_no, pib_item_no, pib_values


    # def _get_wh_in(self, pline=False,picking_ids=False):
    #     pl_no = []
    #     # for pick in picking_ids.filtered(lambda r: r.state == 'done'):
    #     for pick in picking_ids:
    #         if pick.move_lines.filtered(lambda l: l.product_id.id == pline.product_id.id):
    #             pl_no.append(pick.carrier_tracking_ref if pick.carrier_tracking_ref else '')
    #     return ','.join(pl_no)

    # def _msg_date(self, order=False, po=False):
    #     if order and po:
    #         msg = ''
    #         for sol in order.order_line.sorted(key=lambda r: r.sequence2):
    #             for p in po:
    #                 for pol in p.order_line.filtered(lambda p: p.product_id.id == sol.product_id.id):
    #                     time = False
    #                     if sol.requested_date and pol.rts_date:
    #                         time = (fields.Datetime.from_string(sol.requested_date) - fields.Datetime.from_string(pol.rts_date))
    #                     requested_date = datetime.strptime(sol.requested_date,"%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y") if sol.requested_date else ''
    #                     rts_date = datetime.strptime(pol.rts_date,"%Y-%m-%d").strftime("%d-%m-%Y") if pol.rts_date else ''
    #                     msg += '=>P/N:%s (Requested Date: %s, RTS Date: %s, interval hari: %s)' % (sol.product_id.default_code or '', requested_date, rts_date, time.days if time else '')
    #     return msg  

    # def _get_doc(self, order=False):
    #     docs = ''
    #     for doc in order.doc_ids:
    #         docs += '(%s,%s,%s),' % (doc.document_checklist_type_id and doc.document_checklist_type_id.name or '',doc.remark, datetime.strptime(doc.date,"%Y-%m-%d").strftime("%d-%m-%Y"))              
    #     return docs

    # def _get_formalities(self,order=False):
    #     return self.env['skep.pib'].sudo().search([('sale_id','=', order.id)])


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
        sheet.merge_range(1,0,1,9, 'MANAGEMENT REPORT ', t_style)
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
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "CUSTOMER ITEM LINE DUE DATE DELIVERY", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO REMAINING/OVERDUE DAYS TO DELIVER TO CUSTOMER", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO DELIVERY DATE GROUPING", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "DELIVERY DATE GROUPING", h_style)
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
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "P/N PO", h_style)
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
        
        # _FLAGE_DEFAULT = {'blank':'Blank','umbrella_contract':'Umbrella Contract','budgetary':'Budgetary'}
        # _DEFAULT_GET = {'yes':'YES','no':'NO'}

        row = 6
        seq = 1
        count_row_so = {'sol': 0,'pol': 0, 'rec': 0, 'formalities': 0, 'do': 0,'inv': 0}
        for order in self._get_so(objects):
            # if not order:
            #     continue
            # msg = 'Perhatian!!!.'
            # if not order.picking_ids:
            #     msg += '=> SO: %s ini belum ada DO' % (order.name or '')
            # if not order.invoice_ids and order.picking_ids:
            #     msg += '=>  SO: %s ini sudah ada DO tetapi belum dilakukan invoice'
            
            count_row_so = {'sol': 0,'pol': 0, 'rec': 0,'formalities': 0,'do': 0,'inv': 0}
            sheet.write(row, 0, seq or '', c_style) #Number
        
            # so line
            count_row_so['sol'] = len(order.order_line)
            # rowline = row
            # for sol in order.order_line.sorted(key=lambda r: (r['sequence2'])): 
            #     # sheet.write(rowline, 11, sol.old_part_number or '', c_style) # PN
            #     sheet.write(rowline, 11, sol.product_id and sol.product_id.default_code or '', c_style) # PN
            #     sheet.write(rowline, 12, sol.name or '', c_style) # DESC
            #     sheet.write(rowline, 13, sol.product_uom_qty or '', cline_center_style) # QTY
            #     sheet.write(rowline, 14, sol.price_unit or '', num_style) # INQUIRY UNIT PRICE
            #     sheet.write(rowline, 15, sol.price_subtotal or '', num_style) # INQUIRY TOTAL AMOUNT
            #     sheet.write(rowline, 16, order.x_iqo_number or '', cline_center_style) # PTI IQO SO (OLD SYSTEM)
            #     sheet.write(rowline, 17, order.quotation_number, c_style) # PTI QUOT NO
            #     sheet.write(rowline, 18, datetime.strptime(order.final_quotasion_date,"%Y-%m-%d").strftime("%d-%m-%Y") if order.final_quotasion_date else '', c_style) # PTI QUOT DATE
            #     sheet.write(rowline, 19, order.final_quotasion_no if order.final_quotasion_no else '', c_style) # PTI FINAL QUOT NO
            #     sheet.write(rowline, 20, datetime.strptime(order.final_quotasion_date,"%Y-%m-%d").strftime("%d-%m-%Y") if order.final_quotasion_date else '', c_style) # PTI FINAL QUOT DATE
            #     sheet.write(rowline, 21, order.final_quotasion_amount or 0, c_style) # PTI FINAL QUOT AMOUNT
            #     sheet.write(rowline, 22, self._get_doc(order), c_style) # CUSTOMER PO AMANDMEND
            #     sheet.write(rowline, 23, _DEFAULT_GET[order.hard_copy_recv] if order.hard_copy_recv else '', c_style) # PO HARD COPY RECV (Y/N)
            #     sheet.write(rowline, 24, datetime.strptime(order.hard_copy_date,"%Y-%m-%d").strftime("%d-%m-%Y") if order.hard_copy_date else '', c_style) # PO HARD COPY RECV DATE
            #     # sheet.write(rowline, 25, order.name or '', c_style) # PTI ERP SO NO
            #     sheet.write(rowline, 26, datetime.strptime(order.client_order_date_ref,"%Y-%m-%d").strftime("%d-%m-%Y") if order.client_order_date_ref else '', c_style) # PTI ERP SO Date
            #     sheet.write(rowline, 27, order.client_order_ref or '', c_style) # CUSTOMER ORDER NO
            #     sheet.write(rowline, 28, len(order.order_line) if order.order_line else 0, cline_center_style) # TOTAL ITEM LINE EACH PO
            #     sheet.write(rowline, 29, sol.sequence2 or 0, cline_center_style) # PO ITEM LINE NO
            #     sheet.write(rowline, 30, sol.product_id and sol.product_id.default_code or '', c_style) # P/N PO
            #     sheet.write(rowline, 31, sol.name or '', c_style) # PO ITEM DESCRIPTION
            #     sheet.write(rowline, 32, sol.product_uom_qty or 0, cline_center_style) # QTY PO
            #     sheet.write(rowline, 33, sol.product_uom and sol.product_uom.name or '', cline_center_style) # UOM PO
            #     sheet.write(rowline, 34, sol.price_unit or 0, num_style) # PRICE
            #     sheet.write(rowline, 35, sol.price_subtotal or 0, num_style) # VALUES
            #     sheet.write(rowline, 36, datetime.strptime(order.client_order_date_ref,"%Y-%m-%d").strftime("%d-%m-%Y") if order.client_order_date_ref else '', cline_center_style) # CUSTOMER ORDER DATE
            #     sheet.write(rowline, 37, datetime.strptime(sol.requested_date,"%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y") if sol.requested_date else '', cline_center_style) # CUSTOMER ORDER DATE
            #     sheet.write(rowline, 38, order.batch_delivery or '', c_style) # BATCH DELIVERY
            #     if sol.requested_date:
            #         time = (fields.Datetime.from_string(objects.date_as) - fields.Datetime.from_string(sol.requested_date))
            #         msg += '=> P/N: %s ini memiliki masa due date: %s hari' %(sol.product_id.default_code or '', time.days)
            #     if not sol.requested_date:
            #         msg += '=> P/N: %s ini tidak mencantumkan Requested Date' %(sol.product_id.default_code or '')

            #     rowline += 1

            # # -------po-----------
            # # count_row_so['pol'] = 0
            # # count_row_so['fomalities'] = 0
            # # so: requested date vs po: rt date
            # msg_date_so_po = self._get_po(order)
            # if msg_date_so_po:
            #     msg += self._msg_date(order, msg_date_so_po)

            # rowpo = row
            # rowpoline = row
            # rowpickline = row
            # for p in self._get_po(order):
            #     # 
            #     len_max_pline_or_whinline = max([
            #                                     len(p.order_line.filtered(lambda t: t.product_id.type != 'service')),
            #                                     sum([len(whin.move_lines) for whin in p.picking_ids])
            #                                     ])
            #     for len_po in range(len_max_pline_or_whinline):
            #         sheet.write(rowpo, 39, '%s ' %(p.partner_ref or ''), c_style) # SOLAR PO NO
            #         sheet.write(rowpo, 40,  datetime.strptime(p.vendor_date,"%Y-%m-%d").strftime("%d-%m-%Y") if p.vendor_date else '' or '', c_style) # SP DATE
            #         rowpo += 1
            #     # count_row_so['pol'] += len(p.order_line)
            #     # exception product type : service
            #     # count_row_so['pol'] += len(p.order_line.filtered(lambda t: t.product_id.type != 'service'))
            #     count_row_so['pol'] += len_max_pline_or_whinline
            #     for pline in p.order_line.filtered(lambda t: t.product_id.type != 'service').sorted(key=lambda r: (r['sequence'])):
            #         # 
            #         sheet.write(rowpoline, 41, pline.sequence or 0, c_style) # LINE SP SOLAR
            #         sheet.write(rowpoline, 42, pline.product_id and pline.product_id.default_code or '', c_style) # PART NO
            #         sheet.write(rowpoline, 43, pline.name or '', c_style) # SP ITEM DESCRIPTION
            #         sheet.write(rowpoline, 44, pline.product_qty or 0, cline_center_style) # QTY
            #         sheet.write(rowpoline, 45, datetime.strptime(pline.rts_date,"%Y-%m-%d").strftime("%d-%m-%Y") if pline.rts_date else '', c_style) # RTS
                    
            #         rowpoline += 1
        
            #     # WH/IN
            #     for picking in p.picking_ids.filtered(lambda s: s.state != 'cancel'):
            #         count_row_so['rec'] += len(picking.move_lines.filtered(lambda wh: wh.quantity_done != 0))
            #         for pick_moveline in picking.move_lines.filtered(lambda wh: wh.quantity_done != 0):
            #             sheet.write(rowpickline, 59, picking.carrier_tracking_ref or '', c_style) # P/L NO
            #             sheet.write(rowpickline, 60, pick_moveline.move_picking_sequence or 0, c_style) # RECV ITEM LINE NO
            #             sheet.write(rowpickline, 61, pick_moveline.product_id.default_code or '', c_style) # RECV PN NO
            #             sheet.write(rowpickline, 62, pick_moveline.name or '', c_style) # RECV DESCRIPTION
            #             sheet.write(rowpickline, 63, pick_moveline.quantity_done or 0, cline_center_style) # RECV QTY
            #             sheet.write(rowpickline, 64, datetime.strptime(picking.scheduled_date,"%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y") if picking.scheduled_date else '', c_style) # RECV DATE/ Scheduled Date
            #             rowpickline += 1
                
            #     rowpo = rowpoline = rowpickline = max([rowpo,rowpoline,rowpickline])

            # # FORMALITIES 
            # rowf = row
            # rowskep = row
            # rowpib = row
            # for formal in self._get_formalities(order=order):
            #     len_max_skepline_or_pibline = max([len(formal.skep_ids),sum([len(pib.pib_line_ids) for pib in formal.pib_ids])])
            #     for len_skep in range(len_max_skepline_or_pibline):
            #         sheet.write(rowf, 46, _DEFAULT_GET[order.dap_doc] if order.dap_doc else '', c_style) # DAP SUPPORTING DOC
            #         sheet.write(rowf, 47, datetime.strptime(order.dap_doc_date,"%Y-%m-%d").strftime("%d-%m-%Y") if order.dap_doc_date else '', c_style) # DAP SUPPORTING DOC SUBMIT DATE
            #         sheet.write(rowf, 48, formal.skep_no or '', c_style) # SKEP NO
            #         sheet.write(rowf, 49, datetime.strptime(formal.skep_date,"%Y-%m-%d").strftime("%d-%m-%Y") if formal.skep_date else '', c_style) # SKEP DATE
            #         sheet.write(rowf, 50, datetime.strptime(formal.skep_recv_date,"%Y-%m-%d").strftime("%d-%m-%Y") if formal.skep_recv_date else '', c_style) # SKEP RECV DATE
            #         rowf += 1
            #     count_row_so['formalities'] += len_max_skepline_or_pibline
            #     for skep in formal.skep_ids:
            #         # sheet.write(rowpoline, 46, formal.skep_no or '', c_style) # SKEP NO
            #         sheet.write(rowskep, 51, skep.seq_skep or 0, cline_center_style) # SKEP line NO
            #         sheet.write(rowskep, 52, skep.product_id and skep.product_id.default_code or '', c_style) # PN
            #         sheet.write(rowskep, 53, skep.skep_qty or 0, cline_center_style) # Qty SKEP
            #         rowskep += 1
            #         # 
            #     for pib in formal.pib_ids:
            #         for pibline in pib.pib_line_ids:
            #             sheet.write(rowpib, 54, pib.pib_no or '', c_style) # PIB NO
            #             sheet.write(rowpib, 55, pibline.seq_pib or 0, cline_center_style) # PIB ITEM/Line NO
            #             sheet.write(rowpib, 56, pibline.product_id and pibline.product_id.default_code or '', c_style) # PN
            #             sheet.write(rowpib, 57, pibline.pib_qty or 0, cline_center_style) # Qty PIB
            #             sheet.write(rowpib, 58, pibline.pib_item_values or 0, c_style) # PIB VALUES
            #             rowpib += 1
            #     # set row to be paralel 
            #     rowskep = rowpib = max([rowskep,rowpib])
            
            # # -----------WH/OUT : DO
            # # count_row_so['do'] = 0
            
            # # exception return do and wh/in
            # except_return_do_ids = []
            # for erd in order.picking_ids.filtered(lambda rdo: rdo.name[0:5] in ('WH/IN','Wh/In','wh/in')):
            #     except_return_do_ids.append(erd.id)
            #     for erdwhin in order.picking_ids.filtered(lambda rdor: rdor.name == erd.origin.split()[-1]): 
            #         except_return_do_ids.append(erdwhin.id)

            # rowdo = row
            # rowdoline = row
            # for do in order.picking_ids.filtered(lambda d: d.id not in except_return_do_ids and d.state != 'cancel'):
            #     # for len_do in range(len(do.move_lines)):
            #     #     sheet.write(rowdo, 60, '%s ' % (do.name or ''), c_style) # PTI DO NO
            #     #     rowdo += 1
            #     count_row_so['do'] += len(do.move_lines.filtered(lambda rdol: rdol.quantity_done != 0))
            #     for doline in do.move_lines.filtered(lambda rdol: rdol.quantity_done != 0).sorted(key=lambda r: r.move_picking_sequence):
            #         sheet.write(rowdoline, 65, '%s ' % (do.name or ''), c_style) # PTI DO NO
            #         sheet.write(rowdoline, 66, doline.move_picking_sequence or 0, c_style) # DO ITEM LINE NO
            #         sheet.write(rowdoline, 67, doline.product_id.default_code or '', c_style) # PART NO DO
            #         sheet.write(rowdoline, 68, doline.name or '', c_style) # ITEM DESC DO
            #         sheet.write(rowdoline, 69, doline.quantity_done or 0, cline_center_style) # QTY DO
            #         sheet.write(rowdoline, 70, datetime.strptime(do.scheduled_date,"%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y") if do.scheduled_date else '', c_style) # DO DATE
            #         sheet.write(rowdoline, 71, datetime.strptime(do.signed_do_date,"%Y-%m-%d").strftime("%d-%m-%Y") if do.signed_do_date else '', c_style) # DO RECV DATE
            #         rowdoline += 1

            # # -----------Invoice
            # # count_row_so['inv'] = 0
            # rowinv = row
            # rowinvline = row
            # for inv in order.invoice_ids.filtered(lambda r: r.state in ('draft','open','paid')):
            #     for len_inv in range(len(inv.invoice_line_ids)):
            #         sheet.write(rowinv, 72, '%s ' % (inv.number or '' if inv.state != 'draft' else inv.number_draft or ''), c_style) # PTI INV NO
            #         sheet.write(rowinv, 73, datetime.strptime(inv.date_invoice,"%Y-%m-%d").strftime("%d-%m-%Y") if inv.date_invoice else '', c_style) # PTI INV DATE
            #         rowinv += 1
            #     count_row_so['inv'] += len(inv.invoice_line_ids)
            #     for invline in inv.invoice_line_ids:
            #         sheet.write(rowinvline, 74, invline.sequence or 0, c_style) # INV ITEM LINE NO
            #         sheet.write(rowinvline, 75, invline.product_id and invline.product_id.default_code or '', c_style) # PN INV
            #         sheet.write(rowinvline, 76, invline.name or '', c_style) # ITEM DESC INV
            #         qty_inv = 0
            #         values_invoice = 0
            #         if inv.state != 'draft':
            #             qty_inv = invline.quantity if inv.number and inv.number[:2] not in ['CN','Cn','cn'] else -1 * invline.quantity
            #             values_invoice = invline.price_subtotal if inv.number and inv.number[:2] not in ['CN','Cn','cn'] else -1 * invline.price_subtotal
            #         sheet.write(rowinvline, 77, invline.quantity if inv.state == 'draft' else qty_inv, cline_center_style) # QTY INV
            #         sheet.write(rowinvline, 78, invline.price_subtotal if inv.state == 'draft' else values_invoice, num_style) # VALUES INVOICE
            #         rowinvline += 1
                    
            #
            # sheet.merge_range(row, 0, row - 1 + max([v for k,v in count_row_so.items()]), 0, seq or '', c_style) #Number
            
            rowheadso = row
            for len_sol in range(max([v for k,v in count_row_so.items()])):
                sheet.write(rowheadso, 1, order.quotation_number or '', c_style) # PTI QUOT NO
                sheet.write(rowheadso, 2, order.partner_id.name or '', c_style) # CUSTOMER NAME
                sheet.write(rowheadso, 3, order.client_order_ref or '', c_style) # CUSTOMER ORDER NO
                sheet.write(rowheadso, 4, datetime.strptime(order.inquiry_due_date,"%Y-%m-%d").strftime("%d-%m-%Y") if order.inquiry_due_date else '', c_style) # INQUIRY DUE DATE
                inquiry_remaining_days, inquiry_remaining_days_grouping, quotation_status = self._get_inquiry_remaining_days_grouping(inquiry_due_date = order.inquiry_due_date, date_as = objects.date_as, client_order_date_ref = order.client_order_date_ref)
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
            # sheet.write(row, 79, msg, c_style)       
            # sheet.merge_range(row, 0, row, 62, '', cboard_style)       
            row += count_row
            seq += 1

