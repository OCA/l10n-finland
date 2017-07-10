# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Avoin.Systems.
#    Copyright 2017 Avoin.Systems.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see http://www.gnu.org/licenses/agpl.html
#
##############################################################################

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    payment_reference = fields.Char(related='invoice_id.payment_reference', store=True)

    @api.multi
    def prepare_move_lines_for_reconciliation_widget(self, target_currency=False, target_date=False):

        def get_lines(l):
            ids = []
            for d in l:
                ids.append(d['id'])
            return self.search([('id', 'in', ids)])

        res = super(AccountMoveLine, self).prepare_move_lines_for_reconciliation_widget(target_currency, target_date)
        lines = get_lines(res)
        for line_dict in res:
            line = lines.filtered(lambda r: r.id == line_dict['id'])
            line_dict['payment_reference'] = line.payment_reference or '-'
        return res
