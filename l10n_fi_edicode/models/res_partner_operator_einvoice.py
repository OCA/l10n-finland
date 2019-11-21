from odoo import fields, models


class ResPartnerOperatorEinvoice(models.Model):
    _name = "res.partner.operator.einvoice"
    _description = "Adds operator name and identifier fields"

    name = fields.Char(
        string="Operator",
        required=True,
    )
    identifier = fields.Char(
        string="Identifier",
        required=True,
    )
