from odoo.tests.common import TransactionCase


class TestPartner(TransactionCase):
    def setUp(self):
        super(TestPartner, self).setUp()
        self.partner = self.env["res.partner"].create(
            {
                "name": "Test Company",
                "edicode": "003712345678",
                "einvoice_operator_id": self.env.ref(
                    "l10n_fi_edicode.operator_einvoice_ndeafihh"
                ).id,
            }
        )

    def test_partner_edicode(self):
        # Test if edicode and operator is set correctly
        self.assertEqual(self.partner.edicode, "003712345678")
        self.assertEqual(self.partner.einvoice_operator_id.name, "Nordea")
        self.assertEqual(self.partner.einvoice_operator_id.identifier, "NDEAFIHH")
