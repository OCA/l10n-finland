from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _auto_compute_invoice_reference(self):
        """
        Extend to automatically set payment references on refunds.

        It is customary in Finnish accounting to calculate the payment reference
        not just for sales invoices, but for refunds as well.
        """
        self.ensure_one()
        res = super()._auto_compute_invoice_reference()
        return res or (self.move_type == "out_refund" and not self.payment_reference)
