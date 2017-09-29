# -*- coding: utf-8 -*-
from openerp import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    edicode = fields.Char(
        string='Edicode'
    )
    einvoice_operator = fields.Many2one(
        comodel_name='res.partner.operator.einvoice',
        string='eInvoice Operator',
    )
    einvoice_operator_identifier = fields.Char(
        string='Operator ID',
        compute='get_einvoice_operator_identifier',
        readonly=True,
    )

    @api.one
    @api.depends('einvoice_operator')
    def get_einvoice_operator_identifier(self):
        if self.einvoice_operator:
            self.einvoice_operator_identifier = self.einvoice_operator.identifier
