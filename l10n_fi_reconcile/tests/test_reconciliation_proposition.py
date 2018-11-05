from odoo.tests.common import TransactionCase
from odoo import fields

import logging

_logger = logging.getLogger(__name__)

REFERENCE_ONE_WITH_ZEROS = '00000145561'
REFERENCE_TWO_WITH_ZEROS = '00000145562'
REFERENCE_ONE_WITHOUT_ZEROS = '145561'
REFERENCE_THREE = '00000145563'
AMOUNT1 = 250.00
AMOUNT2 = 225.00
AMOUNT3 = 150.00

# account.move.line
ACCOUNT_MOVE_LINES = [
    {
        'name': 'perfect_match1',
        'payment_reference': REFERENCE_ONE_WITH_ZEROS,
        'amount': AMOUNT1,
    },
    {
        'name': 'perfect_match2',
        'payment_reference': REFERENCE_ONE_WITH_ZEROS,
        'amount': AMOUNT2,
    },
    {
        'name': 'partial_match1',
        'payment_reference': REFERENCE_TWO_WITH_ZEROS,
        'amount': AMOUNT1,
    },
    {
        'name': 'partial_match2',
        'payment_reference': REFERENCE_TWO_WITH_ZEROS,
        'amount': AMOUNT3,
    },
    {
        'name': 'partial_match2',
        'payment_reference': REFERENCE_THREE,
        'amount': AMOUNT2
    },
]

# account.bank.statement.line
# We have to create the account.move.lines in a way that doesn't allow us to
# (easily) know their ids, so we use the move line's name to compare the
# return values.
BANK_STATEMENT_LINES = [
    {
        'reference': REFERENCE_ONE_WITH_ZEROS,
        'amount': AMOUNT1,
        'expected_match': 'perfect_match1',
    },
    {
        'reference': REFERENCE_ONE_WITHOUT_ZEROS,
        'amount': AMOUNT2,
        'expected_match': 'perfect_match2',
    },
    {
        'reference': REFERENCE_TWO_WITH_ZEROS,
        'amount': AMOUNT1,
        'expected_match': 'partial_match1',
    },
    {
        'reference': REFERENCE_THREE,
        'amount': AMOUNT3,
        'expected_match': 'partial_match2',
    },
]


