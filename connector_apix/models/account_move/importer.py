import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ApixAccountInvoice(models.Model):
    _inherit = "apix.account.invoice"

    def import_finvoice(self, finvoice, attachments):
        if not finvoice:
            raise UserError(_("Finvoice is mandatory information"))

        AccountInvoiceImport = self.env["account.invoice.import"]

        import_config_id = self.env["account.invoice.import.config"].search(
            [
                ("company_id", "=", finvoice.company_id.id),
            ],
            limit=1,
        )

        values = dict(
            invoice_file=finvoice.datas,
            invoice_filename=finvoice.name,
            import_config_id=import_config_id.id,
        )

        # Launch the import wizard programmatically
        importer_wizard = AccountInvoiceImport.with_context(
            force_company=finvoice.company_id.id
        ).create(values)

        res = importer_wizard.import_invoice()
        res_id = res.get("res_id")

        for attachment in attachments:
            attachment.res_id = res_id

        # Importer creates a new Finvoice XML attachment. Remove the original
        finvoice.unlink()

        return res_id
