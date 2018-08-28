# Copyright (C) Avoin.Systems 2018
from odoo import fields, models


class FinnishCompany(models.Model):
    _inherit = 'res.company'

    payment_reference_type = fields.Selection(
        [
            ('none', 'Free Reference'),
            ('fi', 'Finnish Standard Reference'),
            ('rf', 'Creditor Reference (RF)'),
        ],
        'Payment Reference Type',
        default='rf',
        help='The default payment reference for sales invoices',
        required=True,
    )
