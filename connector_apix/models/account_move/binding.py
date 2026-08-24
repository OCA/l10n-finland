from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ApixAccountInvoice(models.Model):
    # Binding Model for the APIX Invoice
    _name = "apix.account.invoice"
    _inherit = "apix.binding"
    _inherits = {"account.move": "odoo_id"}
    _description = "APIX Invoice"

    odoo_id = fields.Many2one(
        comodel_name="account.move",
        string="Invoice",
        required=True,
        ondelete="cascade",
    )

    @api.constrains("backend_id", "odoo_id")
    def _check_odoo_uniq(self):
        for record in self:
            if (
                self.search_count(
                    [
                        ("backend_id", "=", record.backend_id.id),
                        ("odoo_id", "=", record.odoo_id.id),
                        ("id", "!=", record.id),
                    ]
                )
                > 0
            ):
                raise ValidationError(
                    self.env._(
                        "An APIX binding for invoice '%s' already exists.",
                        record.odoo_id.name,
                    ),
                )
