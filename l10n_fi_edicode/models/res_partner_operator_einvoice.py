from odoo import fields, models


class ResPartnerOperatorEinvoice(models.Model):
    _name = "res.partner.operator.einvoice"
    _description = "eInvoice Operator"

    name = fields.Char(
        string="Operator",
        required=True,
    )
    identifier = fields.Char(
        string="Identifier",
        required=True,
    )

    def name_get(self):
        """
        Overwrite core method to add value of `identifier` ("Identifier") field
        into name of recors.
        """
        result = []
        for operator in self:
            name = " - ".join([
                operator.identifier,
                operator.name,
            ])
            result.append(
                (operator.id, name),
            )
        return result
