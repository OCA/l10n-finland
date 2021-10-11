from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestBusinessCodeValidate(TransactionCase):
    # Test partner business code validation

    def setUp(self):
        # Set up Finnish and Swedish partners
        super().setUp()

        self.ResPartner = self.env["res.partner"]

        self.partner_fi = self.ResPartner.create(
            dict(name="Yritys Oy", country_id=self.env.ref("base.fi").id)
        )

        self.partner_se = self.ResPartner.create(
            dict(name="Företag Ab", country_id=self.env.ref("base.se").id)
        )

    def test_empty_business_code(self):
        # An empty business id (not set, unset)
        self.partner_fi.business_code = False
        self.assertEqual(self.partner_fi.business_code, False)

    def test_valid_finnish_business_code(self):
        # A valid business id. This should be saved without error
        business_code = "1234567-1"

        self.partner_fi.business_code = business_code
        self.assertEqual(self.partner_fi.business_code, business_code)

        # This format should work too and be auto-formatted to 1234567-1
        business_code_alternative = "12345671"

        self.partner_fi.business_code = business_code_alternative
        self.assertEqual(self.partner_fi.business_code, business_code)

    def test_invalid_finnish_business_code_validation_bit(self):
        # An invalid validation bit. This should throw a ValidationError
        business_code = "1234567-2"

        with self.assertRaises(ValidationError):
            self.partner_fi.business_code = business_code

    def test_invalid_finnish_business_code_format(self):
        # An invalid format. This should throw a ValidationError
        business_code = "FI12345671"

        with self.assertRaises(ValidationError):
            self.partner_fi.business_code = business_code

    def test_valid_finnish_registered_association(self):
        # A valid registered association number
        business_code = "123.456"

        self.partner_fi.business_code = business_code
        self.assertEqual(self.partner_fi.business_code, business_code)

    def test_invalid_swedish_business_code(self):
        # Only Finnish business ids have a validation so far,
        # so this shouldn't raise an error
        # (Swedish) VAT-numbers should generally go to the VAT-field

        business_code = "SE123456-7890"

        self.partner_se.business_code = business_code
        self.assertEqual(self.partner_se.business_code, business_code)
