# -*- coding: utf-8 -*-
from odoo import fields, models


class PaymentTerm(models.Model):

    _inherit = 'account.payment.term'
    _order = 'sequence, name'

    sequence = fields.Integer('Sequence')
    code = fields.Char('Unique code')
