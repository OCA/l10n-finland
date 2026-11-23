from odoo.tests.common import TransactionCase


class TestPartner(TransactionCase):
    def setUp(self):
        super().setUp()
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

    def test_import_einvoice_operator_by_name(self):
        # Importing a contact should resolve the operator from its name
        result = self.env["res.partner"].load(
            ["name", "einvoice_operator_id"],
            [["Imported Company", "Apix Messaging Oy"]],
        )

        self.assertEqual([], result["messages"])
        self.assertEqual(
            self.env.ref("l10n_fi_edicode.operator_einvoice_003723327487"),
            self.env["res.partner"].browse(result["ids"]).einvoice_operator_id,
        )
