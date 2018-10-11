# Copyright 2017 Oy Tawasta OS Technologies Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re
from odoo import models
from odoo import _
from odoo.exceptions import ValidationError


class ResPartnerIdCategory(models.Model):
    _inherit = 'res.partner.id_category'

    # Number-space specific multipliers
    FINNISH_ID_DIGIT_MULTIPLIERS = [7, 9, 10, 5, 8, 4, 2]

    # Business id validator
    def validate_business_id(self, id_number):
        partner = id_number.partner_id

        if partner.country_id:
            # Try to find a validator function by partner country code

            # The method name should be
            # '_business_id_validate_{lowercase_country_code}'
            validator_method_name = '_business_id_validate_%s' % \
                                    partner.country_id.code.lower()

            # Check if the method exists
            if hasattr(self, validator_method_name):
                # Run the validator
                validator_method = getattr(self, validator_method_name)
                validator_method(partner)

    # Finnish (FI) business id validation
    def _business_id_validate_fi(self, partner):
        # Update the format
        self._business_id_update_format_fi(partner)

        business_id = partner.business_id

        if re.match('^[0-9]{3}[.][0-9]{3}$', business_id):
            # Registered association (rekisteröity yhdistys, ry / r.y.).
            # Format 123.456
            return True

        # Validate business id formal format
        if not re.match('^[0-9]{7}[-][0-9]{1}$', business_id):
            msg = _('Your business id is invalid. Please use format 1234567-1')
            raise ValidationError(msg)

        # The formal format is ok, check the validation number
        multipliers = self.FINNISH_ID_DIGIT_MULTIPLIERS
        validation_multiplier = 0  # Initial multiplier

        # business id without "-" for validation
        business_id_number = re.sub("[^0-9]", "",
                                    business_id)
        validation_bit = business_id_number[7:8]

        # Test the validation bit
        for number, multiplier in zip(business_id_number[0:7], multipliers):
            validation_multiplier += multiplier * int(number)
        modulo = validation_multiplier % 11

        # Get the final modulo
        if 2 <= modulo <= 10:
            modulo = 11 - modulo

        if int(modulo) != int(validation_bit):
            # The validation bit doesn't match
            msg = '%s %s' % (
                _('Your business id validation number is invalid.'),
                _('Please check the given business id.'),
            )
            raise ValidationError(msg)

    # Finnish (FI) business id formatter
    def _business_id_update_format_fi(self, partner):
        # Reformat business id from 12345671 to 1234567-1
        if partner.business_id and re.match('^[0-9]{8}$', partner.business_id):

            partner.business_id = \
                partner.business_id[:7] + '-' + partner.business_id[7:]
