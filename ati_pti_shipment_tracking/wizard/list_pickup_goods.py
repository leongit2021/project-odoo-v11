# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError
from odoo.addons import decimal_precision as dp
import math
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons.base_import.models.base_import import xlrd
from base64 import decodestring
import xlsxwriter
import os
import logging
_logger = logging.getLogger(__name__)

_CO_TYPE = [
    ("div_21", "DIV-21"),
    ("general", "General"),
]


class ListPickupGoodsWiz(models.TransientModel):
    _name           = "list.pickup.goods.wizard"
    _description    = "List Pickup Goods"


    purchase_id = fields.Many2one('purchase.order', string='Purchase Order') 
    summary_nor_goods_id = fields.Many2one('summary.nor.goods', string='Summary NOR') 
    purchase_order_line_ids = fields.Many2many('purchase.order.line', string='Purchase Order Line') 
    pickup_ids = fields.One2many('list.pickup.goods.line.wiz','pickup_id', string='List Pickup Goods')
    goods_id = fields.Many2one('pickup.goods', string='Pickup Goods', default= lambda self: self.env.context.get('active_id'))
    # co_type = fields.Selection(selection=_CO_TYPE,string="Type",index=True,track_visibility="onchange",copy=False,default="div_21")
    nor_date = fields.Date(string='NOR Date')


    @api.onchange('purchase_id','summary_nor_goods_id','purchase_order_line_ids','nor_date')
    def onchange_purchase_id(self):
        ids = []
        # for pol in self.env['purchase.order.line'].sudo().search([]).filtered(lambda r: r.buffer_qty != 0):
        #     ids.append(pol.id)
        res = {}
        if self.purchase_id or self.summary_nor_goods_id:
            res['domain'] = {'purchase_order_line_ids':['|',('order_id','=',self.purchase_id.id),'&',('load_code','=',self.summary_nor_goods_id.load_code),('load_code','!=','')]}
            return res

        if self.nor_date:
            return {'domain':{'purchase_order_line_ids':[('nor_date','=',self.nor_date)]}}

        return {'domain':{'purchase_order_line_ids':[('order_id','!=',False),('id','not in',ids)]}}
    
    
    @api.onchange('purchase_order_line_ids')
    def onchange_purchase_order_line_ids(self):
        self.pickup_ids = False
        vals = []
        for rec in self.purchase_order_line_ids:
            # if self.co_type != 'div_21':
            #     if rec.buffer_qty == 0:
            #         continue

            #     val = {
            #         'purchase_order_line_id': rec.id or False,
            #         'picked_qty': rec.buffer_qty or 0,
            #     }
            #     vals.append((0,0,val))
            # else:
            #     limit_qty_nor = self.env['summary.nor.goods'].sudo().search([('sales_order_no','=',rec.order_id.partner_ref),('position','=',rec.sequence),('product_id','=',rec.product_id.id)])
            #     buffer_qty_nor = sum([lqn.buffer_qty for lqn in limit_qty_nor])
            #     if buffer_qty_nor == 0:
            #         continue

            #     val = {
            #         'purchase_order_line_id': rec.id or False,
            #         'picked_qty': buffer_qty_nor or 0,
            #     }
            #     vals.append((0,0,val))
            if rec.load_code == '' or not rec.load_code:
                if rec.buffer_qty == 0:
                    continue

                val = {
                    'purchase_order_line_id': rec.id or False,
                    'po_number': rec.order_id.name or '',
                    'picked_qty': rec.buffer_qty or 0,
                    'product_uom': rec.product_uom.id or False,
                    'rts_date': rec.rts_date or False,
                    'nor_date': rec.nor_date or False

                }
                vals.append((0,0,val))
            else:
                limit_qty_nor = self.env['summary.nor.goods'].sudo().search([('sales_order_no','=',rec.order_id.partner_ref),('position','=',rec.sequence),('product_id','=',rec.product_id.id)])
                buffer_qty_nor = sum([lqn.buffer_qty for lqn in limit_qty_nor])
                if buffer_qty_nor == 0:
                    continue

                val = {
                    'purchase_order_line_id': rec.id or False,
                    'po_number': rec.order_id.name or '',
                    'picked_qty': buffer_qty_nor or 0,
                    'product_uom': rec.product_uom.id or False,
                    'rts_date': rec.rts_date or False,
                    'nor_date': rec.nor_date or False
                }
                vals.append((0,0,val))

        # 
        self.pickup_ids = vals


    @api.onchange('pickup_ids','pickup_ids.picked_qty')
    def validation(self):
        for rec in self.pickup_ids:
            if rec.picked_qty < 0:
                raise UserError(_("Not allowed: Qty Pickup less than zero(0)."))
            
            picked_qty_onprogress = sum(self.env['pickup.goods.line'].sudo().search([('purchase_order_line_id','=',rec.purchase_order_line_id.id),('pickup_id.state','not in',('confirmed','cancelled'))]).mapped('picked_qty'))
            if rec.load_code == '' or not rec.load_code:
                qty_limit = rec.purchase_order_line_id.buffer_qty - picked_qty_onprogress
                if rec.picked_qty > qty_limit:
                    raise UserError(_("Not allowed: Qty pickup %d greater than qty limit %d." % (rec.picked_qty, qty_limit)))
            else:
                limit_qty_nor = self.env['summary.nor.goods'].sudo().search([('sales_order_no','=',rec.purchase_order_line_id.partner_ref),('position','=',rec.purchase_order_line_id.sequence),('product_id','=',rec.purchase_order_line_id.product_id.id)])
                buffer_qty_nor = sum([lqn.buffer_qty for lqn in limit_qty_nor])
                qty_limit = buffer_qty_nor - picked_qty_onprogress
                if rec.picked_qty > qty_limit:
                    raise UserError(_("Not allowed: Qty pickup %d greater than qty limit %d." % (rec.picked_qty, qty_limit)))



    by_xlsx = fields.Boolean(string='Import By Xlsx?')
    book = fields.Binary(string='File Excel')
    book_filename = fields.Char(string='File Name')
    import_error_note = fields.Text("Error Note")


    @api.multi
    def import_file(self):
        if not self.book:
            raise UserError(_("File not found!."))
        return self.upload_file(False,False)
    

    @api.multi
    def upload_file(self, workbook, sheet_number):
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


        vals = []
        col = 1
        row = 1

        warning = ''
        msg = ''

        data = []
        while row != sheet.nrows:
            _logger.warning("row %s/%s" % (row,sheet.nrows))


            # load code/wj
            load_code = ''
            # sp/ pol
            sp_number = ''
            # sequece
            sequence = 0
            # item code/default code
            item_code =''

            # -----------------------------------------------------------------------------------
            col = 0
            # 1. load code/wj
            if sheet.cell(row, col).value:
                load_code = sheet.cell(row, col).value
                if type(load_code).__name__ in ('float','int'):
                    load_code = str(int(load_code))
            else:
                warning+="Warning, not found Load Code/WJ at row: %s !!!\n" % (row)

            col += 1

            # 2. sp_number
            if sheet.cell(row, col).value:
                sp_number = sheet.cell(row, col).value
                if type(sp_number).__name__ in ('float','int'):
                    sp_number = str(int(sp_number))
            else:
                warning+="Warning, not found SP Number at row: %s !!!\n" % (row)

            col += 1

            # 3. sequence
            if sheet.cell(row, col).value:
                sequence = sheet.cell(row, col).value
            else:
                warning+="Warning, not found Sequence at row: %s !!!\n" % (row)

            col += 1

            # 4. item code
            if sheet.cell(row, col).value:
                item_code = sheet.cell(row, col).value
                if type(item_code).__name__ in ('float','int'):
                    item_code = str(int(item_code))
            else:
                warning+="Warning, not found Item Code at row: %s !!!\n" % (row)

            col += 1
            
            
            # warning
            if warning:
                msg = 'The first is make sure to fill Data. \n %s' %(msg)
                raise UserError(_(msg))


            pol = self.env['purchase.order.line'].sudo().search([('load_code','=',load_code),('partner_ref','=',sp_number),('sequence','=',sequence),('product_id.default_code','=',item_code)], limit=1)
            # purchase order line
            if pol:
                for rec in pol:
                    if rec.load_code == '' or not rec.load_code:
                        if rec.buffer_qty == 0:
                            continue

                        val = {
                            'purchase_order_line_id': rec.id or False,
                            'po_number': rec.order_id.name or '',
                            'picked_qty': rec.buffer_qty or 0,
                            'product_uom': rec.product_uom.id or False,
                            'rts_date': rec.rts_date or False,
                            'nor_date': rec.nor_date or False

                        }
                        vals.append((0,0,val))
                    else:
                        limit_qty_nor = self.env['summary.nor.goods'].sudo().search([('sales_order_no','=',rec.order_id.partner_ref),('position','=',rec.sequence),('product_id','=',rec.product_id.id)])
                        buffer_qty_nor = sum([lqn.buffer_qty for lqn in limit_qty_nor])
                        if buffer_qty_nor == 0:
                            continue

                        val = {
                            'purchase_order_line_id': rec.id or False,
                            'po_number': rec.order_id.name or '',
                            'picked_qty': buffer_qty_nor or 0,
                            'product_uom': rec.product_uom.id or False,
                            'rts_date': rec.rts_date or False,
                            'nor_date': rec.nor_date or False
                        }
                        vals.append((0,0,val))

            else:
                # not found po
                msg_po = 'Not Found Purchase Order at Load Code: %s, SP Number: %s, Sequence: %d, Item Code: %s. \n' %(load_code,sp_number,sequence,item_code)
                raise UserError(_(msg_po))
            # 
            row+=1
        # 
        self.pickup_ids = vals

        return {'type': 'ir.actions.do_nothing'}



    def get_pickup_goods(self):
        pickup_goods_line = self.env['pickup.goods.line'].sudo()
        vals = []
        lartas = []
        for rec in self.pickup_ids:
            if rec.purchase_order_line_id.id in self.goods_id.pickup_ids.mapped('purchase_order_line_id').ids:
                continue
            # 
            if rec.purchase_order_line_id.product_id.product_lartas in ('LARTAS','Lartas','lartas'):
                lartas.append(True)

            val = {
                'purchase_order_line_id': rec.purchase_order_line_id.id or False,
                'picked_qty': rec.picked_qty or 0,
                'picked_uom': rec.product_uom.id or False,
                'rts_date': rec.rts_date or False,
                'pickup_id': self.goods_id.id or False,
            }
            # print('------po', rec.purchase_order_line_id, rec.purchase_order_line_id.order_id, rec.purchase_order_line_id.order_id.partner_ref)
            pickup_goods_line != pickup_goods_line.create(val) 
        
        # update pickup goods active id:  is_lartas: True
        if any([lartas]):
            self.goods_id.is_lartas = True
        sequence = 1
        for rec in self.goods_id.pickup_ids:
            rec.sequence = sequence
            sequence += 1

        return {}

class ListPickupGoodsLineWiz(models.TransientModel):
    _name           = "list.pickup.goods.line.wiz"
    _description    = "List Pickup Goods Detail"


    pickup_id = fields.Many2one('list.pickup.goods.wizard', string='List Pickup Goods', ondelete='cascade')
    purchase_order_line_id = fields.Many2one('purchase.order.line')
    po_number = fields.Char(related='purchase_order_line_id.order_id.name')
    load_code = fields.Char(string='Load Code', related='purchase_order_line_id.load_code', store=True)
    partner_ref = fields.Char(string='SP Number',related='purchase_order_line_id.partner_ref', store=True)
    product_id = fields.Many2one('product.product', related='purchase_order_line_id.product_id', string='Product')
    picked_qty     = fields.Float(string='Qty Pickup', digits=dp.get_precision('Product Unit of Measure'))
    product_uom = fields.Many2one('product.uom',string='UOM', store=True)
    rts_date = fields.Date(string='RTS Date') 
    nor_date = fields.Date(string='NOR Date', related='purchase_order_line_id.nor_date')