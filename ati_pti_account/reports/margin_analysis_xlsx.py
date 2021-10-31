# -*- coding: utf-8 -*-

from odoo import api, models, fields
# from report_xlsx.report.report_xlsx import ReportXlsx
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import time

class margin_analysis_xlsx(models.AbstractModel):
    _name = 'report.ati_pti_account.margin_analysis_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    

    def _get_acl(self, objects):
        domain = [('date','>=',objects.date_from),('date','<=',objects.date_to),('move_id.state','=','posted')]
        
        # aml = self.env['account.move.line'].sudo().search(domain).filtered(lambda r: str(r.account_id.code[0]) in ('3','4','5','6') and r.move_id.state == 'posted')
        aml = self.env['account.move.line'].sudo().search(domain).filtered(lambda r: str(r.account_id.code[0]) in ('3','4','5','6'))
        
        return aml

    def _get_invoice(self, project=False, objects=False):
        domain = [('project_id','=',project.id),('state','in',('open','paid'))]
        ainv = self.env['account.invoice'].sudo().search(domain).filtered(lambda r: r.move_id.date >= objects.date_from and r.move_id.date <= objects.date_to and r.number[:2] not in ('CN','cn') and r.paid_by_type not in ('refund','other'))
        
        return ainv

    def _get_invoice_by_project(self, objects=False):
        for project in objects.project_ids.sorted(key=lambda r: r.partner_id):
            domain = [('project_id','=',project.id),('state','in',('open','paid'))]
            yield project,self.env['account.invoice'].sudo().search(domain).filtered(lambda r: r.move_id.date >= objects.date_from and r.move_id.date <= objects.date_to and r.number[:2] not in ('CN','cn') and r.paid_by_type not in ('refund','other'))
        

    def _get_payment(self, project=False, invoice=False):
        domain = [('project_id','=',project.id),('invoice_id','=',invoice.id)]
        apinv = self.env['account.payment.invoice'].sudo().search(domain)
        
        return apinv


    def _get_voucher(self,inv=False):
        # 
        voucher_name = inv.move_id and inv.move_id.name or ''
        voucher_date = ''
        # Ref 
        # ref1 = inv.name if inv.type == 'out_invoice' else ''
        ref1 = inv.number or ''
        ref2 = inv.client_order_ref if inv.type == 'out_invoice' else inv.name
        if inv.state == 'paid':
            payment_name = inv.payment_ids.mapped('move_name')
            voucher_name = ','.join(payment_name)
            # 
            payment_date = [str(datetime.strptime(dt,"%Y-%m-%d").strftime("%d/%m/%Y")) for dt in inv.payment_ids.mapped('payment_date')]
            voucher_date = ','.join(payment_date)
            
            return voucher_name, voucher_date, ref1, ref2

        elif inv.state == 'open':
            voucher_name = ''

            return voucher_name, voucher_date, ref1, ref2
            
        else:
            return voucher_name, voucher_date, ref1, ref2

    def _get_projects(self, objects):
        if not objects.project_ids:
            projects = self.env['project.project'].sudo().search([]).filtered(lambda r: r.name not in ('GENERAL','GEN','GENERA','General','Gen'))
            return projects
        else:
            projects = objects.project_ids
            return projects


    def _get_parameter_query(self,acl_penjualan=False,acl_hpp=False,acl_penalty=False,acl_angkut=False,acl_asuransi=False,b_karyawan_fji=False,b_karyawan_fji_bol=False,bp_jual_fji=False,b_lain_fji=False):
        q_penjualan = q_hpp = q_penalty = q_angkut = q_asuransi = 'WHERE id = %s' % (str(0))
        q_pro_b_karyawan_fji = q_pro_b_karyawan_fji_bol = q_pro_bp_jual_fji = q_pro_b_lain_fji = 'WHERE id = %s' % (str(0))

        args = (q_penjualan, q_hpp, q_penalty, q_angkut, q_asuransi,q_pro_b_karyawan_fji, q_pro_b_karyawan_fji_bol, q_pro_bp_jual_fji, q_pro_b_lain_fji)
        if acl_penjualan:
            q_penjualan = 'WHERE id in %s' % (str(tuple(acl_penjualan.ids)) if len(acl_penjualan) > 1 else '('+str(acl_penjualan.id)+')')
        if acl_hpp:
            q_hpp = 'WHERE id in %s' % (str(tuple(acl_hpp.ids)) if len(acl_hpp) > 1 else '('+str(acl_hpp.id)+')')
        if acl_penalty:
            q_penalty = 'WHERE id in %s' % (str(tuple(acl_penalty.ids)) if len(acl_penalty) > 1 else '('+str(acl_penalty.id)+')')
        if acl_angkut:
            q_angkut = 'WHERE id in %s' % (str(tuple(acl_angkut.ids)) if len(acl_angkut) > 1 else '('+str(acl_angkut.id)+')')
        if acl_asuransi:
            q_asuransi = 'WHERE id in %s' % (str(tuple(acl_asuransi.ids)) if len(acl_asuransi) > 1 else '('+str(acl_asuransi.id)+')')
        # direct journal item
        if b_karyawan_fji:
            q_pro_b_karyawan_fji = 'WHERE id in %s' % (str(tuple(b_karyawan_fji.ids)) if len(b_karyawan_fji) > 1 else '('+str(b_karyawan_fji.id)+')')
        if b_karyawan_fji_bol:
            q_pro_b_karyawan_fji_bol = 'WHERE id in %s' % (str(tuple(b_karyawan_fji_bol.ids)) if len(b_karyawan_fji_bol) > 1 else '('+str(b_karyawan_fji_bol.id)+')')
        if bp_jual_fji:
            q_pro_bp_jual_fji = 'WHERE id in %s' % (str(tuple(bp_jual_fji.ids)) if len(bp_jual_fji) > 1 else '('+str(bp_jual_fji.id)+')')
        if b_lain_fji:
            q_pro_b_lain_fji = 'WHERE id in %s' % (str(tuple(b_lain_fji.ids)) if len(b_lain_fji) > 1 else '('+str(b_lain_fji.id)+')')

        args = (q_penjualan,q_hpp,q_penalty,q_angkut,q_asuransi,q_pro_b_karyawan_fji, q_pro_b_karyawan_fji_bol, q_pro_bp_jual_fji, q_pro_b_lain_fji)
        # 
        self._cr.execute("""
                        SELECT penjualan.val AS penjualan, hpp.val AS hpp, penalty.val AS penalty, angkut.val AS angkut, asuransi.val AS asuransi,
                        pro_b_karyawan_fji.val AS pro_b_karyawan_fji, pro_b_karyawan_fji_bol.val AS pro_b_karyawan_fji_bol,pro_bp_jual_fji.val AS pro_bp_jual_fji,pro_b_lain_fji.val AS pro_b_lain_fji
                        FROM
                        (SELECT COALESCE(sum(aml.debit) - sum(aml.credit),0) as val FROM account_move_line AS aml %s) AS penjualan,
                        (SELECT COALESCE(sum(aml.debit) - sum(aml.credit),0) as val FROM account_move_line AS aml %s) AS hpp, 
                        (SELECT COALESCE(sum(aml.debit) - sum(aml.credit),0) as val FROM account_move_line AS aml %s) AS penalty, 
                        (SELECT COALESCE(sum(aml.debit) - sum(aml.credit),0) as val FROM account_move_line AS aml %s) AS angkut, 
                        (SELECT COALESCE(sum(aml.debit) - sum(aml.credit),0) as val FROM account_move_line AS aml %s) AS asuransi,

                        (SELECT COALESCE(sum(aml.debit) - sum(aml.credit),0) as val FROM account_move_line AS aml %s) AS pro_b_karyawan_fji,
                        (SELECT COALESCE(sum(aml.debit) - sum(aml.credit),0) as val FROM account_move_line AS aml %s) AS pro_b_karyawan_fji_bol,
                        (SELECT COALESCE(sum(aml.debit) - sum(aml.credit),0) as val FROM account_move_line AS aml %s) AS pro_bp_jual_fji,
                        (SELECT COALESCE(sum(aml.debit) - sum(aml.credit),0) as val FROM account_move_line AS aml %s) AS pro_b_lain_fji 
                        
                        """ %  args)

        result = self.env.cr.dictfetchall()[0]
        # penjualan, hpp, penalty, angkut, asuransi, pro_b_karyawan_fji, pro_b_karyawan_fji_bol, pro_bp_jual_fji, pro_b_lain_fji
        return result['penjualan'], result['hpp'], result['penalty'], result['angkut'], result['asuransi'], result['pro_b_karyawan_fji'], result['pro_b_karyawan_fji_bol'], result['pro_bp_jual_fji'], result['pro_b_lain_fji']



    def generate_xlsx_report(self, workbook, data, objects):
        project_ids = objects.project_ids
        acl = self._get_acl(objects) 
        sheet_name = 'Detail Margin Analysis' if objects.report_format == 'detail' else 'Summary Margin Analysis'  
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.set_footer('&R&6&"Courier New,Italic"Page &P of &N', {'margin': 0.25})
        column_width = [6,25,25] + [20]*17
        column_width = column_width
        for col_pos in range(0,len(column_width)):
            sheet.set_column(col_pos, col_pos, column_width[col_pos])


        # TITLE
        t_cell_format = {'font_name': 'Arial', 'font_size': 13, 'bold': True, 'valign': 'vcenter', 'align': 'center'}
        t_style = workbook.add_format(t_cell_format)
        t_cell_sub_format = {'font_name': 'Arial', 'font_size': 12, 'bold': False, 'valign': 'vcenter', 'align': 'center'}
        t_sub_style = workbook.add_format(t_cell_sub_format)
        sheet.merge_range(0,0,0,13, 'PT. INDOTURBINE', t_style)
        sheet.merge_range(1,0,1,13, 'Detail Margin Analysis(USD)' if objects.report_format == 'detail' else 'Report Summary Margin Analysis(USD)', t_sub_style)
        sheet.merge_range(2,0,2,13, str(datetime.strptime(objects.date_from,"%Y-%m-%d").strftime("%d/%m/%Y")) +' until '+ str(datetime.strptime(objects.date_to,"%Y-%m-%d").strftime("%d/%m/%Y")), t_sub_style)
        # default h_style
        h_cell_format = {'font_name': 'Arial', 'font_size': 10, 'bold': True, 'valign': 'vcenter', 'align': 'center', 'border': 1, 'bg_color':'#00aaff'}
        h_style = workbook.add_format(h_cell_format)
        # default
        c_cell_format = {'font_name': 'Arial', 'font_size': 9, 'valign': 'top', 'align': 'left', 'border':1}
        c_style = workbook.add_format(c_cell_format)
        # sub default
        c_cell_sub__format = {'font_name': 'Arial', 'font_size': 9, 'valign': 'top', 'align': 'left', 'border':1, 'bold':True, 'bg_color':'#ccffcc'}
        c_sub_style = workbook.add_format(c_cell_sub__format)
        # default number
        num_cell_format = c_cell_format.copy()
        num_cell_format.update({'align': 'right', 'num_format':'#,##0.##;-#,##0.##;-'})
        num_style = workbook.add_format(num_cell_format)
        # subtotal
        num_subtotal_cell_format = c_cell_format.copy()
        num_subtotal_cell_format.update({'align': 'right', 'bold':True, 'num_format':'#,##0.##;-#,##0.##;-','bg_color':'#f0f5f3'})
        num_subtotal_style = workbook.add_format(num_subtotal_cell_format)

        if objects.report_format == 'detail':
            h_row, h_col = 3, 0
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "NO", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Customer", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Voucher", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Date", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Voucher Date", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Ref1", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Ref2", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Penjualan", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Invoice Principl(HPP)", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Penalty", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Biaya Angkut", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Asuransi", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Biaya Karyawan", h_style)
            
            sheet.merge_range(h_row, h_col+1, h_row,h_col+3, "Biaya Operasi Lainnya", h_style)
            h_col +=1
            sheet.write_string(h_row+1, h_col, "B.Karyawan", h_style)
            h_col += 1
            sheet.write_string(h_row+1, h_col, "B.P. Jual", h_style)
            h_col += 1
            sheet.write_string(h_row+1, h_col, "Lain-Lain", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Tanggal", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Cair", h_style)
            
            sheet.panes_frozen = True
            sheet.freeze_panes(5, 7)

            row = 5
            seq = 1

            for pro in self._get_projects(objects):
                # sales team
                sheet.merge_range(row, 0, row, 17, pro.crm_team_id and pro.crm_team_id.name or pro.x_team_id.name or '', c_sub_style)
                row += 1
                customer_inv_from_project = ','.join(list(map(lambda cust_inv_project: cust_inv_project.name or '',pro.invoice_customer_ids.mapped('partner_id')))) if pro.invoice_customer_ids else '' 
                sheet.merge_range(row, 0, row, 17, 'SO: %s        %s        %s ' %(pro.name,pro.partner_id and pro.partner_id.name if pro.partner_id else customer_inv_from_project, pro.subtask_project_id and pro.subtask_project_id.name or ''), c_sub_style)
                # row += 1
                # account.invoice
                invoices = self._get_invoice(pro,objects)
                numb = 1
                tot_penjualan, tot_hpp, tot_penalty, tot_angkut, tot_asuransi, tot_karyawan, = 0,0,0,0,0,0
                type_inv = ('out_invoice','in_invoice')
                for tinv in type_inv:
                    for inv in invoices.filtered(lambda rtinv: rtinv.type == tinv).sorted(key=lambda p: p.partner_id.name):
                        if not inv:
                            continue
                        
                        # account.move.line
                        # Penjualan
                        acl_penjualan = acl.filtered(lambda rinv: rinv.invoice_id.id == inv.id and rinv.account_id.code[0] == '3')
                        penjualan = sum(acl_penjualan.mapped('debit')) - sum(acl_penjualan.mapped('credit'))
                        # print('------penjualan', inv, inv.number, penjualan, acl_penjualan)
                        # HPP
                        acl_hpp = acl.filtered(lambda rinv: rinv.invoice_id.id == inv.id and rinv.account_id.code[:2] in ('41','42'))
                        hpp = sum(acl_hpp.mapped('debit')) - sum(acl_hpp.mapped('credit'))
                        # payment->journal
                        # Penalty
                        # payment = self._get_payment(pro,inv)
                        # acl_penalty = acl.filtered(lambda rinv: rinv.payment_id.id in payment.mapped('payment_id').ids and rinv.account_id.code[:3] in ('526'))
                        acl_penalty = acl.filtered(lambda rinv: rinv.invoice_id.id == inv.id and rinv.account_id.code[:3] in ('526'))
                        penalty = sum(acl_penalty.mapped('debit')) - sum(acl_penalty.mapped('credit'))
                        # B. Angkut
                        # acl_angkut = acl.filtered(lambda rinv: rinv.payment_id.id in payment.mapped('payment_id').ids and rinv.account_id.code[:3] in ('440'))
                        acl_angkut = acl.filtered(lambda rinv: rinv.invoice_id.id == inv.id and rinv.account_id.code[:3] in ('440'))
                        angkut = sum(acl_angkut.mapped('debit')) - sum(acl_angkut.mapped('credit'))
                        # Asuransi
                        # acl_asuransi = acl.filtered(lambda rinv: rinv.payment_id.id in payment.mapped('payment_id').ids and rinv.account_id.code[:3] in ('441'))
                        acl_asuransi = acl.filtered(lambda rinv: rinv.invoice_id.id == inv.id and rinv.account_id.code[:3] in ('441'))
                        asuransi = sum(acl_asuransi.mapped('debit')) - sum(acl_asuransi.mapped('credit'))
                        # B. Karyawan
                        # acl_karyawan = acl.filtered(lambda rinv: rinv.payment_id.id in payment.mapped('payment_id').ids and rinv.account_id.code[:3] in (str(c) for c in range(451,459)))
                        # karyawan = sum(acl_karyawan.mapped('debit')) - sum(acl_karyawan.mapped('credit'))
                        karyawan = 0
                        # gross margin, %
                        gross_margin = sum([penjualan, -hpp, -penalty, -angkut, -asuransi, -karyawan])
                        percent_gross = gross_margin/penjualan * 100 if penjualan != 0 else 0
                        # -----total
                        tot_penjualan += abs(penjualan)
                        tot_hpp += abs(hpp)
                        tot_penalty += abs(penalty)
                        tot_angkut += abs(angkut)
                        tot_asuransi += abs(asuransi)
                        tot_karyawan += abs(karyawan)
                        # Except AP value is zero
                        if penjualan == 0 and hpp == 0 and penalty == 0 and angkut == 0 and asuransi == 0:
                            continue
    
                        # 
                        row += 1
                        sheet.write(row, 0, numb or '', c_style)
                        sheet.write(row, 1, inv.partner_id and inv.partner_id.name if tinv == 'out_invoice' else '', c_style) #Customer
                        # 
                        voucher_name, voucher_date, ref1, ref2 = self._get_voucher(inv)
                        # 
                        sheet.write(row, 2, voucher_name, c_style)#Voucher
                        sheet.write(row, 3, str(datetime.strptime(inv.move_id and inv.move_id.date,"%Y-%m-%d").strftime("%d/%m/%Y")) or '', c_style) #Date
                        sheet.write(row, 4, voucher_date, c_style) #Voucher Date
                        sheet.write(row, 5, ref1 or '',  c_style) #Ref1
                        sheet.write(row, 6, ref2 or '', c_style) #Ref2
                        sheet.write(row, 7, abs(penjualan) or 0, num_style) #Penjualan
                        sheet.write(row, 8, abs(hpp) or 0, num_style) #hpp
                        sheet.write(row, 9, abs(penalty) or 0, num_style) #penalty
                        sheet.write(row, 10, abs(angkut) or 0, num_style) #angkut
                        sheet.write(row, 11, abs(asuransi) or 0, num_style) #asuransi
                        sheet.write(row, 12, abs(karyawan) or 0, num_style) #karyawan
                        sheet.write(row, 13, 0, num_style) #B Karyawan
                        sheet.write(row, 14, 0, num_style) #B.P Jual
                        sheet.write(row, 15, 0, num_style) #Lain - lain
                        sheet.write(row, 16, 0, num_style) # Tanggal
                        sheet.write(row, 17, 0, num_style) # Cair

                        numb += 1
                        # row += 1
                # b.karyawan from journal item /fji
                b_karyawan_fji = acl.filtered(lambda fji:  pro.id in fji.analytic_account_id.project_ids.ids and fji.account_id.code[:3] in (str(c) for c in range(451,459)))
                pro_b_karyawan_fji = sum(b_karyawan_fji.mapped('debit')) - sum(b_karyawan_fji.mapped('credit'))
                # biaya operasional lainnya /bol
                b_karyawan_fji_bol = acl.filtered(lambda fji: pro.id in fji.analytic_account_id.project_ids.ids and fji.account_id.code[:3] in (str(c) for c in range(510,519)))
                pro_b_karyawan_fji_bol = sum(b_karyawan_fji_bol.mapped('debit')) - sum(b_karyawan_fji_bol.mapped('credit'))
                # b.jual from journal item /fji
                bp_jual_fji = acl.filtered(lambda fji: pro.id in fji.analytic_account_id.project_ids.ids and fji.account_id.code[:2] =='52' and fji.account_id.code[:3] !='526')
                pro_bp_jual_fji = sum(bp_jual_fji.mapped('debit')) - sum(bp_jual_fji.mapped('credit'))
                # lain - lain from journal item /fji
                b_lain_fji = acl.filtered(lambda fji: pro.id in fji.analytic_account_id.project_ids.ids and fji.account_id.code[0] in ('5','6') and fji.account_id.code[:3] !='526' and fji.account_id.code[:3] not in (str(c) for c in range(510,519)))
                pro_b_lain_fji = sum(b_lain_fji.mapped('debit')) - sum(b_lain_fji.mapped('credit'))
                # total b.lain
                pro_total_b_lain = sum([pro_b_karyawan_fji_bol,pro_bp_jual_fji,pro_b_lain_fji])
                # 
                if abs(pro_b_karyawan_fji) > 0 or abs(pro_b_karyawan_fji_bol) or abs(pro_bp_jual_fji) or abs(pro_b_lain_fji):
                    customer_inv = ','.join(list(map(lambda n: n.name or '',pro.invoice_customer_ids.mapped('partner_id')))) if pro.invoice_customer_ids else '' 
                    row += 1
                    sheet.write(row, 0, numb or '', c_style)
                    sheet.write(row, 1, pro.partner_id and pro.partner_id.name if pro.partner_id else customer_inv, c_style) #Customer
                    sheet.write(row, 2, '', c_style)#Voucher
                    sheet.write(row, 3, '', c_style) #Date
                    sheet.write(row, 4, '', c_style) #Voucher Date
                    sheet.write(row, 5, '',  c_style) #Ref1
                    sheet.write(row, 6, '', c_style) #Ref2
                    sheet.write(row, 7, 0, num_style) #Penjualan
                    sheet.write(row, 8, 0, num_style) #hpp
                    sheet.write(row, 9, 0, num_style) #penalty
                    sheet.write(row, 10, 0, num_style) #angkut
                    sheet.write(row, 11, 0, num_style) #asuransi
                    sheet.write(row, 12, abs(pro_b_karyawan_fji) or 0, num_style) #karyawan
                    sheet.write(row, 13, abs(pro_b_karyawan_fji_bol) or 0, num_style) #B Karyawan
                    sheet.write(row, 14, abs(pro_bp_jual_fji) or 0, num_style) #B.P Jual
                    sheet.write(row, 15, abs(pro_b_lain_fji) or 0, num_style) #Lain - lain
                    sheet.write(row, 16, 0, num_style) # Tanggal
                    sheet.write(row, 17, 0, num_style) # Cair

                numb += 1
                row += 1
                
                # Total SO
                sheet.merge_range(row, 0, row, 6, 'Total SO', c_style)
                sheet.write(row, 7, tot_penjualan or 0, num_subtotal_style) #Penjualan
                sheet.write(row, 8, tot_hpp or 0, num_subtotal_style) #hpp
                sheet.write(row, 9, tot_penalty or 0, num_subtotal_style) #penalty
                sheet.write(row, 10, tot_angkut or 0, num_subtotal_style) #angkut
                sheet.write(row, 11, tot_asuransi or 0, num_subtotal_style) #asuransi
                sheet.write(row, 12, pro_b_karyawan_fji or 0, num_subtotal_style) #karyawan
                sheet.merge_range(row, 13, row, 17, 0, num_subtotal_style)
                # 
                tot_gross_margin = sum([tot_penjualan,-tot_hpp,-tot_penalty,-tot_angkut,-tot_asuransi,-pro_b_karyawan_fji])
                percent_tot_gross_margin = tot_gross_margin/tot_penjualan * 100 if tot_penjualan != 0 else 0
                # job profit, %
                tot_job_profit = abs(tot_gross_margin) - abs(pro_total_b_lain)
                tot_percent = tot_job_profit/tot_penjualan * 100 if tot_penjualan != 0 else 0
                # Gross Margin 
                row += 1
                sheet.merge_range(row, 0, row, 6, 'Gross Margin', c_style)
                sheet.merge_range(row, 7, row, 17, tot_gross_margin or 0, num_subtotal_style) #Gross Margin
                # Job Profit
                row += 1
                sheet.merge_range(row, 0, row, 6, 'Job Profit', c_style)
                sheet.merge_range(row, 7, row, 17, tot_job_profit or 0, num_subtotal_style) #Gross Margin
                # %
                row += 1
                sheet.merge_range(row, 0, row, 6, 'Percent (%) ', c_style)
                sheet.merge_range(row, 7, row, 17, tot_percent or 0, num_subtotal_style) #Gross Margin

                row += 2

            sheet.merge_range(row,0,row,6, 'Total Divisi', c_style)
            sheet.merge_range(row,7,row,8,len(objects.project_ids.mapped('partner_id').ids) or 0 , num_subtotal_style)

        if objects.report_format == 'summary':

            h_row, h_col = 3, 0
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "NO", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "SO", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Customer", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Penjualan", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Invoice Principl(HPP)", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Penalty", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Biaya Angkut", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Asuransi", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Biaya Karyawan", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Gross Margin", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "%", h_style)
            
            sheet.merge_range(h_row, h_col+1, h_row,h_col+4, "Biaya Operasi Lainnya", h_style)
            h_col +=1
            sheet.write_string(h_row+1, h_col, "B.Karyawan", h_style)
            h_col += 1
            sheet.write_string(h_row+1, h_col, "B.P. Jual", h_style)
            h_col += 1
            sheet.write_string(h_row+1, h_col, "Lain-Lain", h_style)
            h_col += 1
            sheet.write_string(h_row+1, h_col, "Total B.Lain", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, "Job Profit", h_style)
            h_col += 1
            sheet.merge_range(h_row, h_col, h_row+1,h_col, " % ", h_style)
            # h_col += 1

            # sheet.merge_range(h_row, h_col, h_row+1,h_col, "Tanggal", h_style)
            # h_col += 1
            # sheet.merge_range(h_row, h_col, h_row+1,h_col, "Cair", h_style)
            
            sheet.panes_frozen = True
            sheet.freeze_panes(5, 3)

            row = 5
            seq = 1
            # initial grand total
            g_tot_penjualan, g_tot_hpp, g_tot_penalty, g_tot_angkut, g_tot_asuransi, g_tot_karyawan, = 0,0,0,0,0,0
            g_tot_b_karyawan_fji_bol,g_tot_bp_jual_fji, g_tot_b_lain_fji, g_tot_total_b_lain = 0,0,0,0
            # 
            t0 = time.clock()
            # optimization_acl = acl
            optimization_acl = acl


            # for pro in objects.project_ids.sorted(key=lambda r: r.partner_id):
            acl_penjualan = acl_hpp = acl_penalty = acl_angkut = acl_asuransi = b_karyawan_fji = b_karyawan_fji_bol = bp_jual_fji = b_lain_fji = self.env['account.move.line'].sudo()
            # self._get_parameter_query(acl_penjualan,acl_hpp,acl_penalty,acl_angkut,acl_asuransi)
            
            for pro,invoices in self._get_invoice_by_project(objects):
                # # sales team
                # sheet.merge_range(row, 0, row, 16, pro.crm_team_id and pro.crm_team_id.name or pro.x_team_id.name or '', c_sub_style)
                # row += 1
                # sheet.merge_range(row, 0, row, 16, 'SO: %s        %s        %s ' %(pro.name,pro.partner_id and pro.partner_id.name or '',pro.subtask_project_id and pro.subtask_project_id.name or ''), c_sub_style)
                # account.invoice
                # invoices = self._get_invoice(pro,objects)
                tot_penjualan, tot_hpp, tot_penalty, tot_angkut, tot_asuransi, tot_karyawan, = 0,0,0,0,0,0
                # 
                # Penjualan
                acl_penjualan |= optimization_acl.filtered(lambda rinv: rinv.invoice_id.id in invoices.ids and rinv.account_id.code[0] == '3')
                # penjualan = sum(acl_penjualan.mapped('debit')) - sum(acl_penjualan.mapped('credit'))
                # penjualan = self._get_parameter_query(acl_penjualan,acl_hpp,acl_penalty,acl_angkut,acl_asuransi)
                optimization_acl = optimization_acl - acl_penjualan
                # HPP
                acl_hpp |= optimization_acl.filtered(lambda rinv: rinv.invoice_id.id in invoices.ids and rinv.account_id.code[:2] in ('41','42'))
                # hpp = sum(acl_hpp.mapped('debit')) - sum(acl_hpp.mapped('credit'))
                # hpp = self._get_parameter_query(acl_hpp)
                optimization_acl = optimization_acl - acl_hpp
                # payment->journal
                # Penalty
                acl_penalty |= optimization_acl.filtered(lambda rinv: rinv.invoice_id.id in invoices.ids and rinv.account_id.code[:3] in ('526'))
                # penalty = sum(acl_penalty.mapped('debit')) - sum(acl_penalty.mapped('credit'))
                # penalty = self._get_parameter_query(acl_penalty)
                optimization_acl = optimization_acl - acl_penalty
                # B. Angkut
                acl_angkut |= optimization_acl.filtered(lambda rinv: rinv.invoice_id.id in invoices.ids and rinv.account_id.code[:3] in ('440'))
                # angkut = sum(acl_angkut.mapped('debit')) - sum(acl_angkut.mapped('credit'))
                # angkut = self._get_parameter_query(acl_angkut)
                optimization_acl = optimization_acl - acl_angkut
                # Asuransi
                acl_asuransi |= optimization_acl.filtered(lambda rinv: rinv.invoice_id.id in invoices.ids and rinv.account_id.code[:3] in ('441'))
                # asuransi = sum(acl_asuransi.mapped('debit')) - sum(acl_asuransi.mapped('credit'))
                # asuransi = self._get_parameter_query(acl_asuransi)
                optimization_acl = optimization_acl - acl_asuransi
                # karyawan
                # karyawan = 0

                # 
                # type_inv = ('out_invoice','in_invoice')
                # for tinv in type_inv:
                #     for inv in invoices.filtered(lambda rtinv: rtinv.type == tinv).sorted(key=lambda p: p.partner_id.name):
                #         if not inv:
                #             continue
                #         # account.move.line
                #         # Penjualan
                #         acl_penjualan = acl.filtered(lambda rinv: rinv.invoice_id.id == inv.id and rinv.account_id.code[0] == '3')
                #         # acl_penjualan = optimization_acl.filtered(lambda rinv: rinv.invoice_id.id == inv.id and rinv.account_id.code[0] == '3')
                #         penjualan = sum(acl_penjualan.mapped('debit')) - sum(acl_penjualan.mapped('credit'))
                #         # optimization_acl = optimization_acl - acl_penjualan
                #         # HPP
                #         acl_hpp = acl.filtered(lambda rinv: rinv.invoice_id.id == inv.id and rinv.account_id.code[:2] in ('41','42'))
                #         # acl_hpp = optimization_acl.filtered(lambda rinv: rinv.invoice_id.id == inv.id and rinv.account_id.code[:2] in ('41','42'))
                #         hpp = sum(acl_hpp.mapped('debit')) - sum(acl_hpp.mapped('credit'))
                #         # optimization_acl = optimization_acl - acl_hpp
                #         # payment->journal
                #         # Penalty
                #         acl_penalty = acl.filtered(lambda rinv: rinv.invoice_id.id == inv.id and rinv.account_id.code[:3] in ('526'))
                #         # acl_penalty = optimization_acl.filtered(lambda rinv: rinv.invoice_id.id == inv.id and rinv.account_id.code[:3] in ('526'))
                #         penalty = sum(acl_penalty.mapped('debit')) - sum(acl_penalty.mapped('credit'))
                #         # optimization_acl = optimization_acl - acl_penalty
                #         # B. Angkut
                #         acl_angkut = acl.filtered(lambda rinv: rinv.invoice_id.id == inv.id and rinv.account_id.code[:3] in ('440'))
                #         # acl_angkut = optimization_acl.filtered(lambda rinv: rinv.invoice_id.id == inv.id and rinv.account_id.code[:3] in ('440'))
                #         angkut = sum(acl_angkut.mapped('debit')) - sum(acl_angkut.mapped('credit'))
                #         # optimization_acl = optimization_acl - acl_angkut
                #         # Asuransi
                #         acl_asuransi = acl.filtered(lambda rinv: rinv.invoice_id.id == inv.id and rinv.account_id.code[:3] in ('441'))
                #         # acl_asuransi = optimization_acl.filtered(lambda rinv: rinv.invoice_id.id == inv.id and rinv.account_id.code[:3] in ('441'))
                #         asuransi = sum(acl_asuransi.mapped('debit')) - sum(acl_asuransi.mapped('credit'))
                #         # optimization_acl = optimization_acl - acl_asuransi
                #         # B. Karyawan
                #         karyawan = 0
                #         # -----total
                #         tot_penjualan += abs(penjualan)
                #         tot_hpp += abs(hpp)
                #         tot_penalty += abs(penalty)
                #         tot_angkut += abs(angkut)
                #         tot_asuransi += abs(asuransi)
                #         tot_karyawan += abs(karyawan)

                # # -----total
                # tot_penjualan += abs(penjualan)
                # tot_hpp += abs(hpp)
                # tot_penalty += abs(penalty)
                # tot_angkut += abs(angkut)
                # tot_asuransi += abs(asuransi)
                # tot_karyawan += abs(karyawan)
    
                # b.karyawan from journal item /fji
                # b_karyawan_fji = acl.filtered(lambda fji:  pro.id in fji.analytic_account_id.project_ids.ids and fji.account_id.code[:3] in (str(c) for c in range(451,459)))
                b_karyawan_fji |= optimization_acl.filtered(lambda fji:  pro.id in fji.analytic_account_id.project_ids.ids and fji.account_id.code[:3] in (str(c) for c in range(451,459)))
                # pro_b_karyawan_fji = sum(b_karyawan_fji.mapped('debit')) - sum(b_karyawan_fji.mapped('credit'))
                optimization_acl = optimization_acl - b_karyawan_fji
                # biaya operasional lainnya /bol
                # b_karyawan_fji_bol = acl.filtered(lambda fji: pro.id in fji.analytic_account_id.project_ids.ids and fji.account_id.code[:3] in (str(c) for c in range(510,519)))
                b_karyawan_fji_bol |= optimization_acl.filtered(lambda fji: pro.id in fji.analytic_account_id.project_ids.ids and fji.account_id.code[:3] in (str(c) for c in range(510,519)))
                # pro_b_karyawan_fji_bol = abs(sum(b_karyawan_fji_bol.mapped('debit')) - sum(b_karyawan_fji_bol.mapped('credit')))
                optimization_acl = optimization_acl - b_karyawan_fji_bol
                # b.jual from journal item /fji
                # bp_jual_fji = acl.filtered(lambda fji: pro.id in fji.analytic_account_id.project_ids.ids and fji.account_id.code[:2] =='52' and fji.account_id.code[:3] !='526')
                bp_jual_fji |= optimization_acl.filtered(lambda fji: pro.id in fji.analytic_account_id.project_ids.ids and fji.account_id.code[:2] =='52' and fji.account_id.code[:3] !='526')
                # pro_bp_jual_fji = abs(sum(bp_jual_fji.mapped('debit')) - sum(bp_jual_fji.mapped('credit')))
                optimization_acl = optimization_acl - bp_jual_fji
                # lain - lain from journal item /fji
                # b_lain_fji = acl.filtered(lambda fji: pro.id in fji.analytic_account_id.project_ids.ids and fji.account_id.code[0] in ('5','6') and fji.account_id.code[:3] !='526' and fji.account_id.code[:3] not in (str(c) for c in range(510,519)))
                b_lain_fji |= optimization_acl.filtered(lambda fji: pro.id in fji.analytic_account_id.project_ids.ids and fji.account_id.code[0] in ('5','6') and fji.account_id.code[:3] !='526' and fji.account_id.code[:3] not in (str(c) for c in range(510,519)))
                # pro_b_lain_fji = abs(sum(b_lain_fji.mapped('debit')) - sum(b_lain_fji.mapped('credit')))
                optimization_acl = optimization_acl - b_lain_fji
                # query
                # result = self._get_parameter_query(acl_penjualan,acl_hpp,acl_penalty,acl_angkut,acl_asuransi,b_karyawan_fji,b_karyawan_fji_bol,bp_jual_fji,b_lain_fji)
                penjualan, hpp, penalty, angkut, asuransi, pro_b_karyawan_fji, pro_b_karyawan_fji_bol, pro_bp_jual_fji, pro_b_lain_fji = self._get_parameter_query(acl_penjualan,acl_hpp,acl_penalty,acl_angkut,acl_asuransi,b_karyawan_fji,b_karyawan_fji_bol,bp_jual_fji,b_lain_fji)
                # clean
                acl_penjualan = acl_hpp = acl_penalty = acl_angkut = acl_asuransi = b_karyawan_fji = b_karyawan_fji_bol = bp_jual_fji = b_lain_fji = self.env['account.move.line'].sudo()
                # ----total
                tot_penjualan += abs(penjualan)
                tot_hpp += abs(hpp)
                tot_penalty += abs(penalty)
                tot_angkut += abs(angkut)
                tot_asuransi += abs(asuransi)

                # Total B. Lain
                pro_total_b_lain = sum([pro_b_karyawan_fji_bol,pro_bp_jual_fji,pro_b_lain_fji])

                # gross margin, %
                gross_margin = sum([tot_penjualan, -tot_hpp, -tot_penalty, -tot_angkut, -tot_asuransi, -pro_b_karyawan_fji])
                percent_gross = gross_margin/tot_penjualan * 100 if tot_penjualan != 0 else 0   
                # job profit/ %
                pro_job_profit = gross_margin - pro_total_b_lain
                pro_percent_gross = pro_job_profit/tot_penjualan * 100 if tot_penjualan != 0 else 0
                
                # Total SO
                # row += 1
                customer_pro = ','.join(list(map(lambda n: n.name or '',pro.invoice_customer_ids.mapped('partner_id')))) if pro.invoice_customer_ids else '' 
                sheet.write(row, 0, seq, c_style) # no
                sheet.write(row, 1, pro.name or '', c_style) # project/so
                sheet.write(row, 2, pro.partner_id and pro.partner_id.name if pro.partner_id else customer_pro, c_style) # customer
                sheet.write(row, 3, tot_penjualan or 0, num_style) # Penjualan
                sheet.write(row, 4, tot_hpp or 0, num_style) # hpp
                sheet.write(row, 5, tot_penalty or 0, num_style) # penalty
                sheet.write(row, 6, tot_angkut or 0, num_style) # angkut
                sheet.write(row, 7, tot_asuransi or 0, num_style) # asuransi
                sheet.write(row, 8, pro_b_karyawan_fji or 0, num_style) # karyawan
                sheet.write(row, 9, gross_margin or 0, num_style) # gross margin
                sheet.write(row, 10, percent_gross or 0, num_style) # %
                # bol
                sheet.write(row, 11, pro_b_karyawan_fji_bol or 0, num_style) # b.karyawan
                sheet.write(row, 12, pro_bp_jual_fji or 0, num_style) # b.p jual
                sheet.write(row, 13, pro_b_lain_fji or 0, num_style) # lain-lain
                sheet.write(row, 14, pro_total_b_lain or 0, num_style) # total b.lain
                sheet.write(row, 15, pro_job_profit or 0, num_style) # job profit
                sheet.write(row, 16, pro_percent_gross or 0, num_style) # %
                # grand total project/so
                g_tot_penjualan += tot_penjualan
                g_tot_hpp += tot_hpp
                g_tot_penalty += tot_penalty
                g_tot_angkut += tot_angkut
                g_tot_asuransi += tot_asuransi
                g_tot_karyawan += pro_b_karyawan_fji
                # 
                g_tot_b_karyawan_fji_bol += pro_b_karyawan_fji_bol
                g_tot_bp_jual_fji += pro_bp_jual_fji
                g_tot_b_lain_fji += pro_b_lain_fji
                g_tot_total_b_lain += pro_total_b_lain
                # 
                row += 1
                seq += 1

            # grand
            sheet.merge_range(row,0,row,2, 'Total SO.', c_style) # no  
            sheet.write(row, 3, g_tot_penjualan or 0, num_subtotal_style) # Penjualan
            sheet.write(row, 4, g_tot_hpp or 0, num_subtotal_style) # hpp
            sheet.write(row, 5, g_tot_penalty or 0, num_subtotal_style) # penalty
            sheet.write(row, 6, g_tot_angkut or 0, num_subtotal_style) # angkut
            sheet.write(row, 7, g_tot_asuransi or 0, num_subtotal_style) # asuransi
            sheet.write(row, 8, g_tot_karyawan or 0, num_subtotal_style) # karyawan
            sheet.write(row, 9, 0, num_subtotal_style) # gross margin
            sheet.write(row, 10, 0, num_subtotal_style) # %
            # bol
            # sheet.write(row, 11, pro_b_karyawan_fji_bol or 0, num_subtotal_style) # b.karyawan
            sheet.write(row, 11, g_tot_b_karyawan_fji_bol or 0, num_subtotal_style) # b.karyawan
            # sheet.write(row, 12, pro_bp_jual_fji or 0, num_subtotal_style) # b.p jual
            sheet.write(row, 12, g_tot_bp_jual_fji or 0, num_subtotal_style) # b.p jual
            # sheet.write(row, 13, pro_b_lain_fji or 0, num_subtotal_style) # lain-lain
            sheet.write(row, 13, g_tot_b_lain_fji or 0, num_subtotal_style) # lain-lain
            # sheet.write(row, 14, pro_total_b_lain or 0, num_subtotal_style) # total b.lain
            sheet.write(row, 14, g_tot_total_b_lain or 0, num_subtotal_style) # total b.lain
            sheet.write(row, 15, 0, num_subtotal_style) # job profit
            sheet.write(row, 16, 0, num_subtotal_style) # %

            # margin
            row += 1
            sheet.merge_range(row,0,row,2, 'Gross Margin.', c_style) # no  
            sheet.write(row, 3, 0, num_subtotal_style) # Penjualan
            sheet.write(row, 4, 0, num_subtotal_style) # hpp
            sheet.write(row, 5, 0, num_subtotal_style) # penalty
            sheet.write(row, 6, 0, num_subtotal_style) # angkut
            sheet.write(row, 7, 0, num_subtotal_style) # asuransi
            sheet.write(row, 8, 0, num_subtotal_style) # karyawan
            g_gross_margin = sum([g_tot_penjualan, -g_tot_hpp, -g_tot_penalty, -g_tot_angkut, -g_tot_asuransi, -g_tot_karyawan])
            g_percent_gross = g_gross_margin/g_tot_penjualan * 100 if g_tot_penjualan != 0 else 0
            sheet.write(row, 9, g_gross_margin or 0, num_subtotal_style) # gross margin
            sheet.write(row, 10, g_percent_gross or 0, num_subtotal_style) # %
            # bol
            sheet.write(row, 11, 0, num_subtotal_style) # b.karyawan
            sheet.write(row, 12, 0, num_subtotal_style) # b.p jual
            sheet.write(row, 13, 0, num_subtotal_style) # lain-lain
            sheet.write(row, 14, 0, num_subtotal_style) # total b.lain
            g_job_profit = g_gross_margin - g_tot_total_b_lain
            g_jb_percent_gross = g_job_profit/g_tot_penjualan * 100 if g_tot_penjualan != 0 else 0
            sheet.write(row, 15, g_job_profit, num_subtotal_style) # job profit
            sheet.write(row, 16, g_jb_percent_gross, num_subtotal_style) # %

            # total divisi
            row += 1
            sheet.merge_range(row,0,row,2, 'Total Divisi', c_style)
            sheet.merge_range(row,3,row,4,len(objects.project_ids.mapped('partner_id').ids) or 0 , num_subtotal_style)

            t1 = time.clock() - t0
            print('time elapsed', t1)
