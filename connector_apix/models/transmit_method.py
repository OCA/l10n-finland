from odoo import api, models

# Create transmit methods in init
# Doing this in XML may cause error if a method with same code already exists

# Transmit methods: code, name
TRANSMIT_METHODS = {
    "einvoice": "eInvoice",
    "printing_service": "Printing service",
}


class TransmitMethod(models.Model):
    _inherit = "transmit.method"

    @api.model
    def _init_apix_transmit_methods(self):
        for code, name in TRANSMIT_METHODS.items():
            if self.search([("code", "=", code)]):
                # Transmit method code already exits
                continue

            # Transmit method code doesn't exist. Create one
            self.create(
                {
                    "name": name,
                    "code": code,
                    "customer_ok": True,
                }
            )
