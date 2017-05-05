# -*- coding: utf-8 -*-
from openerp import fields, models


class PaymentTerm(models.Model):

    # 1. Private attributes
    _inherit = 'account.payment.term'

    # 2. Fields declaration
    _order = 'sequence, name'

    sequence = fields.Integer('Sequence')
    code = fields.Char('Unique code')
