# -*- coding: utf-8 -*-

from odoo import api, models, fields
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class sales_due_delivery_xlsx(models.AbstractModel):
    _name = 'report.ati_pti_sales.sales_due_delivery_xlsx'
    _inherit = 'report.report_xlsx.abstract'



    def _get_so(self, objects):
        state = self._get_state(objects)
        so = self.env['sale.order'].sudo().search([('team_id','in',objects.crm_team_ids.ids),('state','in',state)])
        return so

    def _get_default_code_so_line(self, so=False):
        dc = set(so.order_line.sorted(key=lambda s: s.sequence2).mapped('product_id.default_code'))
        dict_seq_dc = {}
        for line in list(dc):
            seq = {line: min(so.order_line.filtered(lambda r: r.product_id.default_code == line).mapped('sequence2'))} 
            dict_seq_dc.update(seq)

        # sorted
        default_code = []
        for seq_dc in sorted(dict_seq_dc.items(), key=lambda k: k[1]):
            default_code.append(seq_dc[0])

        return default_code

    def _get_po(self, so):
        po = self.env['purchase.order'].sudo().search([('sale_id','=',so.id)])
        po_filter = self.env['purchase.order'].sudo()
        for p in self.env['purchase.order'].sudo().search([('sale_id','=',so.id)]):
            for p_line in p.order_line:
                if p_line.product_id.default_code in so.order_line.mapped('product_id.default_code'):
                    po_filter |= p
                    break
        return po_filter

    def _get_state(self, objects):
        state = ['sale','delivery','waiting_invoice','waiting_payment']
        if objects.is_done:
            state.append('done')
        return state

    def _choosen_range(self, objects, num_days=0):
        group_due_date = ''
        if objects.is_choice_1 and objects.range_1_from <= num_days and objects.range_1_to >= num_days:
            group_due_date = str(objects.range_1_from) + ' - ' + str(objects.range_1_to) + ' Days'
        elif objects.is_choice_2 and objects.range_2_from < num_days and objects.range_2_to >= num_days:
            group_due_date = str(objects.range_2_from) + ' - ' + str(objects.range_2_to) + ' Days'
        elif objects.is_choice_3 and objects.range_3_from < num_days and objects.range_3_to >= num_days:
            group_due_date = str(objects.range_3_from) + ' - ' + str(objects.range_3_to) + ' Days'
        elif objects.is_choice_4 and objects.range_4_from < num_days and objects.range_4_to >= num_days:
            group_due_date = str(objects.range_4_from) + ' - ' + str(objects.range_4_to) + ' Days'
        elif objects.is_choice_5 and objects.range_5_from < num_days:
            group_due_date = '> ' + str(objects.range_5_from) + ' Days'
        elif objects.is_choice_6 and num_days < 0:
            group_due_date = 'Overdue'
        else:
            pass

        return group_due_date
    
    def _do_status(self, do, dc_sline, s, total):
        do_status = ''
        sline = sum(s.order_line.filtered(lambda sl: sl.product_id.default_code == dc_sline).mapped('product_uom_qty'))
        if total == 0:
            do_status = 'No Delivery'
        elif sline == total:
            do_status = 'Complete'
        elif total < sline:
            do_status = 'Partial'
        elif total > sline:
            do_status = 'Qty Delivered > Qty SO'
        else:
            pass
        return do_status


    # @api.model
    def generate_xlsx_report(self, workbook, data, objects):
        sheet_name = 'Due Delivery Div 21 Sparepart'
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.set_footer('&R&6&"Courier New,Italic"Page &P of &N', {'margin': 0.25})
        column_width = [6,35,20,25,30,20,25,20,35] + [20]*14
        column_width = column_width
        for col_pos in range(0,len(column_width)):
            sheet.set_column(col_pos, col_pos, column_width[col_pos])


        # TITLE
        t_cell_format = {'font_name': 'Arial', 'font_size': 12, 'bold': True, 'valign': 'vcenter', 'align': 'left'}
        t_style = workbook.add_format(t_cell_format)
        sheet.merge_range(0,0,0,22, 'PT. INDOTURBINE', t_style)
        sheet.merge_range(1,0,1,22, 'Report Due Delivery Div-21 Spare Part', t_style)
        sheet.merge_range(2,0,2,22, 'Report as of: '+ str(datetime.strptime(objects.date,"%Y-%m-%d").strftime("%d-%m-%Y")), t_style)
        # default h_style
        h_cell_format = {'font_name': 'Arial', 'font_size': 10, 'bold': True, 'valign': 'vcenter', 'align': 'center', 'border': 1, 'bg_color':'#d9d9d9'}
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
        num_cell_format.update({'align': 'right', 'num_format':'#,##0;-#,##0;-'})
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
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Customer Name", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SO No.", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Customer Reference.", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SO Requested Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Days Before Due", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Grouping Due Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SO Seq No", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Part Number", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Qty Ordered SO", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "SO UOM", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO No. (Qty)", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO Seq No", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO Scheduled Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO Qty", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "PO UOM", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "RTS Date", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Receive Number", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Receive Qty", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Receive UOM", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "DO Number", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "DO Status", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "Qty Delivered", h_style)
        h_col += 1
        sheet.merge_range(h_row, h_col, h_row+1,h_col, "DO UOM", h_style)

        sheet.panes_frozen = True
        sheet.freeze_panes(6, 3)
        
        

        row = 6
        seq = 1
        # 
        so = self._get_so(objects)
        # 
        for team in objects.crm_team_ids:
            for s in so.filtered(lambda r: r.team_id.id == team.id):
                # time = False
                # if s.commitment_date:
                #     time = (fields.Datetime.from_string(s.commitment_date) - fields.Datetime.from_string(objects.date))
                # else:
                #     continue

                # group_due_date = self._choosen_range(objects,time.days)
                # if group_due_date == '':
                #     continue
                    
                for dc_sline in self._get_default_code_so_line(so=s):
                    # sol = s.order_line.filtered(lambda dc: dc.product_id.default_code == dc_sline)
                    sol = s.order_line.filtered(lambda dc: dc.product_id.default_code == dc_sline).sorted(key=lambda s: s.sequence2)
                    time = 0
                    for request_date in sol:
                        if request_date.requested_date:
                            time = (fields.Datetime.from_string(request_date.requested_date) - fields.Datetime.from_string(objects.date)).days
                        else:
                            continue
                            
                    group_due_date = self._choosen_range(objects,time)
                    if group_due_date == '':
                        continue
                     
                    sheet.write(row, 0, seq or '', c_style) # No.
                    sheet.write(row, 1, s.partner_id.name if s.partner_id.name else s.partner_id.parent_id.name or '', c_style) # Sales
                    sheet.write(row, 2, s.name or '', c_style) # SO Number
                    sheet.write(row, 3, s.client_order_ref or '', c_style) # Cust Ref
                    sheet.write(row, 4, ', '.join(set([datetime.strptime(date.requested_date,"%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y") for date in sol if date.requested_date])) or '', c_style) # Promised Delivery Date
                    # 
                    sheet.write(row, 5, time or 0, c_style) # Days Before Due
                    # sheet.write(row, 6, group_due_date, c_style) # Grouping Due Date
                    #sheet.write(row, 5, '', c_style) # Days Before Due
                    sheet.write(row, 6, group_due_date, c_style) # Grouping Due Date
                    sheet.write(row, 7, ', '.join([str(seq2) for seq2 in sol.mapped('sequence2')]) or '', c_style) # SO Seq No
                    sheet.write(row, 8, 'P/N: %s, %s' % (dc_sline or '', ','.join([prod.name for prod in sol]) or ''), c_style) # Part Number
                    sheet.write(row, 9, sum(sol.mapped('product_uom_qty')) or 0, num_style) # Qty Ordered SO
                    # sheet.write(row, 10, ', '.join(set([uom.product_uom.name + ' (' + str(int(uom.product_uom_qty)) + ')' for uom in sol])) or '', c_style) # UOM Qty Ordered SO
                    sheet.write(row, 10, ', '.join([uom.product_uom.name + ' (' + str(int(uom.product_uom_qty)) + ')' for uom in sol]) or '', c_style) # UOM Qty Ordered SO
                    # PO
                    po = self._get_po(s)
                    rts_date = []
                    rcv_qty = 0
                    po_qty = 0
                    po_uom = []
                    po_uom_qty = []
                    rts_date_max = False
                    po_number = []
                    quantity_po = 0
                    rts_date_po = []
                    seq_po = []
                    po_ids = []
                    for po_rts in po.sorted(key=lambda p: p.id):
                        filter_default_code = po_rts.order_line.filtered(lambda p: p.product_id.default_code == dc_sline and p.product_qty > 0)
                        if not filter_default_code:
                            continue

                        x = filter_default_code
                        quantity_po += sum(filter_default_code.mapped('product_qty'))
                        rcv_qty += sum(filter_default_code.mapped('qty_received'))
                        po_qty += sum(filter_default_code.mapped('product_qty'))
                        #po_uom += filter_default_code.mapped('product_uom.name')
                        po_uom += [po_uom.product_uom.name + ' (' + str(int(po_uom.product_qty)) +')' for po_uom in filter_default_code] 
                        z = [rd.rts_date for rd in filter_default_code if rd.rts_date]
                        rts_date_po.append([po_rts.name,max(z) if z else False])
                        seq_po.append([po_rts.name,filter_default_code.mapped('sequence')])
                        po_number.append(po_rts.name + ' (' + str(int(quantity_po)) + ')' )
                        po_ids.append(po_rts.id)

                    sheet.write(row, 11,', '.join(set(po_number)) if po_qty > 0 else '', c_style) # PO No (Qty)
                    sheet.write(row, 12,', '.join([','.join(list(map(lambda a: str(a),k[1])))+ ' ('+ k[0] + ')' for k in seq_po ]) if po_qty > 0 else '', c_style) # PO Seq No
                    sheet.write(row, 13,', '.join([datetime.strptime(dp.date_planned,"%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y") for dp in po.filtered(lambda i: i.id in po_ids).sorted(key=lambda pl: pl.id) if dp.date_planned]) if po_qty > 0 else '', c_style) # PL Date
                    sheet.write(row, 14, po_qty or 0, num_style) # PO Qty
                    sheet.write(row, 15, ', '.join(po_uom), c_style) # UOM Qty Ordered PO
                    date_var = [m for m in rts_date_po]
                    date_join = [str(datetime.strptime(d[1],"%Y-%m-%d").strftime("%d-%m-%Y")) if d and d[1] else '' + ' ('+ d[0] + ')' for d in rts_date_po]
                    sheet.write(row, 16,', '.join([str(datetime.strptime(d[1],"%Y-%m-%d").strftime("%d-%m-%Y")) + ' ('+ d[0] + ')' for d in rts_date_po if d and d[1]]), c_style) # RTS Date

                    picking_name = []
                    picking_quantity_done = 0
                    receive_uom = []
                    for po_picking in po:
                        for picking in po_picking.picking_ids:
                            picking_lines = picking.filtered(lambda p: p.state == 'done').move_lines.filtered(lambda q: q.product_id.default_code == dc_sline)
                            if picking_lines:
                                quantity_done = sum(picking_lines.mapped('quantity_done'))
                                #receive_uom += picking_lines.mapped('product_uom.name')
                                receive_uom += [rcv_uom.product_uom.name + ' (' + str(rcv_uom.quantity_done) + ')' for rcv_uom in picking_lines]
                                picking_name.append(picking.name+' ('+str(quantity_done)+')')
                                picking_quantity_done += quantity_done
                    
                    do_name = []
                    delivery_order_done = 0
                    delivery_order_done_return = 0
                    do_uom = []
                    for so_delivery_order in s:
                        for delivery_order in so_delivery_order.picking_ids.filtered(lambda do_head: do_head.state == 'done'):
                            delivery_order_line = delivery_order.filtered(lambda do: do.state == 'done' and (do.is_do == True and do.name[:2] == "DO") or (do.name[:6] == "WH/OUT" or do.name[:7] == "PLB/OUT")).move_lines.filtered(lambda do: do.product_id.default_code == dc_sline)
                            delivery_order_line_return = delivery_order.filtered(lambda do: do.state == 'done' and (do.name[:5] == "WH/IN" or do.name[:6] == "PLB/IN")).move_lines.filtered(lambda do: do.product_id.default_code == dc_sline)
                            if delivery_order_line:
                                quantity_done = sum(delivery_order_line.mapped('quantity_done'))
                                delivery_order_done += quantity_done
                                do_name.append(delivery_order.name+' ('+str(quantity_done)+')')
                                do_uom += [dol.product_uom.name + ' (' + str(dol.quantity_done) + ')' for dol in delivery_order_line]
                            if delivery_order_line_return:
                                quantity_done_return = sum(delivery_order_line_return.mapped('quantity_done'))
                                delivery_order_done_return += quantity_done_return
                                do_name.append(delivery_order.name+' ('+str(quantity_done_return)+')')
                                do_uom += [dolr.product_uom.name + ' (' + str(dolr.quantity_done) + ')' for dolr in delivery_order_line_return]
                    
                    total = delivery_order_done - delivery_order_done_return
                        
                    sheet.write(row, 17, ', '.join(picking_name), c_style) # Receive Number
                    sheet.write(row, 18, picking_quantity_done or 0, num_style) # Receive QTY
                    sheet.write(row, 19, ', '.join(receive_uom) or '', c_style) # UOM Receive Qty
                    sheet.write(row, 20, ', '.join(do_name), c_style) # DO Number
                    status = self._do_status(s.picking_ids, dc_sline, s, total)
                    sheet.write(row, 21, status or '', c_style) # DO Status
                    sheet.write(row, 22, total or 0, num_style) # qty_delivered
                    sheet.write(row, 23,', '.join(do_uom) or '', c_style) # UOM qty_delivered


                    row += 1
                    seq += 1