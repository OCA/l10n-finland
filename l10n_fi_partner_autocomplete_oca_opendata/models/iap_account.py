from odoo import fields, models


class IapAccount(models.Model):
    _inherit = "iap.account"

    provider = fields.Selection(
        selection_add=[("prh", "PRH Avoin Data")],
        ondelete={"prh": "cascade"},
    )

    prh_use_industry = fields.Boolean(
        "PRH industry",
        help="Automatically fetch and create industry from PRH",
        default=True,
    )

    prh_language_code = fields.Selection(
        string="PRH language",
        selection=[
            ("1", "Finnish"),
            ("2", "Swedish"),
            ("3", "English"),
        ],
        default="1",
        help="Which language to use for importing data",
    )
