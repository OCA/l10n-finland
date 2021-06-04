from odoo import fields, models


class PaymentTerm(models.Model):

    _inherit = "account.payment.term"

    code = fields.Char("Unique code")
