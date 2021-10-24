# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time


class SalesQuotationOrderWizard(models.TransientModel):
    _name           = "sales.quotation.order.wizard"
    _description    = "Sales Quotation/ Sales Order"
    
    date_from = fields.Date('Date From', required=True, default=fields.Datetime.now)
    date_to = fields.Date('Date To', required=True)
    status_ids = fields.Many2many("sqo.state",string="Sales Status")
    is_detail = fields.Boolean(string="Is Quotation / SO Detail show?")
    team_ids = fields.Many2many('crm.team', string='Sales Channel')
    partner_ids = fields.Many2many('res.partner', string='Customer', index=True)
    wiz_line_ids = fields.One2many('sales.quotation.order.wizard.line','wiz_line_id', string="Pre-Filter Detail")

    @api.constrains('date_from','data_to')
    def warning_date(self):
        if self.date_from >= self.date_to:
            raise UserError(_("You can not allowed Date From is greater than or equal to Date To."))

    
    def _get_so(self):
        domain = [('create_date','>=',self.date_from),('create_date','<=',self.date_to)]
        if self.team_ids:
            domain += [('team_id','in',self.team_ids.ids)]
        if self.partner_ids:
            domain += [('partner_id','in',self.partner_ids.ids)]
        if self.status_ids:
            domain += [('state','in',self.status_ids.mapped('code'))]

        so = self.env['sale.order'].sudo().search(domain)
        return so


    @api.onchange('date_from','date_to')
    def onchange_filter_info(self):
        if not self.date_from or not self.date_to:
            so,self.team_ids, self.partner_ids, self.status_ids = None, False, False,False
            self.wiz_line_ids = False
            return {}

        if self.date_from and self.date_to and self.team_ids:
            so,self.partner_ids, self.status_ids = None, False,False
            self.wiz_line_ids = False

            so = self._get_so()
            # self.team_ids = so.mapped('team_id').ids or False
            self.partner_ids = so.filtered(lambda r: r.team_id.id in self.team_ids.ids).mapped('partner_id').ids or False
            state = list(set(so.mapped('state')))
            wiz_state = self.env['sqo.state'].sudo().search([])
            self.status_ids =  wiz_state.filtered(lambda r: r.code in state).ids or False
            vals = []
            for team in self.team_ids:
                so_team = so.filtered(lambda r: r.team_id.id == team.id)
                state_team = list(set(so_team.mapped('state')))
                val = {
                    'team_ids': team.ids or False,
                    'partner_ids': so_team.mapped('partner_id').ids or False,
                    'so_ids': so_team.ids or False,
                    'status_ids': wiz_state.filtered(lambda r: r.code in state_team).ids or False
                }
                vals.append((0,0,val))
            self.wiz_line_ids = vals
        return {}

    @api.onchange('team_ids')
    def onchange_team(self):
        if self.date_from and self.date_to:
            so, self.partner_ids, self.status_ids = None, False,False
            self.wiz_line_ids = False
            if not self.team_ids:
                return {}

            so = self._get_so()
            self.partner_ids = so.filtered(lambda r: r.team_id.id in self.team_ids.ids).mapped('partner_id').ids or False
            state = list(set(so.mapped('state')))
            wiz_state = self.env['sqo.state'].sudo().search([])
            self.status_ids =  wiz_state.filtered(lambda r: r.code in state) 
            vals = []
            for team in self.team_ids:
                so_team = so.filtered(lambda r: r.team_id.id == team.id)
                state_team = list(set(so_team.mapped('state')))
                val = {
                    'team_ids': team.ids or False,
                    'partner_ids': so_team.mapped('partner_id').ids or False,
                    'so_ids': so_team.ids or False,
                    'status_ids': wiz_state.filtered(lambda r: r.code in state_team).ids or False
                }
                vals.append((0,0,val))
            self.wiz_line_ids = vals
        return {}

    
    @api.onchange('partner_ids')
    def onchange_partner(self):
        if self.date_from and self.date_to and not self.team_ids:
            so, self.team_ids, self.status_ids = None, False,False
            self.wiz_line_ids = False
            if not self.partner_ids:
                return {}

            so = self._get_so()
            state = list(set(so.mapped('state')))
            wiz_state = self.env['sqo.state'].sudo().search([])
            self.status_ids =  wiz_state.filtered(lambda r: r.code in state) 
            vals = []
            for partner in self.partner_ids:
                so_partner = so.filtered(lambda r: r.partner_id.id == partner.id)
                state_partner = list(set(so_partner.mapped('state')))
                val = {
                    'team_ids': so_partner.mapped('team_id').ids if so_partner else False,
                    'partner_ids': partner.ids or False,
                    'so_ids': so_partner.ids or False,
                    'status_ids': wiz_state.filtered(lambda r: r.code in state_partner).ids or False
                }
                vals.append((0,0,val))
            self.wiz_line_ids = vals
        return {}

    @api.onchange('status_ids')
    def onchange_state(self):
        if self.date_from and self.date_to and not self.team_ids and not self.partner_ids:
            so, self.team_ids, self.partner_ids = None, False,False
            self.wiz_line_ids = False
            if not self.status_ids:
                return {}

            so = self._get_so()
            state = list(set(so.mapped('state')))
            wiz_state = self.env['sqo.state'].sudo().search([])
            vals = []
            for state in self.status_ids:
                so_state = so.filtered(lambda r: r.state == state.code)
                state_state = list(set(so_state.mapped('state')))
                val = {
                    'team_ids': so_state.mapped('team_id').ids if so_state else False,
                    'partner_ids': so_state.mapped('partner_id').ids or False,
                    'so_ids': so_state.ids or False,
                    'status_ids': wiz_state.filtered(lambda r: r.code in state_state).ids or False
                }
                vals.append((0,0,val))
            self.wiz_line_ids = vals
        return {}


    @api.multi
    def generate(self):
        return self.env.ref('ati_pti_sales.sales_sqo_slsx').report_action(self.ids, config=False)


class SalesQuotationOrderWizardLine(models.TransientModel):
    _name           = "sales.quotation.order.wizard.line"
    _description    = "Detail Filter"


    team_ids = fields.Many2many('crm.team', string='Sales Channel')
    partner_ids = fields.Many2many('res.partner', string='Customer', index=True)
    wiz_line_id = fields.Many2one('sales.quotation.order.wizard', string="Sales Quotation/Order", ondelete="cascade")
    so_ids = fields.Many2many('sale.order', string="Sales Quotation/Order Group")
    status_ids = fields.Many2many("sqo.state",string="Status")
 

# class SalesQuotationOrderStatusWizard(models.TransientModel):
#     _name = 'sqo.state.wizard'
#     _description = "Sales Order Status"
#     _order = 'sequence asc'

#     name= fields.Char('Name')
#     code= fields.Char('Code')
#     sequence= fields.Integer('Sequence', default=5)


