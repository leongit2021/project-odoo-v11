from odoo import fields, api, models,_
from odoo.exceptions import Warning, UserError
from odoo.addons.base_import.models.base_import import xlrd
from base64 import decodestring
import xlsxwriter


class SourceDocumentDO(models.TransientModel):
    _inherit = "import.stock.move"

    file = fields.Binary(string='File', required=False)


    do_file = fields.Binary(string='File', required=False)
    do_filename = fields.Char('File Name', default='import.xls')
    document_id = fields.Many2one('document.document', string='Document', default=lambda self: self.env['document.document'].sudo().search([('code','ilike','DO')],limit=1))

    def get_template(self):
        if not self.document_id or not self.document_id.book:
            raise UserError(_("The template  may be not yet prepare."))
        self.do_file= self.document_id.book

        return {'type': 'ir.actions.do_nothing'}




    # def get_template(self):
    #     self.ensure_one()
    #     # res = self.env.ref('document_management_system.view_document_form', False)
    #     res = self.env.ref('ati_pti_document.document_do_mgmt_view  ', False)
        
    #     return {
    #         'name': ('Default Template DO Import'),
    #         'type': 'ir.actions.act_window',
    #         # 'domain': domain,
    #         'res_model': 'document.document',
    #         'type': 'ir.actions.act_window',
    #         # 'view_id': False,
    #         'views': [(res and res.id or False, 'form')],
    #         # 'res_id': self.document_id.id,
    #         'res_id': 5,
    #         # 'view_mode': 'tree,form',
    #         # 'view_type': 'form',
    #         'target':'new',
    #     }


class SourceDocumentPLB(models.TransientModel):
    _inherit = "update.plb.stock.move"

    file = fields.Binary(string='File', required=False)

    do_file = fields.Binary(string='File', required=False)
    do_filename = fields.Char('File Name', default='import.xls')
    document_id = fields.Many2one('document.document', string='Document', default=lambda self: self.env['document.document'].sudo().search([('code','ilike','PLB')],limit=1))

    def get_template(self):
        if not self.document_id or not self.document_id.book:
            raise UserError(_("The template may be not yet prepare."))
        self.do_file= self.document_id.book

        return {'type': 'ir.actions.do_nothing'}



class SourceDocumentSKEP(models.TransientModel):
    _inherit = "update.import.skep.line"


    file = fields.Binary(string='File', required=False)

    do_file = fields.Binary(string='File', required=False)
    do_filename = fields.Char('File Name', default='import.xls')
    document_id = fields.Many2one('document.document', string='Document', default=lambda self: self.env['document.document'].sudo().search([('code','ilike','SKEP')],limit=1))

    def get_template(self):
        if not self.document_id or not self.document_id.book:
            raise UserError(_("The template may be not yet prepare."))
        self.do_file= self.document_id.book

        return {'type': 'ir.actions.do_nothing'}




    


    
    