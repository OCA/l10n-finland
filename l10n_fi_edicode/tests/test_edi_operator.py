from psycopg2 import IntegrityError

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestPartnerOperatorInvoice(TransactionCase):
    def setUp(self):
        super(TestPartnerOperatorInvoice, self).setUp()

    def test_name_get(self):
        operator = self.env.ref("l10n_fi_edicode.operator_einvoice_003723327487")
        operator_name = operator.name_get()

        # Name should have operator code and name
        self.assertEqual(operator_name[0][1], "003723327487 - Apix Messaging Oy")

    def test_name_search(self):
        operators = self.env["res.partner.operator.einvoice"].name_search(name="Apix")
        # Search should find one operator
        self.assertEqual(len(operators), 1)

    def test_name_search_negative(self):
        operators = self.env["res.partner.operator.einvoice"].name_search(
            name="Apix", operator="not ilike"
        )

        # This should return all operators BUT Apix
        # We are comparing with > 1 so this test won't fail
        # if operator list changes in the future
        self.assertGreater(len(operators), 1)

    def test_operator_info(self):
        # Test if operator information is correctly set
        operator = self.env.ref("l10n_fi_edicode.operator_einvoice_003723327487")
        self.assertEqual(operator.name, "Apix Messaging Oy")
        self.assertEqual(operator.identifier, "003723327487")

    def test_operator_identifier_constraint(self):
        # Test if a duplicate operator identifier is handled correctly
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            self.env["res.partner.operator.einvoice"].create(
                {
                    "name": "Nordea Duplicate",
                    "identifier": "NDEAFIHH",
                }
            )
