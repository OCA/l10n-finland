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

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools import float_round, float_repr

_logger = logging.getLogger(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    @api.multi
    def auto_reconcile(self):
        """
        Try to automatically reconcile the statement.line return the
        counterpart journal entry/ies if the automatic reconciliation
        succeeded, False otherwise.
        Copied with modifications from super.
        """
        if self.company_id.auto_reconcile_method != 'finnish':
            return super(AccountBankStatementLine, self).auto_reconcile()

        self.ensure_one()
        match_recs = self.env['account.move.line']

        amount = self.amount_currency or self.amount
        company_currency = self.journal_id.company_id.currency_id
        st_line_currency = self.currency_id or self.journal_id.currency_id
        currency = (st_line_currency and
                    st_line_currency != company_currency) \
                   and st_line_currency.id or False
        precision = st_line_currency and st_line_currency.decimal_places \
                    or company_currency.decimal_places
        params = {'company_id': self.env.user.company_id.id,
                  'account_payable_receivable': (
                      self.journal_id.default_credit_account_id.id,
                      self.journal_id.default_debit_account_id.id),
                  'amount': float_round(amount, precision_digits=precision),
                  'partner_id': self.partner_id.id,
                  'ref': self.name,
                  }
        field = currency and 'amount_residual_currency' or 'amount_residual'
        liquidity_field = currency and 'amount_currency' or amount > 0 and 'debit' or 'credit'
        # Look for structured communication match
        if self.name:
            sql_query = self._get_common_sql_query() + \
                        " AND aml.ref = %(ref)s AND (" + field + \
                        " = %(amount)s OR (acc.internal_type = 'liquidity' " \
                        "AND " + liquidity_field + \
                        " = %(amount)s)) " \
                        "ORDER BY date_maturity asc, aml.id asc"
            self.env.cr.execute(sql_query, params)
            match_recs = self.env.cr.dictfetchall()
            if len(match_recs) > 1:
                return False

        # DIFF: Look for matching structured communication in payment_reference field
        if self.name and not match_recs:
            # sql_query = self._get_common_sql_query() + " AND aml.payment_reference = %(ref)s"
            sql_query = self._get_common_sql_query() + \
                        " AND aml.payment_reference = %(ref)s AND (" \
                        + field + \
                        " = %(amount)s OR (acc.internal_type = 'liquidity' " \
                        "AND " + liquidity_field + \
                        " = %(amount)s)) " \
                        "ORDER BY date_maturity asc, aml.id asc"
            self.env.cr.execute(sql_query, params)
            match_recs = self.env.cr.dictfetchall()
            if len(match_recs) > 1:
                return False

        # DIFF: Look for structured communication match, overlook partner
        if self.name:
            sql_query = self._get_common_sql_query(overlook_partner=True) + \
                        " AND aml.ref = %(ref)s AND (" + field + \
                        " = %(amount)s OR (acc.internal_type = 'liquidity' " \
                        "AND " + liquidity_field + \
                        " = %(amount)s)) " \
                        "ORDER BY date_maturity asc, aml.id asc"
            self.env.cr.execute(sql_query, params)
            match_recs = self.env.cr.dictfetchall()
            if len(match_recs) > 1:
                return False

        # DIFF: Look for matching structured communication in
        # payment_reference field, overlook partner
        if self.name and not match_recs:
            # sql_query = self._get_common_sql_query() + \
            # " AND aml.payment_reference = %(ref)s"
            sql_query = self._get_common_sql_query(overlook_partner=True) + \
                        " AND aml.payment_reference = %(ref)s AND (" \
                        + field + \
                        " = %(amount)s OR (acc.internal_type = 'liquidity' " \
                        "AND " + liquidity_field + \
                        " = %(amount)s)) " \
                        "ORDER BY date_maturity asc, aml.id asc"
            self.env.cr.execute(sql_query, params)
            match_recs = self.env.cr.dictfetchall()
            if len(match_recs) > 1:
                return False

        # DIFF: Do not try to match anything if structured communication match
        # fails
        # Look for a single move line with the same partner, the same amount
        # if not match_recs:
        #     if self.partner_id:
        #         sql_query = self._get_common_sql_query() + \
        #                     " AND (" + field + \
        #                     " = %(amount)s " \
        #                     "OR (acc.internal_type = 'liquidity' AND " + \
        #                     liquidity_field + \
        #                     " = %(amount)s)) " \
        #                     "ORDER BY date_maturity asc, aml.id asc"
        #         self.env.cr.execute(sql_query, params)
        #         match_recs = self.env.cr.dictfetchall()
        #         if len(match_recs) > 1:
        #             return False

        if not match_recs:
            return False

        match_recs = self.env['account.move.line'].browse(
            [aml.get('id') for aml in match_recs])
        # Now reconcile
        counterpart_aml_dicts = []
        payment_aml_rec = self.env['account.move.line']
        for aml in match_recs:
            if aml.account_id.internal_type == 'liquidity':
                payment_aml_rec = (payment_aml_rec | aml)
            else:
                amount = aml.currency_id and aml.amount_residual_currency \
                         or aml.amount_residual
                counterpart_aml_dicts.append({
                    'name': aml.name if aml.name != '/' else aml.move_id.name,
                    'debit': amount < 0 and -amount or 0,
                    'credit': amount > 0 and amount or 0,
                    'move_line': aml
                })

        try:
            with self._cr.savepoint():
                counterpart = self.process_reconciliation(
                    counterpart_aml_dicts=counterpart_aml_dicts,
                    payment_aml_rec=payment_aml_rec)
            return counterpart
        except UserError:
            # A configuration / business logic error that makes it impossible
            # to auto-reconcile should not be raised since automatic
            # reconciliation is just an amenity and the user will get the same
            # exception when manually reconciling. Other types of exception
            # are (hopefully) programmation errors and should cause a
            # stacktrace.
            self.invalidate_cache()
            self.env['account.move'].invalidate_cache()
            self.env['account.move.line'].invalidate_cache()
            return False

    def get_reconciliation_proposition(self, excluded_ids=None):
        # pylint: disable=sql-injection
        self.ensure_one()

        if not excluded_ids:
            excluded_ids = []
        amount = self.amount_currency or self.amount
        company_currency = self.journal_id.company_id.currency_id
        st_line_currency = self.currency_id or self.journal_id.currency_id
        currency = (st_line_currency and st_line_currency != company_currency) \
                   and st_line_currency.id or False
        precision = st_line_currency and st_line_currency.decimal_places \
                    or company_currency.decimal_places
        field = currency and 'amount_residual_currency' or 'amount_residual'
        liquidity_field = currency and 'amount_currency' or amount > 0 \
                          and 'debit' or 'credit'
        liquidity_amt_clause = currency and '%(amount)s::numeric' \
                               or 'abs(%(amount)s::numeric)'
        params = {'company_id': self.env.user.company_id.id,
                  'account_payable_receivable': (
                      self.journal_id.default_credit_account_id.id,
                      self.journal_id.default_debit_account_id.id
                  ),
                  'amount': float_repr(float_round(amount,
                                                   precision_digits=precision),
                                       precision_digits=precision),
                  'partner_id': self.partner_id.id,
                  'excluded_ids': tuple(excluded_ids),
                  'ref': self.ref,
                  'field': field,
                  'liquidity_field': liquidity_field,
                  'liquidity_amt_clause': liquidity_amt_clause,
                  }

        if self.ref:
            # Check for both matching reference and amount
            add_to_select = ", CASE WHEN LTRIM(aml.payment_reference, '0') =" \
                            " %(ref)s THEN 1 ELSE 2 END as temp_field_order "
            add_to_from = " JOIN account_move m ON m.id = aml.move_id "
            select_clause, from_clause, where_clause = \
                self._get_common_sql_query(
                    overlook_partner=True,
                    excluded_ids=excluded_ids,
                    split=True
                )
            sql_query = "{}{}{}{}{}".format(
                select_clause,
                add_to_select,
                from_clause,
                add_to_from,
                where_clause
            )
            add_to_where = """
                AND (LTRIM(aml.payment_reference, '0') = LTRIM(%(ref)s, '0')
                OR m.name = %(ref)s)
                AND ({field} = %(amount)s::numeric
                OR (acc.internal_type = 'liquidity'
                AND {liquidity_field}::numeric = {liquidity_amt_clause}))
                ORDER BY temp_field_order, date_maturity desc, aml.id desc
                """.format(**params)

            self.env.cr.execute(
                "{}{}".format(sql_query, add_to_where),
                params
            )
            results = self.env.cr.fetchone()
            if results:
                return self.env['account.move.line'].browse(results[0])

            # Check for just a matching reference
            add_to_where = " AND (LTRIM(aml.payment_reference, '0') = " \
                           "LTRIM(%(ref)s, '0') or m.name = %(ref)s)" \
                           "ORDER BY temp_field_order, date_maturity desc, " \
                           "aml.id desc"
            self.env.cr.execute(
                "{}{}".format(sql_query, add_to_where),
                params
            )
            results = self.env.cr.fetchone()
            if results:
                return self.env['account.move.line'].browse(results[0])

        # Return super if our queries yielded nothing
        return super(AccountBankStatementLine, self) \
            .get_reconciliation_proposition(excluded_ids=excluded_ids)

    def get_statement_line_for_reconciliation_widget(self):
        res = super(AccountBankStatementLine, self) \
            .get_statement_line_for_reconciliation_widget()

        # The partner_name key holds a name of an actual res.partner connected
        # to the bank statement. If we can find an existing res.partner on an
        # invoice that matches to the bank statement line's payment_reference,
        # we use that.
        #
        # The bank statement line's partner_name field is used by bank
        # statement importer to store bank statement's field's `partner`-column
        # that has some sort of description of the other party of the payment.
        # This might be just a name, name and description of the transaction
        # or something else. The `self.partner_name`-field has a slightly
        # misleading name because of the way the importer uses it. We are
        # showing this field as a separate column on the reconciliation view
        # since it often contains the most descriptive information about the
        # payment.
        #
        # The dict is returned to a Qweb view and not to create any records,
        # so the keys' names don't have to match any existing fields. Since
        # `partner_name` is used to store the name of an actual partner, we
        # create a new key `partner_note` that contains the bank statement
        # line's partner_name -field.

        if self.partner_name:
            res['partner_note'] = self.partner_name

        invoice_model = self.env['account.invoice']

        reference = res['ref']

        invoice = invoice_model.search([
            ('state', '=', 'open'), '|',
            ('payment_reference', '=', reference),
            ('reference', '=', reference)
        ], limit=1) if reference else False

        if invoice:
            res['partner_name'] = invoice.partner_id.name
            res['partner_id'] = invoice.partner_id.id
            res['has_no_partner'] = False
        return res
