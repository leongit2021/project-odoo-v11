# -*- coding: utf-8 -*-
from typing import Sequence
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import logging
_logger = logging.getLogger(__name__)



_STATES = [
    ("draft", "Draft"),
    ("validate", "Done"),
    ("cancel", "Cancelled"),
]


class Sil(models.Model):
    _name = 'sil.sil'
    _description = "Shipping Instruction"
    _order = 'id asc'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string='SIL .', index=True, track_visibility='onchange', defaul='_New')
    ref_no = fields.Char(string='Ref. No.')
    shipper_id = fields.Many2one('res.partner', string='Shipper',  change_default=True, track_visibility='always')
    attn_shipper = fields.Char(string='Attn Shipper')
    phone_shipper = fields.Char(string='Phone')
    pti_ref_no = fields.Char(string='PTI Ref. No.')
    po_customer = fields.Char(string='PO Customer')
    division = fields.Many2one('crm.team', string='Division')
    #
    consignee_id = fields.Many2one('res.partner', string='Consignee',  change_default=True, track_visibility='always')
    attn_consignee = fields.Char(string='Attn Consignne')
    phone_consignee = fields.Char(string='Phone')
    fax = fields.Char(string='Fax')
    email = fields.Char(string='E-mail') 
    # 
    collection_poin_id = fields.Many2one('res.partner', string='Collection Poin',  change_default=True, track_visibility='always')
    # 
    package_qty = fields.Char(string='Qty Packages')
    rts = fields.Date(string='E.T.D/RTS')
    mode_transport = fields.Many2one('mode.transport', string='Mode Of Transport')
    delivery_date = fields.Date(string='Start Delivery Date')
    end_delivery_date = fields.Date(string='End Delivery Date')
    description = fields.Char(string='Description Of Goods')
    commodity = fields.Char(string='Commodity')
    remark = fields.Text(string='Remark') 
    state = fields.Selection(selection=_STATES,string="Status",index=True,track_visibility="onchange",copy=False,default="draft")
    # 
    picking_ids = fields.One2many('stock.picking', 'sil_id', 'Receiving')
    sil_ids = fields.One2many('sil.document','sil_id', string='SIL')



    @api.model
    def create(self, vals):
        res = super(Sil, self).create(vals)
        name = self.env['ir.sequence'].next_by_code(self._name)
        if name:
            res['name'] = name
        return res

    def action_draft(self):
        return self.write({'state': 'draft'})
    
    def action_done(self):
        if not self.picking_ids:
            raise UserError(_("Warning, not allowed empty picking."))
        return self.write({'state':'validate'})

    def action_cancel(self):
        return self.write({'state': 'cancel'})


    @api.onchange('shipper_id')
    def onchange_shipper(self):
        if self.shipper_id:
            self.attn_shipper = ','.join([rec.name for rec in self.shipper_id.child_ids])
            self.phone_shipper = self.shipper_id.phone or ''

    @api.onchange('consignee_id')
    def onchange_consignee(self):
        if self.consignee_id:
            self.attn_consignee = ','.join([rec.name for rec in self.shipper_id.child_ids])
            self.phone_consignee = self.consignee_id.phone or ''
            self.fax = self.consignee_id.fax or ''
            self.email = self.consignee_id.email or ''


    @api.onchange('picking_ids','picking_ids.sequence')
    def onchange_picking_ids(self):
        seq = 1
        for rec in self.picking_ids:
            rec.sequence_ref = seq
            seq += 1

    def action_reset_sequence(self):
        seq = 1
        for rec in self.picking_ids:
            rec.sequence_ref = seq
            seq += 1


    def _set_sil_order(self):
        sequence = []
        for rec in self.picking_ids.sorted(key=lambda s: s.sequence_ref):
            if rec.partner_id.id in [partner.id for partner in sequence]:
                continue

            sequence.append(rec.partner_id)
            
        return sequence

            

class SilLine(models.Model):
    _name = 'sil.document'
    _description = "SIL Document"
    _order = 'id asc'


    sil_id = fields.Many2one('sil.sil', string='SIL', ondelete='cascade')
    sequence = fields.Integer(string='Sequence')
    sil_doc_type_id = fields.Many2one('sil.document.type',string='Document Name')
    is_validate = fields.Boolean(string='Validate')

    @api.onchange('sil_doc_type_id')
    def onchange_sil_doc_type(self):
        for rec in self:
            rec.is_validate = rec.sil_doc_type_id.is_validate  


class SilDocumentType(models.Model):
    _name = 'sil.document.type'
    _description = "SIL Document Type"
    _order = 'id asc'

    name = fields.Char(string='Document Name')
    is_validate = fields.Boolean(string='Validate')


    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id,'%s' % (rec.name)))
        return res


    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        domain = args + [('name', operator, name)]
        return super(SilDocumentType, self).search(domain, limit=limit).name_get()


