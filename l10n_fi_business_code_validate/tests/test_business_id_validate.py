# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestBusinessIdValidate(TransactionCase):
    # Test partner business id validation

    def setUp(self):
        # Set up Finnish and Swedish partners
        super(TestBusinessIdValidate, self).setUp()

        self.ResPartner = self.env['res.partner']

        self.partner_fi = self.ResPartner.create(dict(
            name='Yritys Oy',
            country_id=self.env.ref('base.fi').id
        ))

        self.partner_se = self.ResPartner.create(dict(
            name='Företag Ab',
            country_id=self.env.ref('base.se').id
        ))

    def test_empty_business_id(self):
        # An empty business id (not set, unset)
        self.partner_fi.business_id = False
        self.assertEqual(self.partner_fi.business_id, False)

    def test_valid_finnish_business_id(self):
        # A valid business id. This should be saved without error
        business_id = '1234567-1'

        self.partner_fi.business_id = business_id
        self.assertEqual(self.partner_fi.business_id, business_id)

        # This format should work too
        business_id = '12345671'

        self.partner_fi.business_id = business_id
        self.assertEqual(self.partner_fi.business_id, business_id)

    def test_invalid_finnish_business_id_validation_bit(self):
        # An invalid validation bit. This should throw a ValidationError
        business_id = '1234567-2'

        with self.assertRaises(ValidationError):
            self.partner_fi.business_id = business_id

    def test_invalid_finnish_business_id_format(self):
        # An invalid format. This should throw a ValidationError
        business_id = 'FI12345671'

        with self.assertRaises(ValidationError):
            self.partner_fi.business_id = business_id

    def test_valid_finnish_registered_association(self):
        # A valid registered association number
        business_id = '123.456'

        self.partner_fi.business_id = business_id
        self.assertEqual(self.partner_fi.business_id, business_id)

    def test_invalid_swedish_business_id(self):
        # Only Finnish business ids have a validation so far,
        # so this shouldn't raise an error
        # (Swedish) VAT-numbers should generally go to the VAT-field

        business_id = 'SE123456-7890'

        self.partner_se.business_id = business_id
        self.assertEqual(self.partner_se.business_id, business_id)
