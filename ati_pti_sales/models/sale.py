from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
from datetime import datetime, timedelta, time


class SaleOrder(models.Model):
    _inherit = 'sale.order'


    @api.multi
    def _compute_skep(self):
        for rec in self:
            skep = self.env['skep.pib'].sudo().search([('sale_id', '=', rec.id),('state','not in',('draft','cancelled'))])
            rec.skep_count = len(skep)
            rec.pib_count = sum(len(pib.pib_ids) for pib in skep)


    @api.multi
    # @api.one
    def formalities_view(self):
        self.ensure_one()
        domain = [('sale_id', '=', self.id)]
        return {
            'name': ('Formalities'),
            'domain': domain,
            'res_model': 'skep.pib',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'help': ('''<p class="oe_view_nocontent_create">
                           Click to Create for New SKEP
                        </p>'''),
            'limit': 80,
            'context': "{'default_sale_id': %s}" % (self.id)
        }

    skep_count = fields.Integer(compute='_compute_skep')
    pib_count = fields.Integer(compute='_compute_skep')



class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'


    skep_pib_ids = fields.Many2many('skep.pib', string="SKEP/PIB")



    @api.onchange('categ_id','product_id')
    def onchange_history_replacement(self):
        for rec in self:
            if rec.product_id:
                if any([h.is_replacement for h in rec.product_id.history_replacement_ids]):
                    msg = "Warning, %s" %(','.join([msg.desc for msg in rec.product_id.history_replacement_ids.filtered(lambda r: r.is_replacement == True)]))
                    raise UserError(_(msg))


class CrmLead(models.Model):
    _inherit = 'crm.lead.line'


    @api.onchange('category_id','product_id')
    def onchange_history_replacement(self):
        for rec in self:
            if rec.product_id:
                if any([h.is_replacement for h in rec.product_id.history_replacement_ids]):
                    msg = "Warning, %s" %(','.join([msg.desc for msg in rec.product_id.history_replacement_ids.filtered(lambda r: r.is_replacement == True)]))
                    raise UserError(_(msg))





