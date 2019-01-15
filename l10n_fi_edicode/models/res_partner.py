from odoo import fields, models


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
        related='einvoice_operator.identifier',
        readonly=True,
    )
