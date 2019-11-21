from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('standard', 'at_install')
class InvoiceValidateTest(TransactionCase):

    def setUp(self):
        super(InvoiceValidateTest, self).setUp()
        partner_id = self.env.ref('base.res_partner_1')
        self.company = self.env.ref('base.main_company')
        self.company.write({'payment_reference_type': 'fi'})
        account_receivable = self.env['account.account'].search(
            [('user_type_id',
              '=',
              self.env.ref('account.data_account_type_receivable').id)],
            limit=1)
        account_revenue = self.env['account.account'].search(
            [('user_type_id',
              '=',
              self.env.ref('account.data_account_type_revenue').id)],
            limit=1)

        self.invoice = self.env['account.invoice'].create({
            'partner_id': partner_id.id,
            'account_id': account_receivable.id,
            'type': 'out_invoice',
            'company_id': self.company.id,
            'reference_type': 'none',
            'name': 'invoice to client',
        })

        self.env['account.invoice.line'].create({
            'quantity': 1,
            'price_unit': 42,
            'invoice_id': self.invoice.id,
            'name': 'Some product',
            'account_id': account_revenue.id,
        })

        self.invoice.action_invoice_open()

    def test_invoice_validate(self):
        self.assertTrue(self.invoice.invoice_validate())
        prev_reference = self.invoice.payment_reference
        self.assertTrue(self.invoice.invoice_validate())
        self.assertEquals(prev_reference, self.invoice.payment_reference)
        self.invoice.write({'payment_reference': None})
        self.company.write({'payment_reference_type': 'rf'})
        self.assertTrue(self.invoice.invoice_validate())
        self.company.write({'payment_reference_type': 'none'})
        self.assertTrue(self.invoice.invoice_validate())
        self.assertEquals(None, self.env['account.invoice'].search(
            [], limit=2)._compute_payment_reference())
