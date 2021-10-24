# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, AccessError
import math
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons.base_import.models.base_import import xlrd
from base64 import decodestring
import xlsxwriter
import os
from odoo.addons import decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)



class ExportImportProduct(models.TransientModel):
    _name           = "export.import.product.wiz"
    _description    = "Export/Import Product"


    categ_id = fields.Many2one('product.category', string='Product Category')
    product_ids = fields.Many2many('product.template', string='Product')
    

    book = fields.Binary(string='File Excel')
    book_filename = fields.Char(string='File Name')
    import_error_note = fields.Text("Error Note")


    @api.onchange('categ_id')
    def onchange_categ_id(self):
        self.product_ids = False


    @api.multi
    def export_file(self):
        return self.env.ref('ati_pti_sales.export_import_product_xlsx').report_action(self.ids, config=False)




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

        col = 1
        row = 1
        sequence = 1

        warning = ''
        msg = ''

        data = []
        while row != sheet.nrows:
            _logger.warning("row %s/%s" % (row,sheet.nrows))


            # product id
            product_id = False
            # pn
            default_code = ''
            # product name
            product_name = ''
            # uom
            uom = ''
            # purchase uom
            purchase_uom = ''
            # cost
            cost = 0
            # categ name
            category_name = ''
             # product_lartas
            product_lartas = ''
            # hs_code
            hs_code = ''
            # product_adp
            product_adp = ''
            # type
            product_type = ''
            # product length
            product_length = ''
            # product width
            product_width = ''
            # product heigth
            product_height = ''
            # product_dimension
            product_dimension = ''

            # -----------------------------------------------------------------------------------
            col = 0
            # 1. product id
            if sheet.cell(row, col).value:
                product_id = sheet.cell(row, col).value
            else:
                warning+="Warning, not found Product ID at row: %s !!!\n" % (row)

            col += 1

            # 2. default code
            if sheet.cell(row, col).value:
                default_code = sheet.cell(row, col).value.strip()
            else:
                warning+="Warning, not found PN/Default Code at row: %s !!!\n" % (row)

            col += 1

            # 3. product name
            if sheet.cell(row, col).value:
                product_name = sheet.cell(row, col).value.strip()
            else:
                warning+="Warning, not found Product Name at row: %s !!!\n" % (row)

            col += 1

            # 4. uom
            if sheet.cell(row, col).value:
                uom = sheet.cell(row, col).value.strip()
                product_uom_id = self.env['product.uom'].sudo().search([('name','=',uom)], limit=1)
                if not product_uom_id:
                    msg+="Warning, not found UOM at row: %s !!!\n" % (row)    
            else:
                warning+="Warning, not found UOM at row: %s !!!\n" % (row)

            col += 1

            # 5. purchase uom
            if sheet.cell(row, col).value:
                purchase_uom = sheet.cell(row, col).value.strip()
                purchase_uom_id = self.env['product.uom'].sudo().search([('name','=',purchase_uom)], limit=1)
                if not purchase_uom_id:
                    msg+="Warning, not found Purchase UOM at row: %s !!!\n" % (row)
            else:
                warning+="Warning, not found Purchase UOM at row: %s !!!\n" % (row)

            col += 1

            # 6. List Price
            if sheet.cell(row, col).value:
                cost = sheet.cell(row, col).value
            else:
                warning+="Warning, not found Cost at row: %s !!!\n" % (row)

            col += 1

            # 7. category name
            if sheet.cell(row, col).value:
                category_name = sheet.cell(row, col).value.strip()
                product_categ_id = self.env['product.category'].sudo().search([('name','=',category_name)], limit=1)
                if not product_categ_id:
                    msg+="Warning, not found Category Name at row: %s !!!\n" % (row)
            else:
                warning+="Warning, not found Category Name at row: %s !!!\n" % (row)

            col += 1

            # 8. product lartas
            if sheet.cell(row, col).value:
                product_lartas = sheet.cell(row, col).value.strip()
            else:
                warning+="Warning, not found Product Lartas at row: %s !!!\n" % (row)

            col += 1

            # 9. hs code
            if sheet.cell(row, col).value:
                hs_code = sheet.cell(row, col).value.strip()
            else:
                warning+="Warning, not found HS Code at row: %s !!!\n" % (row)

            col += 1

            # 10. product adp
            if sheet.cell(row, col).value:
                product_adp = sheet.cell(row, col).value.strip()
            else:
                warning+="Warning, not found Product ADP at row: %s !!!\n" % (row)

            col += 1

            # 11. type
            if sheet.cell(row, col).value:
                product_type = sheet.cell(row, col).value.strip()
            else:
                warning+="Warning, not found Product Type at row: %s !!!\n" % (row)

            col += 1

            # 12. Product Length
            if sheet.cell(row, col).value:
                product_length = sheet.cell(row, col).value
            else:
                warning+="Warning, not found Product Length at row: %s !!!\n" % (row)

            col += 1

            # 13. Product Width
            if sheet.cell(row, col).value:
                product_width = sheet.cell(row, col).value
            else:
                warning+="Warning, not found Product Widht at row: %s !!!\n" % (row)

            col += 1

            # 14. Product height
            if sheet.cell(row, col).value:
                product_height = sheet.cell(row, col).value
            else:
                warning+="Warning, not found Product Height at row: %s !!!\n" % (row)

            col += 1

            # 15. Product Dimension
            if sheet.cell(row, col).value:
                product_dimension = sheet.cell(row, col).value.strip()
                product_dimension_uom_id = self.env['product.uom'].sudo().search([('name','=',product_dimension)], limit=1)
                if not product_dimension_uom_id:
                    msg+="Warning, not found Product Dimension UOM at row: %s !!!\n" % (row)
            else:
                warning+="Warning, not found Product Dimension UOM at row: %s !!!\n" % (row)

            col += 1

            # warning
            if msg:
                msg = 'The first is make sure to fill Data. \n %s' %(msg)
                raise UserError(_(msg))

            # product
            if product_id:
                product = self.env['product.template'].sudo().search([('id','=',int(product_id)),('default_code','=',str(default_code))], limit=1)
                _types = {'Consumable':'consu','Service':'service', 'Stockable Product':'product'}
                alias_types = [v for k,v in _types.items() if k == product_type] 
                
                for rec in product:
                    rec.write({
                        # 'default_code': default_code,
                        'name': product_name,
                        'uom_id': product_uom_id.id or False,
                        'uom_po_id': purchase_uom_id.id or False,
                        'standard_price': cost or 0,
                        'categ_id': product_categ_id.id or False,
                        'product_lartas': product_lartas,
                        'hs_code': hs_code,
                        'product_adp': product_adp,
                        'type': alias_types[0] if alias_types else '',
                        'product_length': product_length or 0,
                        'product_width': product_width or 0,
                        'product_height': product_height or 0,
                        'product_dimension': product_dimension_uom_id.id or False,

                    })
            
            row+=1
        

    