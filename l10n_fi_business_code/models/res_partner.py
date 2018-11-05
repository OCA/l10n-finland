# Copyright 2017 Oy Tawasta OS Technologies Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


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
