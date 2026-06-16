# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MisReportKpi(models.Model):
    """
    A KPI representation with added fields for partner details.
    """
    _inherit = 'mis.report.kpi'

    display_details_by_partner = fields.Boolean(
        string='Show Details by Partner',
        default=False,
        )
    
    style_id_for_partner_details = fields.Many2one(
        'mis.report.style',
        string="Style for Partner Details",
        )

    partner_id = fields.Many2one(
        'res.partner',
        store=False,
        )
    
    account_id = fields.Many2one(
        'account.account',
        store=False,
        )
    
    parent_kpi_id = fields.Many2one(
        'mis.report.kpi',
        store=False,
        )
    
    partner_vat = fields.Char(
        string='Partner VAT', 
        readonly=True
        )
    
    partner_vat_country = fields.Char(
        string='Partner VAT Country', 
        readonly=True
        )
    
    partner_vat_number = fields.Char(
        string='Partner VAT Number', 
        readonly=True
        )
    
    show_vat_columns = fields.Boolean(
        string="Add VAT columns",
        help="If checked, columns for VAT will be added to the partner details.",
    )
    
    @api.onchange("display_details_by_partner")
    def _onchange_display_details_by_partner(self):
        if not self.display_details_by_partner:
            self.show_vat_columns = False
