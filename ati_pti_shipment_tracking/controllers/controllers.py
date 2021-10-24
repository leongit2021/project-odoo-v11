# -*- coding: utf-8 -*-
from odoo import http

# class AtiPtiShipmentTracking(http.Controller):
#     @http.route('/ati_pti_shipment_tracking/ati_pti_shipment_tracking/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ati_pti_shipment_tracking/ati_pti_shipment_tracking/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('ati_pti_shipment_tracking.listing', {
#             'root': '/ati_pti_shipment_tracking/ati_pti_shipment_tracking',
#             'objects': http.request.env['ati_pti_shipment_tracking.ati_pti_shipment_tracking'].search([]),
#         })

#     @http.route('/ati_pti_shipment_tracking/ati_pti_shipment_tracking/objects/<model("ati_pti_shipment_tracking.ati_pti_shipment_tracking"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ati_pti_shipment_tracking.object', {
#             'object': obj
#         })