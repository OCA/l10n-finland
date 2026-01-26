import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


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

    _sql_constraints = [
        (
            "odoo_uniq",
            "unique(backend_id, odoo_id)",
            "An APIX binding for this invoice already exists.",
        ),
    ]
