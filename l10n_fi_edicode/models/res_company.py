from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    edicode = fields.Char(
        related="partner_id.edicode",
        string="Edicode",
        readonly=False,
        help="Our Company's Edicode for eInvoice documents",
    )
    einvoice_operator_id = fields.Many2one(
        comodel_name="res.partner.operator.einvoice",
        string="eInvoice Operator",
        related="partner_id.einvoice_operator_id",
        readonly=False,
    )
