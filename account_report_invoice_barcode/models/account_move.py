import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    barcode = fields.Char(
        compute="_compute_barcode",
        store=False,
        copy=False,
    )

    def _compute_barcode(self):
        version = 4
        for record in self:
            if not record.validate_barcode():
                record.barcode = False
                continue

            iban = record.partner_bank_id.sanitized_acc_number[2:].zfill(16)
            eur, ct = divmod(record.amount_total, 1)
            eur = str(int(eur)).zfill(6)
            ct = str(int(round(ct, 2) * 100)).zfill(2)
            extra = "000"
            ref = record.payment_reference.zfill(20)
            due_date = fields.Date.from_string(record.invoice_date_due).strftime(
                "%y%m%d"
            )

            barcode = f"{version}{iban}{eur}{ct}{extra}{ref}{due_date}"

            record.barcode = barcode

    def validate_barcode(self):
        self.ensure_one()
        if (
            not self
            or self.move_type not in ("out_invoice", "out_refund")
            or self.state != "posted"
        ):
            return False
        if not self.partner_bank_id:
            _logger.warning(_(f"No bank account for invoice {self.name}"))
            return False
        if self.amount_total > 999999.99:
            _logger.warning(_(f"Too large amount for invoice {self.name}"))
            return False
        if not self.payment_reference:
            _logger.warning(_(f"Payment reference is missing for invoice {self.name}"))
            return False
        if self.payment_reference and len(self.payment_reference) > 20:
            _logger.warning(_(f"Too long payment reference for invoice {self.name}"))
            return False
        if not self.invoice_date_due:
            _logger.warning(_(f"No due date for invoice {self.name}"))
            return False
        if self.currency_id.name != "EUR":
            _logger.warning(_(f"Not using EUR as currency for invoice {self.name}"))
            return False

        return True
