# -*- coding: utf-8 -*-

# 1. Standard library imports:

# 2. Known third party imports:

# 3. Odoo imports (openerp):
from openerp import api, fields, models

# 4. Imports from Odoo modules:

# 5. Local imports in the relative form:

# 6. Unknown third party imports:


class ResPartner(models.Model):

    # 1. Private attributes
    _inherit = 'res.partner'

    # 2. Fields declaration
    edicode = fields.Char(string='Edicode')
    einvoice_operator = fields.Many2one('res.partner.operator.einvoice', string='eInvoice Operator')
    einvoice_operator_identifier = fields.Char(
        string='Operator ID',
        compute='get_einvoice_operator_identifier',
        readonly=True,
    )

    # 3. Default methods

    # 4. Compute and search fields, in the same order that fields declaration
    @api.one
    @api.depends('einvoice_operator')
    def get_einvoice_operator_identifier(self):
        if self.einvoice_operator:
            self.einvoice_operator_identifier = self.einvoice_operator.identifier
