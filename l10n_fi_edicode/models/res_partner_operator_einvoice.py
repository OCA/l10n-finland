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
        super()._compute_display_name()
        for operator in self:
            operator.display_name = " - ".join([operator.identifier, operator.name])

    @api.model
    def _name_search(self, name, domain=None, operator="ilike", limit=None, order=None):
        domain = []
        if name:
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = [
                    "&",
                    ("identifier", "not ilike", name + "%"),
                    ("name", operator, name),
                ]
            else:
                domain = [
                    "|",
                    ("identifier", "=ilike", name + "%"),
                    ("name", operator, name),
                ]

        return self._search(domain, limit=limit, order=order)
