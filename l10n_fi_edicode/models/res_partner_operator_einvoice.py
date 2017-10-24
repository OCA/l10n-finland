# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartnerOperatorEinvoice(models.Model):
    _name = 'res.partner.operator.einvoice'

    name = fields.Char(
        string='Operator',
    )
    identifier = fields.Char(
        string='Identifier',
    )
