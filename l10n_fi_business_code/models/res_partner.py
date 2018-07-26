# Copyright 2017 Oy Tawasta OS Technologies Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    business_id = fields.Char(
        string='Business ID',
        compute=lambda s: s._compute_identification(
            'business_id', 'business_id',
        ),
        inverse=lambda s: s._inverse_identification(
            'business_id', 'business_id',
        ),
        search=lambda s, *a: s._search_identification(
            'business_id', *a
        ),
    )

    @api.constrains('id_numbers')
    def _check_if_single_business_id(self):
        business_category_id = self.env.ref('l10n_fi_business_code.res_partner_id_category_business_id')
        for partner in self:
            id_numbers = partner.id_numbers.filtered(lambda r: r.category_id == business_category_id)
            if len(id_numbers) > 1:
                raise ValidationError('Partner can only have 1 ID number of category ' + business_category_id.name)