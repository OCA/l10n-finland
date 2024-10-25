from odoo import api, fields, models
from odoo.osv import expression


class ResPartnerOperatorEinvoice(models.Model):
    _name = "res.partner.operator.einvoice"
    _description = "eInvoice Operator"
    _order = "sequence, id"

    name = fields.Char(string="Operator", required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer()
    identifier = fields.Char(
        required=True,
        size=35,
        help="Monetary Institution Identifier (see https://tieke.fi)",
    )
    ttype = fields.Selection(
        [
            ("bank", "Bank with Finvoice brokerage service"),
            ("broker", "Carrier broker"),  # default
        ],
        "Type",
        default="broker",
    )

    _sql_constraints = [
        (
            "operator_identifier_uniq",
            "unique(identifier)",
            '"Identifier" should be unique!',
        ),
    ]

    @api.depends("identifier")
    def _compute_display_name(self):
        """
        Overwrite core method to add value of `identifier` ("Identifier") field
        into name of records.
        """
        res = super()._compute_display_name()
        for operator in self:
            operator.display_name = " - ".join([operator.identifier, operator.name])
        return res

    @api.model
    def _search_display_name(self, operator, value):
        if not value:
            return super()._search_display_name(operator, value)
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [
                "&",
                ("identifier", "not ilike", value + "%"),
                ("name", operator, value),
            ]
        else:
            domain = [
                "|",
                ("identifier", "=ilike", value + "%"),
                ("name", operator, value),
            ]
        return domain
