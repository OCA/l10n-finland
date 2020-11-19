from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def post(self):
        """
        Extend post to automatically set payment references on refunds.

        It is customary in Finnish accounting to calculate the payment reference
        not just for sales invoices, but for refunds as well.
        """
        result = super().post()
        # Repeat logic equivalent to what happens in the super
        for move in self:
            if move.type == "out_refund" and not move.invoice_payment_ref:
                to_write = {
                    "invoice_payment_ref": move._get_invoice_computed_reference(),
                    "line_ids": [],
                }
                for line in move.line_ids.filtered(
                    lambda line_: line_.account_id.user_type_id.type
                    in ("receivable", "payable")
                ):
                    to_write["line_ids"].append(
                        (1, line.id, {"name": to_write["invoice_payment_ref"]})
                    )
                move.write(to_write)

        return result
