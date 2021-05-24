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
