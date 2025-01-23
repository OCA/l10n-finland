from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _compute_payment_reference(self):
        """
        Extend to automatically set payment references on refunds.

        It is customary in Finnish accounting to calculate the payment reference
        not just for sales invoices, but for refunds as well.
        """
        for move in self.filtered(
            lambda m: (
                m.state == "posted"
                and m.move_type == "out_refund"
                and not m.payment_reference
            )
        ):
            move.payment_reference = move._get_invoice_computed_reference()
        return super()._compute_payment_reference()
