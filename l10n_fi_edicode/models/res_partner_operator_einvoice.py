# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartnerOperatorEinvoice(models.Model):
    _name = 'res.partner.operator.einvoice'

    name = fields.Char(
        string='Operator',
        required=True,
    )
    identifier = fields.Char(
        string='Identifier',
        required=True,
    )
