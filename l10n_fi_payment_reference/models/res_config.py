# Copyright (C) Avoin.Systems 2018
from odoo import api, fields, models


class FinnishAccountSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payment_reference_type = fields.Selection(
        related='company_id.payment_reference_type',
        required=True,
        readonly=False,
    )

    @api.onchange('company_id')
    def onchange_company_id(self):
        # update related fields
        if self.company_id:
            company = self.company_id
            self.payment_reference_type = company.payment_reference_type
