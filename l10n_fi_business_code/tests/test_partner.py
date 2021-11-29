from odoo.tests.common import TransactionCase


class TestPartner(TransactionCase):
    def setUp(self):
        super(TestPartner, self).setUp()
        self.partner1 = self.env["res.partner"].create(
            {"name": "Test Company", "business_code": "1234567-1"}
        )

    def test_partner_business_code(self):
        # Test if business_code can be found from partner attributes
        self.assertEqual(self.partner1.business_code, "1234567-1")

    def test_partner_commercial_fields(self):
        # Test if business_code is found from commercial fields
        self.assertIn("business_code", self.partner1._commercial_fields())

    def test_partner_same_business_code(self):
        # Test if duplicate business code launches duplicate warning
        self.assertIs(len(self.partner1.same_business_code_partner_id), 0)

        # Create a new partner with the same business code
        self.partner2 = self.env["res.partner"].create(
            {"name": "Test Company 2", "business_code": "1234567-1"}
        )

        self.assertIs(len(self.partner2.same_business_code_partner_id), 1)
