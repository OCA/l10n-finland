from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('standard', 'at_install')
class OnchangeCompanyIdTest(TransactionCase):

    def setUp(self):
        super(OnchangeCompanyIdTest, self).setUp()
        self.company_none = self.env['res.company'].create({
            'name': 'company_none',
            'payment_reference_type': 'none',
        })
        self.company_fi = self.env['res.company'].create({
            'name': 'company_fi',
            'payment_reference_type': 'fi',
        })

        self.settings = self.env['res.config.settings'].create({
            'company_id': self.company_none.id,
        })

    def test_onchange_company_id(self):

        self.assertEqual('none', self.settings.payment_reference_type)
        self.settings.write({'company_id': self.company_fi.id})
        self.settings.onchange_company_id()
        self.assertEqual('fi', self.settings.payment_reference_type)
