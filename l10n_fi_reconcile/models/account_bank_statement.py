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

from odoo import models
from odoo.tools import float_round

_logger = logging.getLogger(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def get_reconciliation_proposition(self, excluded_ids=None):

        self.ensure_one()

        if not excluded_ids:
            excluded_ids = []
        amount = self.amount_currency or self.amount
        company_currency = self.journal_id.company_id.currency_id
        st_line_currency = self.currency_id or self.journal_id.currency_id
        currency = (st_line_currency and st_line_currency != company_currency) and st_line_currency.id or False
        precision = st_line_currency and st_line_currency.decimal_places or company_currency.decimal_places
        field = currency and 'amount_residual_currency' or 'amount_residual'
        liquidity_field = currency and 'amount_currency' or amount > 0 and 'debit' or 'credit'
        liquidity_amt_clause = currency and '%(amount)s::numeric' or 'abs(%(amount)s::numeric)'
        params = {'company_id': self.env.user.company_id.id,
                  'account_payable_receivable': (
                    self.journal_id.default_credit_account_id.id,
                    self.journal_id.default_debit_account_id.id),
                  'amount': float_round(amount, precision_digits=precision),
                  'partner_id': self.partner_id.id,
                  'excluded_ids': tuple(excluded_ids),
                  'ref': self.ref,
                  }

        if self.ref:
            # Check for both matching reference and amount
            add_to_select = ", CASE WHEN LTRIM(aml.payment_reference, '0') = %(ref)s \
                            THEN 1 ELSE 2 END as temp_field_order "
            add_to_from = " JOIN account_move m ON m.id = aml.move_id "
            select_clause, from_clause, where_clause = self._get_common_sql_query(overlook_partner=True, excluded_ids=excluded_ids, split=True)
            sql_query = select_clause + add_to_select + from_clause + add_to_from + where_clause
            add_to_where = " AND (LTRIM(aml.payment_reference, '0') = LTRIM(%(ref)s, '0') or m.name = %(ref)s) \
                            AND (" + field + " = %(amount)s::numeric OR (acc.internal_type = 'liquidity' \
                            AND " + liquidity_field + " = " + liquidity_amt_clause + ")) \
                            ORDER BY temp_field_order, date_maturity asc, aml.id asc"

            self.env.cr.execute(sql_query + add_to_where, params)
            results = self.env.cr.fetchone()
            if results:
                return self.env['account.move.line'].browse(results[0])

            # Check for just a matching reference
            add_to_where = " AND (LTRIM(aml.payment_reference, '0') = LTRIM(%(ref)s, '0') or m.name = %(ref)s) \
                            ORDER BY temp_field_order, date_maturity asc, aml.id asc"
            self.env.cr.execute(sql_query + add_to_where, params)
            results = self.env.cr.fetchone()
            if results:
                return self.env['account.move.line'].browse(results[0])

        # Return super if our queries yielded nothing
        return super(AccountBankStatementLine, self).get_reconciliation_proposition(excluded_ids=excluded_ids)

    def get_statement_line_for_reconciliation_widget(self):
        res = super(AccountBankStatementLine, self).get_statement_line_for_reconciliation_widget()

        # partner_name key is already in use so use something else
        if self.partner_name:
            res['partner_note'] = self.partner_name

        invoice_model = self.env['account.invoice']

        reference = res['ref']

        invoice = invoice_model.search([
            ('state', '=', 'open'),
            '|', ('payment_reference', '=', reference), ('reference', '=', reference)
        ], limit=1)

        if invoice:
            res['partner_name'] = invoice.partner_id.name
            res['partner_id'] = invoice.partner_id.id
            res['has_no_partner'] = False
        return res
