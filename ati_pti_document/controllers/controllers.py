# -*- coding: utf-8 -*-
from odoo import http

# class AtiPtiDocument(http.Controller):
#     @http.route('/ati_pti_document/ati_pti_document/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ati_pti_document/ati_pti_document/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('ati_pti_document.listing', {
#             'root': '/ati_pti_document/ati_pti_document',
#             'objects': http.request.env['ati_pti_document.ati_pti_document'].search([]),
#         })

#     @http.route('/ati_pti_document/ati_pti_document/objects/<model("ati_pti_document.ati_pti_document"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ati_pti_document.object', {
#             'object': obj
#         })