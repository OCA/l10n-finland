# -*- coding: utf-8 -*-

# 1. Standard library imports:

# 2. Known third party imports:

# 3. Odoo imports (openerp):
from openerp import api, fields, models

# 4. Imports from Odoo modules:

# 5. Local imports in the relative form:

# 6. Unknown third party imports:


class ResPartner(models.Model):

    _inherit = 'res.partner'

    edicode = fields.Char(string='Edicode')
    einvoice_operator = fields.Char(string='eInvoice Operator')
    einvoice_operator_identifier = fields.Char(string='Operator ID')
