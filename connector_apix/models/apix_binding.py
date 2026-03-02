from odoo import fields, models


class ApixBinding(models.AbstractModel):
    _name = "apix.binding"
    _inherit = "external.binding"
    _description = "APIX Binding (abstract)"

    backend_id = fields.Many2one(
        comodel_name="apix.backend",
        string="APIX Backend",
        required=True,
        ondelete="restrict",
    )

    apix_batch_id = fields.Char(
        string="APIX Batch ID",
        index=True,
    )

    apix_accepted_document_id = fields.Char(
        string="APIX ID",
        help="AcceptedDocumentID of this record in APIX",
        index=True,
    )

    apix_cost_in_credits = fields.Float(string="Cost in credits")
