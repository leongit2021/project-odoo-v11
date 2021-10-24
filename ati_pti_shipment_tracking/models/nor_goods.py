# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from odoo.addons.base_import.models.base_import import xlrd
from base64 import decodestring
import xlsxwriter
import os

from odoo.addons import decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)



_STATES = [
    ("draft", "Draft"),
    ("validate", "Validate"),
    ("cancelled", "Cancelled"),
]

_NOR = [
    ("yes", "YES"),
    ("no", "NO"),
]


class NorGoods(models.Model):
    _name = 'nor.goods'
    _description = "Nor and goods to collect"
    _order = 'id asc'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string='NOR.', index=True, track_visibility='onchange', defaul='_New')
    created_by = fields.Many2one('res.users','Created By', default=lambda self: self.env.user.id)
    upload_date = fields.Date(string='Upload Date ',default=fields.Datetime.now)
    state = fields.Selection(selection=_STATES,string="Status",index=True,track_visibility="onchange",copy=False,default="draft")
    book = fields.Binary(string='File Excel')
    book_filename = fields.Char(string='File Name')
    import_error_note = fields.Text("Error Note")
    goods_ids = fields.One2many('nor.goods.line','goods_id', string='NOR')


    @api.multi
    def action_import_nor(self):
        return {
            'name': _('Import NOR'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'nor.line.import',
            'target': 'new',
            'context': {
                'default_goods_id': self.id,
            }
        }


    @api.model
    def create(self, vals):
        res = super(NorGoods, self).create(vals)
        name = self.env['ir.sequence'].next_by_code(self._name)
        if name:
            # date = fields.Datetime.from_string(fields.Datetime.now())
            # res['name'] = name.replace(name[4:6], str(date.year)[-2:])
            res['name'] = name

        return res


    @api.multi
    def action_import_nor(self):
        for rec in self.goods_ids:
            rec.unlink()

        if not self.book:
            raise UserError(_("File not found!."))
        return self.upload_nor(False,False)
        


    @api.multi
    def upload_nor(self, workbook, sheet_number):
        data = {}

        if not workbook and not sheet_number:
            file = os.path.splitext(self.book_filename)
            if file[1] not in ('.xls', '.xlsx'):
                raise UserError("Invalid File! Please import the correct file")

            wb = xlrd.open_workbook(file_contents=decodestring(self.book))
            sheet = wb.sheet_by_index(0)
        else:
            wb = workbook
            sheet = wb.sheet_by_index(sheet_number)

        col = 1
        row = 1
        sequence = 1

        warning = ''

        data = []
        while row != sheet.nrows:
            _logger.warning("row %s/%s" % (row,sheet.nrows))

            # Sales Order Number
            sales_order_no = ''
            # purchase
            purchase_id = False
            # Position
            position = 0
            # Item Description
            item_desc = ''
            # product
            product_id = False
            # Item Code
            item_code = ''
            # NOR QTY
            nor_qty = 0
            # UOM
            product_uom = False
            # Sales Value
            sales_value = 0
            # STAGED DT
            staged_dt = False
            # Today
            today = False
            # Days Stage
            days_staged = 0
            # LOAD CODE
            load_code = ''
            # NOR
            nor_state = ''
            # NOR DATE
            nor_date = False
            # NOR COMMENT
            nor_comment = ''

            col = 0


            # Sales Order Number
            if sheet.cell(row, col).value:
                sales_order_no = sheet.cell(row, col).value.strip()
                purchase_id = self.env['purchase.order'].sudo().search([('partner_ref','=',sales_order_no)])
            else:
                warning+="Warning, not found Sales Order Number at row: %s !!!\n" % (row)

            col += 1

            # Position
            if sheet.cell(row, col).value:
                position = sheet.cell(row, col).value
            else:
                warning+="Warning, not found Position at row: %s !!!\n" % (row)

            col += 1

            # Item Code
            if sheet.cell(row, col).value:
                item_code = sheet.cell(row, col).value

                if type(item_code).__name__ in ('float','int'):
                    item_code = str(int(item_code))
                
                # product id from purchase order line
                if purchase_id and purchase_id.order_line:
                    product_ids = purchase_id.order_line.filtered(lambda pro: pro.product_id.default_code == item_code and pro.sequence == position).mapped('product_id')
                    candidate_product_id = max(product_ids.ids) if product_ids else False 
                    if candidate_product_id:
                        new_product_id = self.env['product.product'].browse(candidate_product_id)
                        if new_product_id:
                            product_id = new_product_id
                        else:
                            product_id = False
                    else:
                        product_id = False
                else:
                    product_id = False
            
            else:
                warning+="Warning, not found Item Code at row: %s !!!\n" % (row)

            col += 1

            # Item Desc
            if sheet.cell(row, col).value:
                item_desc = sheet.cell(row, col).value
            else:
                warning+="Warning, not found item Desc at row: %s !!!\n" % (row)

            col += 1

            # NOR QTY
            if sheet.cell(row, col).value:
                nor_qty = sheet.cell(row, col).value
            else:
                warning+="Warning, not found NOR QTY at row: %s !!!\n" % (row)

            col += 1

            # Product UOM
            if sheet.cell(row, col).value:
                product_uom = sheet.cell(row, col).value.strip()
                find_uom = self.env['product.uom'].sudo().search([('name','=',product_uom)], limit=1)
                if not find_uom:
                    warning+="Warning, not found Product UOM at row: %s !!!\n" % (row)    
            else:
                warning+="Warning, not found Product UOM at row: %s !!!\n" % (row)

            col += 1

            # Sales Value
            if sheet.cell(row, col).value:
                if sheet.cell_type(row,col) == 2:
                    sales_value = float(sheet.cell(row, col).value)
                else:
                    sales_value = sheet.cell(row, col).value
            else:
                warning+="Warning, not found Sales Value at row: %s !!!\n" % (row)

            col += 1

            # STAGED DT
            if sheet.cell(row, col).value:
                staged_dt = sheet.cell(row, col).value
                # print('------staged_dt2', datetime(*xlrd.xldate_as_tuple(staged_dt, 0)).date(), type(datetime(*xlrd.xldate_as_tuple(staged_dt, 0)).strftime(DEFAULT_SERVER_DATE_FORMAT)))
            else:
                warning+="Warning, not found STAGED DT at row: %s !!!\n" % (row)

            col += 1

            # Today
            if sheet.cell(row, col).value:
                today = sheet.cell(row, col).value
            else:
                warning+="Warning, not found Today at row: %s !!!\n" % (row)


            col += 1
            # Days Staged
            if sheet.cell(row, col).value:
                days_staged = sheet.cell(row, col).value
            else:
                warning+="Warning, not found Days at row: %s !!!\n" % (row)

            col += 1

            # LOAD CODE
            if sheet.cell(row, col).value:
                load_code = sheet.cell(row, col).value
            else:
                warning+="Warning, not found LOAD CODE at row: %s !!!\n" % (row)

            col += 1

            if col != sheet.ncols:
                
                # NOR
                if sheet.cell(row, col).value:
                    nor_state = sheet.cell(row, col).value
                else:
                    warning+="Warning, not found NOR at row: %s !!!\n" % (row)

                col += 1
                # NOR DATE  
                if sheet.cell(row, col).value:
                    nor_date = sheet.cell(row, col).value
                else:
                    warning+="Warning, not found NOR DATE at row: %s !!!\n" % (row)


                col += 1

                # NOR COMMENT
                if sheet.cell(row, col).value:
                    nor_comment = sheet.cell(row, col).value
                else:
                    warning+="Warning, not found NOR COMMENT at row: %s !!!\n" % (row)

                col += 1


            # if not warning:
            if sales_order_no != '' or position > 0:
                staged_dt_ref, today_ref, nor_date_ref = self._get_date_type(staged_dt=staged_dt,today=today,nor_date=nor_date)
                data.append([0,False,{
                    'sequence': sequence,
                    'sales_order_no' : sales_order_no,
                    'purchase_id': purchase_id.id if purchase_id else False,
                    'position' : position,
                    'product_id': product_id.id if product_id else False,
                    'item_desc' : item_desc,
                    'item_code' : item_code,
                    'nor_qty' : nor_qty,
                    # 'product_uom' : product_uom.id if product_uom else False,
                    'product_uom' : product_uom,
                    'sales_value': sales_value ,
                    'staged_dt': staged_dt_ref,
                    # 'staged_dt': datetime(*xlrd.xldate_as_tuple(staged_dt, 0)).strftime(DEFAULT_SERVER_DATE_FORMAT) if staged_dt else False,
                    'today': today_ref,
                    # 'today': datetime(*xlrd.xldate_as_tuple(today, 0)).strftime(DEFAULT_SERVER_DATE_FORMAT) if today else False,
                    'days_staged': days_staged or 0,
                    'load_code': load_code or '',
                    'nor_state': 'yes' if nor_state in ('YES','Yes','Y','y','yes') else 'no' if nor_state in ('NO','No','N','no','n') else '',
                    'nor_date': nor_date_ref if nor_date != 42 and nor_date else False,
                    'nor_comment': nor_comment,
                    }])
                sequence += 1
            row+=1
        
        if not warning:
            self.write({'goods_ids': data, 'import_error_note': False})
        else:
            self.write({'goods_ids': data, 'import_error_note': False})
            warning = 'The first is make sure to fill Data. \n %s' %(warning)
            self.write({'import_error_note': warning})


    def _get_date_type(self,staged_dt=False,today=False,nor_date=False):
        staged_dt_ref, today_ref, nor_date_ref = False, False, False
        numerik , string = 1.1, 'string'
        # staged_dt
        if staged_dt and type(staged_dt) == type(numerik):
            staged_dt_ref = datetime(*xlrd.xldate_as_tuple(staged_dt, 0)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        elif staged_dt and type(staged_dt) == type(string):
            staged_dt_ref = staged_dt
        else:
            staged_dt_ref = datetime(*xlrd.xldate_as_tuple(staged_dt, 0)).strftime(DEFAULT_SERVER_DATE_FORMAT) if staged_dt else False

        # today
        if today and type(today) == type(numerik):
            today_ref = datetime(*xlrd.xldate_as_tuple(today, 0)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        elif staged_dt and type(today) == type(string):
            today_ref = today
        else:
            today_ref = False

        # nor date
        # today
        if nor_date and type(nor_date) == type(numerik):
            nor_date_ref = datetime(*xlrd.xldate_as_tuple(nor_date, 0)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        elif staged_dt and type(nor_date) == type(string):
            nor_date_ref = nor_date
        else:
            nor_date_ref = False

        return staged_dt_ref, today_ref, nor_date_ref


    def action_draft(self):
        return self.write({'state':'draft'})

    def action_validate(self):
        if not self.goods_ids:
            raise UserError(_("Not allowed, empty data to validate."))

        for valid in self.goods_ids:
            nor = self.env['summary.nor.goods'].sudo().search([('sales_order_no','=',valid.sales_order_no),
                                                                ('item_code','=',valid.item_code),
                                                                ('position','=',valid.position),
                                                                ('initial_qty','!=',valid.nor_qty),
                                                                ('initial_qty','!=',0)
                                                                ],limit=1)
            if nor: 
                action = self.env.ref('ati_pti_shipment_tracking.action_nor_validate_wizard').read()[0]
                action.update({'target': 'new'})
                return action

        new_summary = self.env['summary.nor.goods'].sudo()
        for rec in self.goods_ids:
            if rec.sales_order_no == '' and rec.item_code == '':
                continue

            summary = self.env['summary.nor.goods'].sudo().search([
                                                                ('sales_order_no','=',rec.sales_order_no),
                                                                ('item_code','=',rec.item_code),
                                                                ('position','=',rec.position)
                                                                ])

            purchase_order_line = self.env['purchase.order.line'].sudo().search([
                                                                                ('order_id','=',rec.purchase_id.id),
                                                                                ('sequence','=',rec.position),
                                                                                ('product_id','=',rec.product_id.id),
                                                                                ], limit=1)
            # update purchase order line: wj
            # purchase_order_line.write({'load_code':rec.load_code, 'nor_date':rec.nor_date})
            for pol in purchase_order_line:
                pol['load_code'] = rec.load_code
                pol['nor_date'] = rec.nor_date

            # update summary nor goods
            val = {
                'purchase_id': rec.purchase_id and rec.purchase_id.id if rec.purchase_id else False,
                'product_id': rec.product_id and rec.product_id.id if rec.product_id else False,
                'item_desc': rec.item_desc or '',
                'initial_qty': rec.nor_qty or 0,
                'nor_qty': rec.nor_qty or 0,
                'buffer_qty': rec.nor_qty or 0,
                'product_uom': rec.product_uom or '',
                'currency_id': rec.currency_id or False,
                'sales_value': rec.sales_value or 0,
                'staged_dt': rec.staged_dt or False,
                'today': rec.today or False,
                'days_staged': rec.days_staged or 0,
                'load_code': rec.load_code or '',
                'nor_state': rec.nor_state or '',
                'nor_date': rec.nor_date or False,
                'nor_comment': rec.nor_comment or '',
            }
            # 
            if not summary:
                val.update({
                    'sales_order_no': rec.sales_order_no or '',
                    'position': rec.position or 0,
                    'item_code': rec.item_code or '',
                })
                new_summary |= new_summary.create(val)
            else:
                summary.write(val)

        return self.write({'state':'validate'})

    @api.multi
    def action_validate_nor(self):
        action = self.env.ref('ati_pti_shipment_tracking.action_nor_validate_wizard').read()[0]
        action.update({'target': 'new'})
        return action
    
    def action_cancel(self):
        for rec in self.goods_ids:
            rec.unlink()
        return self.write({'state':'cancelled'})

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Can not deleted if state not draft."))
                
        return super(NorGoods, self).unlink()

    # delete item nor, summary if qty == 0, update purchase order line

    # @api.multi
    def action_delete_nor_detail(self):
        for rec in self.goods_ids.filtered(lambda r: r.is_deleted == True):
            pol = self.env['purchase.order.line'].sudo().search([('order_id','=', rec.purchase_id.id),
                                                                ('product_id','=',rec.product_id.id),
                                                                ('sequence','=',rec.position)])

            # update picked qty == 0
            if pol:
                for line in pol.filtered(lambda r: r.picked_qty == 0):
                    line.write({'load_code':'','nor_date':False})
            
            # # delete summary nor goods
            nor = self.env['summary.nor.goods'].sudo().search([('sales_order_no','=',rec.sales_order_no),
                                                                ('position','=', rec.position),
                                                                ('item_code','=', rec.item_code),
                                                                ])
            # delete summary pickup_qty == 0
            for n in nor.filtered(lambda r: r.pickup_qty == 0):
                n.unlink()

            # # delete nor detail is delete
            rec.unlink()

        return {}

    
    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id,'%s' % (rec.name if rec.name else '')))
        return res

    # @api.constrains('skep_date','skep_recv_date')
    # def _warning_complete(self):
    #     if self.skep_date and self.skep_recv_date:
    #         if self.skep_date > self.skep_recv_date:
    #             raise UserError(_("Not allowed SKEP DATE greater than SKEP RECV DATE."))


class GoodsLine(models.Model):
    _name = 'nor.goods.line'
    _description = "Goods Collect"
    _order = 'id asc'


    goods_id = fields.Many2one('nor.goods', string='Goods', ondelete='cascade')
    sequence = fields.Integer('Sequence', readonly=False)
    name = fields.Char(related='goods_id.name', store=True)
    sales_order_no = fields.Char(string='SP Number')
    purchase_id = fields.Many2one('purchase.order',string='PO Number')
    position = fields.Integer(string='Position')
    product_id = fields.Many2one('product.product', string='Product')
    item_code = fields.Char(string='Item Code')
    item_desc = fields.Char(string='Item Description')
    nor_qty     = fields.Float(string='Qty', digits=dp.get_precision('Product Unit of Measure'))
    # product_uom = fields.Many2one('product.uom', string='UOM')
    product_uom = fields.Char(string='UOM')
    currency_id = fields.Many2one('res.currency', string='Currency')
    sales_value = fields.Monetary(string='Sales Value')
    staged_dt = fields.Date(string='STAGED DT')
    # today = fields.Date('Today', default=fields.Datetime.now)
    today = fields.Date('Today')
    days_staged = fields.Float(string='Days Qty')
    load_code = fields.Char(string='LOAD CODE')
    nor_state = fields.Selection(selection=_NOR,string='NOR')
    nor_date = fields.Date('NOR DATE')
    nor_comment = fields.Char(string='NOR COMMENT')
    is_deleted = fields.Boolean(string='Delete?')
