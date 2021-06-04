from psycopg2 import IntegrityError

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestPartnerOperatorInvoice(TransactionCase):
    def setUp(self):
        super(TestPartnerOperatorInvoice, self).setUp()

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

    def test_name_get(self):
        # Test if name get syntax is correct
        operator = self.env.ref("l10n_fi_edicode.operator_einvoice_003723327487")
        operator_id, operator_name = operator.name_get()[0]
        self.assertEqual("003723327487 - Apix Messaging Oy", operator_name)

    def test_name_search(self):
        # Test name search with name
        operator_id, operator_name = self.env[
            "res.partner.operator.einvoice"
        ].name_search("Apix")[0]
        self.assertEqual("003723327487 - Apix Messaging Oy", operator_name)
