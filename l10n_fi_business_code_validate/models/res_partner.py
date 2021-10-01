# Copyright 2017 Oy Tawasta OS Technologies Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from odoo import _, api, models
from odoo.exceptions import ValidationError

# Number-space specific multipliers
FINNISH_ID_DIGIT_MULTIPLIERS = [7, 9, 10, 5, 8, 4, 2]


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.constrains(
        "business_code",
        "country_id",
    )
    def _check_business_code(self):
        for record in self:
            record.validate_business_code()

    # Business id validator
    def validate_business_code(self):
        for record in self:
            if record.business_code and record.country_id:
                # Try to find a validator function by partner country code

                # The method name should be
                # "_business_code_validate_{lowercase_country_code}"
                # e.g. "_business_code_validate_fi"
                validator_method_name = (
                    "_business_code_validate_%s" % record.country_id.code.lower()
                )

                # Check if the method exists
                if hasattr(self, validator_method_name):
                    # Run the validator
                    validator_method = getattr(self, validator_method_name)
                    validator_method()

    # Finnish (FI) business code validation
    def _business_code_validate_fi(self):
        self.ensure_one()

        # Update the format
        self._business_code_update_format_fi()
        business_code = self.business_code

        if re.match("^[0-9]{3}[.][0-9]{3}$", business_code):
            # Registered association (rekisteröity yhdistys, ry / r.y.).
            # Format 123.456
            return True

        # Validate business id formal format
        if not re.match("^[0-9]{7}[-][0-9]{1}$", business_code):
            msg = _("Your business id is invalid. Please use format 1234567-1")
            raise ValidationError(msg)

        # The formal format is ok, check the validation number
        multipliers = FINNISH_ID_DIGIT_MULTIPLIERS
        validation_multiplier = 0  # Initial multiplier

        # business id without "-" for validation
        business_code_number = re.sub("[^0-9]", "", business_code)
        validation_bit = business_code_number[7:8]

        # Test the validation bit
        for number, multiplier in zip(business_code_number[0:7], multipliers):
            validation_multiplier += multiplier * int(number)
        modulo = validation_multiplier % 11

        # Get the final modulo
        if 2 <= modulo <= 10:
            modulo = 11 - modulo

        if int(modulo) != int(validation_bit):
            # The validation bit doesn't match
            msg = "%s %s" % (
                _("Your business id validation digit is invalid."),
                _("Please check the given business ID."),
            )
            raise ValidationError(msg)

    # Finnish (FI) business id formatter
    def _business_code_update_format_fi(self):
        for record in self:
            # Reformat business id from 12345671 to 1234567-1
            if record.business_code and re.match("^[0-9]{8}$", record.business_code):

                record.business_code = (
                    record.business_code[:7] + "-" + record.business_code[7:]
                )
