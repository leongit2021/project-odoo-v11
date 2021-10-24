# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, AccessError
from odoo.addons import decimal_precision as dp


class BcTwoEightWizard(models.TransientModel):
    _name           = "bc.two.eight.wizard"
    _description    = "BC 2.8 Goods Detail"


    # custom_clearance_id = fields.Many2one('custom.clearance', string='Custom Clearance', default= lambda self: self.env.context.get('active_id',False)) 
    custom_clearance_id = fields.Many2one('custom.clearance', string='Custom Clearance') 
    goods_detail_ids = fields.Many2many('pickup.goods.line', string='Goods Detail')


    @api.model
    def default_get(self,fields):
        data = self.env.context
        bc = self.env['bc.two.eight'].sudo().browse(self.env.context.get('active_id'))
        result = super(BcTwoEightWizard, self).default_get(fields)
        result['custom_clearance_id'] = bc.bc_two_eight_id.id
        # result['domain'] = {'goods_detail_ids': [('id','in',custom_clearance.goods_detail_ids.ids)]}
        return result


    @api.onchange('goods_detail_ids')
    def _onchange_goods_detail_ids(self):
        return {'domain': {'goods_detail_ids': [('id','in',self.custom_clearance_id.goods_detail_ids.ids),('id','not in',[line.id for rec in self.custom_clearance_id.bc_two_eight_ids for line in rec.goods_detail_ids] )]}}


    def get_goods_detail(self):
        bc = self.env['bc.two.eight'].sudo().browse(self.env.context.get('active_id'))
        bc.goods_detail_ids = self.goods_detail_ids.ids