class ReconciliationPropositionTestCase(TransactionCase):
    def setUp(self):
        super(ReconciliationPropositionTestCase, self).setUp()

        self.company = self.env['res.company'].search([], limit=1)
        self.assertTrue(self.company)
        # the method also matches by user's company, so we must make sure the
        # correct one is linked to it
        self.env.user.company_id = self.company.id

        self.journal = self.env['account.journal'].search([
            ('type', '=', 'sale')
        ], limit=1)
        self.assertTrue(self.journal)

        # any account that can be reconciled
        self.account = self.env['account.account'].search([
            ('reconcile', '=', True)
        ], limit=1)
        self.assertTrue(self.account)

        self.partner = self.env['res.partner'].search([
            ('customer', '=', True)
        ], limit=1)
        self.assertTrue(self.partner)
        # invoices are there just to hold payment_reference which move lines
        # are related to place the invoices in a dict with payment reference
        # as the key
        invoices = dict()
        invoices[REFERENCE_ONE_WITH_ZEROS] = self.env['account.invoice'] \
            .create({
                'partner_id': self.partner.id,
                'account_id': self.account.id,
                'journal_id': self.journal.id,
                'company_id': self.company.id,
                'payment_reference': REFERENCE_ONE_WITH_ZEROS,
            })
        invoices[REFERENCE_TWO_WITH_ZEROS] = self.env['account.invoice'] \
            .create({
                'partner_id': self.partner.id,
                'account_id': self.account.id,
                'journal_id': self.journal.id,
                'company_id': self.company.id,
                'payment_reference': REFERENCE_TWO_WITH_ZEROS,
            })
        invoices[REFERENCE_THREE] = self.env['account.invoice'] \
            .create({
                'partner_id': self.partner.id,
                'account_id': self.account.id,
                'journal_id': self.journal.id,
                'company_id': self.company.id,
                'payment_reference': REFERENCE_THREE,
            })

        self.account_bank_statement_id = self.env['account.bank.statement'] \
            .create({
                'journal_id': self.journal.id,
                'company_id': self.company.id,
            })

        # We need a payment_method to assign to payments. This is how
        # account.invoice gets payment_method when creating payments.
        payment_method = self.env.ref(
            'account.account_payment_method_manual_in'
        )

        # We need to create move lines at the same time so the journal stays
        # in balance, so create a list of tuples with dicts that hold the
        # values and pass them to the account.move line_ids which will then
        # link and create them all at once. [(0, 0, {values}), (0, 0, ...]
        aml_lines = []
        for line in ACCOUNT_MOVE_LINES:
            # we just need a payment_id to give to account move lines.
            # Contains no relevant information,
            # just enough values to be able to create the payment
            payment_id = self.env['account.payment'].create({
                'amount': line['amount'],
                'partner_id': self.partner.id,
                'partner_type': 'customer',
                'journal_id': self.journal.id,
                'payment_type': 'inbound',
                'payment_method_id': payment_method.id,
            })

            # Debit and Credit lines to keep the move in balance.
            aml_lines.append((0, 0, {
                'name': line['name'],
                'account_id': self.account.id,
                'date_maturity': fields.Date.today(),
                # account.move.line gets its payment_reference from the linked
                # invoice.
                'invoice_id': invoices[line['payment_reference']].id,
                'debit': line['amount'],
                'payment_id': payment_id.id,
            }))
            aml_lines.append((0, 0, {
                'name': line['name'],
                'account_id': self.account.id,
                'date_maturity': fields.Date.today(),
                'invoice_id': invoices[line['payment_reference']].id,
                'credit': line['amount'],
                'payment_id': payment_id.id,
            }))

        self.account_move_id = self.env['account.move'].create({
            'name': 'testMove1',
            'line_ids': aml_lines,
            'company_id': self.company.id,
            'journal_id': self.journal.id,
        })

    def test_cases(self):
        for i, case in enumerate(BANK_STATEMENT_LINES):
            st_line = self.env['account.bank.statement.line'].create({
                'name': 'test_st_line' + str(i),
                'statement_id': self.account_bank_statement_id.id,
                'ref': case['reference'],
                'amount': case['amount'],
            })
            res = st_line.get_reconciliation_proposition(excluded_ids=None)

            # We had to outsource the account.move.line creation to
            # account.move so we don't know the ids for each of the lines
            # we created. Match with names instead.
            expected_aml_name = case['expected_match']
            assert len(res) == 1, "Test #{}: Expected exactly one result," \
                                  " received {}.".format(i, len(res))
            self.assertEqual(res.name, expected_aml_name,
                             msg="Test #{}: Unexpected return value. Returned "
                                 "{}, should be {}."
                                 .format(i, res.name, expected_aml_name))

    def test_normal_proposition(self):
        st_line = self.env['account.bank.statement.line'].create({
            'name': 'no_match',
            'statement_id': self.account_bank_statement_id.id,
            'amount': 2,
        })
        res = st_line.get_reconciliation_proposition(excluded_ids=None)
        expected_aml_name = 'no_match'
        self.assertNotEqual(res.name, expected_aml_name,
                            msg="Unexpected return value. Returned "
                                "{}, should be {}."
                            .format(res.name, expected_aml_name))
        res = st_line.get_statement_line_for_reconciliation_widget()
        self.assertEqual(res['partner_id'], False,
                         msg="Unexpected return value. Returned "
                             "{}, should be {}."
                             .format(res['partner_id'], False))

    def test_st_line_reconciliation_widget_data(self):
        # creating an invoice in open state
        invoice_line_data = [
            (0, 0,
                {
                    'product_id': self.env.ref('product.product_product_5').id,
                    'quantity': 10.0,
                    'account_id': self.account.id,
                    'name': 'product test 5',
                    'price_unit': 100.00,
                }
             )
        ]
        account_invoice_customer = self.env['account.invoice'].create(dict(
            name="Open Invoice Test",
            reference="123456",
            payment_term_id=self.env.ref(
                'account.account_payment_term_advance').id,
            journal_id=self.env['account.journal'].search([
                ('type', '=', 'sale')
            ])[0].id,
            partner_id=self.partner.id,
            account_id=self.account.id,
            invoice_line_ids=invoice_line_data
        ))
        ova = self.env['account.account'].search([(
            'user_type_id', '=',
            self.env.ref('account.data_account_type_current_assets').id
        )], limit=1)
        invoice_tax_line = {
            'name': 'Test Tax for Customer Invoice',
            'manual': 1,
            'amount': 9050,
            'account_id': ova.id,
            'invoice_id': account_invoice_customer.id,
        }
        self.env['account.invoice.tax'].create(invoice_tax_line)
        account_invoice_customer.action_invoice_open()

        # creating bank statement that gathers all data for the reconciliation
        # widget
        st_line = self.env['account.bank.statement.line'].create({
            'name': 'test_st_line_widget_data',
            'statement_id': self.account_bank_statement_id.id,
            'ref': account_invoice_customer.reference,
            'partner_name': self.partner.name,
        })
        res = st_line.get_statement_line_for_reconciliation_widget()

        self.assertEqual(res['partner_note'], self.partner.name,
                         msg="Unexpected return value. Returned "
                             "{}, should be {}."
                             .format(res['partner_note'], self.partner.name))
        self.assertEqual(res['partner_name'], self.partner.name,
                         msg="Unexpected return value. Returned "
                             "{}, should be {}."
                             .format(res['partner_name'], self.partner.name))
        self.assertEqual(res['partner_id'], self.partner.id,
                         msg="Unexpected return value. Returned "
                             "{}, should be {}."
                             .format(res['partner_id'], self.partner.id))
        self.assertEqual(res['has_no_partner'], False,
                         msg="Unexpected return value. Returned "
                             "{}, should be {}."
                             .format(res['has_no_partner'], False))

    def test_move_lines_reconciliation_widget_data(self):
        aml1 = self.env['account.move.line'].search([
            ('move_id', '=', self.account_move_id.id),
            ('payment_reference', '=', REFERENCE_THREE),
            ('debit', '=', 0)
        ], limit=1)
        res = aml1.prepare_move_lines_for_reconciliation_widget()
        self.assertEqual(res[0]['payment_reference'], REFERENCE_THREE,
                         msg="Unexpected return value. Returned "
                         "{}, should be {}."
                         .format(res[0]['payment_reference'], REFERENCE_THREE))
