
# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestMisReportPartnerDetails(TransactionCase):

    def setUp(self):
        """
        Create test data.
        """
        super().setUp()
        
        # models
        self.Report = self.env['mis.report']
        self.Kpi = self.env['mis.report.kpi']
        self.Instance = self.env['mis.report.instance']
        self.Period = self.env['mis.report.instance.period']
        self.Partner = self.env['res.partner']
        self.Account = self.env['account.account']
        self.Move = self.env['account.move']
        self.Journal = self.env['account.journal']

        # mis report
        self.report = self.Report.create({
            'name': 'Test Partner Report',
        })

        self.kpi = self.Kpi.create({
            'report_id': self.report.id,
            'name': 'kpi_debit',
            'description': 'Total Debit',
            'expression': 'bal[]',
            'type': 'num',
            'display_details_by_partner': False,
        })

        self.instance = self.Instance.create({
            'report_id': self.report.id,
            'name': 'Test Instance',
            'comparison_mode': False,
            'date_from': '2025-01-01',
            'date_to': '2025-12-31',
        })

        # partner
        self.partner = self.Partner.create({'name': 'Test Company', 'is_company': True})
        
        self.account = self.Account.create({
            'name': 'Test Account',
            'code': 'TEST100',
            'account_type': 'asset_receivable',
            'reconcile': True,
        })

        self.journal = self.Journal.create({
            'name': 'Test Journal',
            'code': 'TJ',
            'type': 'general',
        })

    def _create_move(self, partner, amount):
        move = self.Move.create({
            'journal_id': self.journal.id,
            'date': '2025-06-01',
            'line_ids': [
                (0, 0, {
                    'account_id': self.account.id,
                    'partner_id': partner.id if partner else False,
                    'debit': amount,
                    'credit': 0,
                }),
                (0, 0, {
                    'account_id': self.account.id,
                    'partner_id': False,
                    'debit': 0,
                    'credit': amount,
                }),
            ]
        })
        move.action_post()
        return move

    def _create_credit_move(self, partner, amount):
        move = self.Move.create({
            'journal_id': self.journal.id,
            'date': '2025-06-01',
            'line_ids': [
                (0, 0, {
                    'account_id': self.account.id,
                    'partner_id': partner.id if partner else False,
                    'debit': 0,
                    'credit': amount,
                }),
                (0, 0, {
                    'account_id': self.account.id,
                    'partner_id': False,
                    'debit': amount,
                    'credit': 0,
                }),
            ]
        })
        move.action_post()
        return move

    def test_compute_matrix_skip_no_checkbox(self):
        """
        Test that partner details are skipped when partner checkbox is unchecked.
        """
        # test data
        self.kpi.display_details_by_partner = False
        self._create_move(self.partner, 100.0)

        # test
        matrix = self.instance._compute_matrix()
        
        # report assertions
        rows = list(matrix.iter_rows())
        partner_rows = [r for r in rows if hasattr(r, '_partner_label')]
        self.assertEqual(len(partner_rows), 0, "No partner detail rows should be created when checkbox is off")

    def test_compute_matrix_generated(self):
        """
        Test that partner details are generated when conditions are met.
        """
        # test data
        self.kpi.display_details_by_partner = True
        self._create_move(self.partner, 100.0)

        # test
        matrix = self.instance._compute_matrix()
        
        # report assertions
        rows = list(matrix.iter_rows())
        partner_rows = [r for r in rows if hasattr(r, '_partner_label')]
        
        self.assertGreater(len(partner_rows), 0, 
                          f"Matrix should have partner detail rows. "
                          f"Total rows: {len(rows)}, "
                          f"KPI checkbox={self.kpi.display_details_by_partner}, "
                          f"expression={self.kpi.expression}")
        
        partner_found = False
        for r in partner_rows:
            if hasattr(r.kpi, 'partner_id') and r.kpi.partner_id.id == self.partner.id:
                partner_found = True
                self.assertIn(self.partner.name, r.label, "Partner name should be in row label")
                break
        
        self.assertTrue(partner_found, f"Should find partner row for {self.partner.name}")

    def test_compute_matrix_individual_contact_aggregated_to_company(self):
        """
        Test that individual contacts are aggregated into their parent company.
        """
        # test data
        self.kpi.display_details_by_partner = True

        child_partner = self.Partner.create({
            'name': 'Test individual',
            'parent_id': self.partner.id,
            'is_company': False,
        })

        self._create_move(self.partner, 100.0)
        self._create_move(child_partner, 50.0)

        # test
        matrix = self.instance._compute_matrix()
        
        # partner assertions
        rows = list(matrix.iter_rows())
        partner_rows = [r for r in rows if hasattr(r, '_partner_label') and hasattr(r.kpi, 'partner_id')]
        
        relevant_rows = [r for r in partner_rows if r.kpi.partner_id.id in (self.partner.id, child_partner.id)]
        self.assertGreater(len(relevant_rows), 0, "Should have at least one partner row")
        
        for row in relevant_rows:
            self.assertEqual(row.kpi.partner_id.id, self.partner.id, 
                           f"Partner row should be aggregated to company, not child")
        
        total_val = 0.0
        for row in relevant_rows:
            cells = list(row.iter_cells())
            if cells and cells[0] and hasattr(cells[0], 'val') and cells[0].val:
                total_val += cells[0].val

        self.assertAlmostEqual(total_val, 150.0, places=2,
                              msg=f"Value should be aggregated (100 from company + 50 from child). Got {total_val}")

    def test_compute_matrix_individual_excluded(self):
        """
        Test that individual partners are excluded.
        """
        # test data
        self.kpi.display_details_by_partner = True
        
        individual = self.Partner.create({
            'name': 'Test individual',
            'is_company': False,
            'parent_id': False,
        })
        self._create_move(individual, 200.0)
        
        # test
        matrix = self.instance._compute_matrix()
        
        # partner assertions
        rows = list(matrix.iter_rows())
        partner_rows = [r for r in rows if hasattr(r, '_partner_label') and hasattr(r.kpi, 'partner_id')]
        
        freelancer_row = next((r for r in partner_rows if r.kpi.partner_id.id == individual.id), None)
        
        self.assertIsNone(freelancer_row, 
                         "Individual partner should be excluded from partner details")

    def test_is_expression_valid_for_partner_breakdown(self):
        """
        Test how expressions are validated for partner breakdown.
        """
        # Invalid - empty/None/no account variable
        self.assertFalse(self.instance._is_expression_valid_for_partner_breakdown(""))
        self.assertFalse(self.instance._is_expression_valid_for_partner_breakdown(None))
        self.assertFalse(self.instance._is_expression_valid_for_partner_breakdown(False))
        self.assertFalse(self.instance._is_expression_valid_for_partner_breakdown("1 + 2"))
        self.assertFalse(self.instance._is_expression_valid_for_partner_breakdown("receivable * 0.1"))

        # Invalid - already has partner_id filter
        self.assertFalse(self.instance._is_expression_valid_for_partner_breakdown("balp[('partner_id', '=', 1)]"))
        self.assertFalse(self.instance._is_expression_valid_for_partner_breakdown("balp[('commercial_partner_id', '=', 1)]"))

        # Valid - has account variable and no partner filter
        self.assertTrue(self.instance._is_expression_valid_for_partner_breakdown("-balp[('tag_ids', 'in', (ref('l10n_fi.account_tag_sales').id))][]"))
        self.assertTrue(self.instance._is_expression_valid_for_partner_breakdown("bal[('account_type', '=', 'asset_receivable')]"))
        self.assertTrue(self.instance._is_expression_valid_for_partner_breakdown("crd[('code', 'like', '10%')]"))
        self.assertTrue(self.instance._is_expression_valid_for_partner_breakdown("deb[('account_id', 'in', [1,2,3])]"))
        self.assertTrue(self.instance._is_expression_valid_for_partner_breakdown("deb[1%]"))

    def test_compute_matrix_zero_balance_partner_filtered(self):
        """
        Test that partners with zero balance are filtered out.
        """
        # test data
        self.kpi.display_details_by_partner = True
        
        zero_partner = self.Partner.create({'name': 'Zero Balance Partner', 'is_company': True})
        self._create_move(zero_partner, 100.0)
        self._create_credit_move(zero_partner, 100.0)
        
        active_partner = self.Partner.create({'name': 'Partner With Active Balance', 'is_company': True})
        self._create_move(active_partner, 100.0)
        
        # test
        matrix = self.instance._compute_matrix()
        
        # matrix assertions
        rows = list(matrix.iter_rows())
        partner_rows = [r for r in rows if hasattr(r, '_partner_label') and hasattr(r.kpi, 'partner_id')]
        
        active_row = next((r for r in partner_rows if r.kpi.partner_id.id == active_partner.id), None)
        self.assertIsNotNone(active_row, "Active partner should be present in matrix")
        
        zero_row = next((r for r in partner_rows if r.kpi.partner_id.id == zero_partner.id), None)
        self.assertIsNone(zero_row, "Partner with zero balance should be filtered out")

    def test_get_kpi_query_domain(self):
        """
        Test _get_kpi_query_domain logic.
        """
        if not self.instance.period_ids:
            self.Period.create({
                'name': 'Test Period',
                'report_instance_id': self.instance.id,
                'date_from': '2025-01-01',
                'date_to': '2025-12-31',
                'source': 'actuals',
            })
            
        period = self.instance.period_ids[0]
        aep = self.report._prepare_aep(self.instance.query_company_ids, self.instance.currency_id)
        
        # Valid expression - should return a domain
        domain = self.instance._get_kpi_query_domain(self.kpi, aep, period, 'account.move.line')
        self.assertIsInstance(domain, list, "Valid expression should return a domain list")
        
        # Invalid expression - should return None
        self.kpi.expression = "invalid_syntax(("
        domain = self.instance._get_kpi_query_domain(self.kpi, aep, period, 'account.move.line')
        self.assertIsNone(domain, "Invalid expression should return None")

    def test_add_partner_filter_to_expression(self):
        """
        Test that partner and account filters are added correctly to expressions.
        """
        pid = self.partner.id
        aid = self.account.id
        partner_filter = f"('partner_id', 'child_of', {pid})"
        account_filter = f"('account_id', '=', {aid})"
        
        # Expression with empty account selector
        expr = "balp[]"
        res = self.instance._add_partner_filter_to_expression(expr, pid, aid)
        self.assertEqual(res, f"balp[][{partner_filter}, {account_filter}]")

        # Expression with account selector
        expr = "balp[70]"
        res = self.instance._add_partner_filter_to_expression(expr, pid, aid)
        self.assertEqual(res, f"balp[70][{partner_filter}, {account_filter}]")

        # Expression with existing move line domain
        expr = "balp[][('journal_id', '=', 1)]"
        res = self.instance._add_partner_filter_to_expression(expr, pid, aid)
        self.assertEqual(res, f"balp[][('journal_id', '=', 1), {partner_filter}, {account_filter}]")

        # Multiple variables in expression - test without spaces around operator to avoid regex issues
        expr = "balp[]+deb[70]"
        res = self.instance._add_partner_filter_to_expression(expr, pid, aid)
        expected = f"balp[][{partner_filter}, {account_filter}]+deb[70][{partner_filter}, {account_filter}]"
        self.assertEqual(res, expected)
        
        # No partner/account provided - should return original
        self.assertEqual(self.instance._add_partner_filter_to_expression("balp[]", False, False), "balp[]")

    def test_create_partner_kpi(self):
        """
        Test creation of partner sub-KPI.
        """
        # test data
        partner_info = {
            'partner_id': self.partner.id,
            'partner_name': self.partner.name,
            'partner_vat': 'CZ12345678',
            'balance': 100.0,
            'account_id': self.account.id,
            'account_name': f"{self.account.code} {self.account.name}",
        }
        
        style = self.env['mis.report.style'].create({'name': 'Partner Style'})
        self.kpi.style_id_for_partner_details = style.id
        
        sequence = 11.0
        
        # test
        new_kpi = self.instance._create_partner_kpi(self.kpi, partner_info, sequence)
        
        # kpi assertions
        self.assertEqual(new_kpi.report_id, self.kpi.report_id)
        self.assertEqual(new_kpi.sequence, sequence)
        self.assertIn(self.partner.name, new_kpi.description)
        self.assertIn(self.account.code, new_kpi.description)
        self.assertEqual(new_kpi.name, f"{self.kpi.name}_acc{self.account.id}_partner_{self.partner.id}")
        self.assertEqual(new_kpi.partner_id.id, self.partner.id)
        # account_id might be Many2one or Integer depending on implementation
        if hasattr(new_kpi.account_id, 'id'):
            self.assertEqual(new_kpi.account_id.id, self.account.id)
        else:
            self.assertEqual(new_kpi.account_id, self.account.id)
        self.assertEqual(new_kpi.parent_kpi_id.id, self.kpi.id)
        self.assertEqual(new_kpi.style_id.id, style.id)
        
        # Verify filters are in expression
        expected_partner_filter = f"('partner_id', 'child_of', {self.partner.id})"
        expected_account_filter = f"('account_id', '=', {self.account.id})"
        self.assertIn(expected_partner_filter, new_kpi.expression)
        self.assertIn(expected_account_filter, new_kpi.expression)
        
        # Verify VAT handling
        self.assertEqual(new_kpi.partner_vat, 'CZ12345678')
        self.assertEqual(new_kpi.partner_vat_country, 'CZ')
        self.assertEqual(new_kpi.partner_vat_number, '12345678')

    def test_filter_empty_partner_rows(self):
        """
        Test that partner rows with 0 or None values are removed,
        while partner rows with values are kept.
        """
        # test data
        class MockKpi:
            def __init__(self, id_val, partner_id=None, account_id=None):
                self.id = id_val
                self.partner_id = partner_id
                self.account_id = account_id
            def __repr__(self):
                return f"MockKpi({self.id})"

        class MockCell:
            def __init__(self, val):
                self.val = val

        class MockRow:
            def __init__(self, kpi, cells, label="MockRow"):
                self.kpi = kpi
                self._cells = cells
                self.label = label
            def iter_cells(self):
                return self._cells

        class MockMatrix:
            def __init__(self):
                self._kpi_rows = {}
                self._detail_rows = {}
                self._partner_row_map = {}

        matrix = MockMatrix()

        # Parent KPI
        kpi_parent = MockKpi("parent")
        
        # Partner KPI with value (should be kept)
        kpi_partner_val = MockKpi("new_1", partner_id=1, account_id=100)
        row_partner_val = MockRow(kpi_partner_val, [MockCell(100.0)], "Partner with value")
        
        # Partner KPI with 0 (should be removed)
        kpi_partner_zero = MockKpi("new_2", partner_id=2, account_id=101)
        row_partner_zero = MockRow(kpi_partner_zero, [MockCell(0.0)], "Partner with zero")
        
        # Partner KPI with None (should be removed)
        kpi_partner_none = MockKpi("new_3", partner_id=3, account_id=102)
        row_partner_none = MockRow(kpi_partner_none, [MockCell(None)], "Partner with None")

        # Setup matrix structure
        matrix._detail_rows[kpi_parent] = {
            -1: row_partner_val,
            -2: row_partner_zero,
            -3: row_partner_none,
            100: MockRow(MockKpi("account"), [MockCell(50.0)], "Account row"),  # Positive ID (account row)
        }
        
        partner_kpis_by_parent = {kpi_parent: [kpi_partner_val, kpi_partner_zero, kpi_partner_none]}

        # test
        self.instance._filter_empty_partner_rows(matrix, partner_kpis_by_parent)

        # assertions
        details = matrix._detail_rows[kpi_parent]
        self.assertIn(-1, details, "Partner row with value should be kept")
        self.assertNotIn(-2, details, "Partner row with 0.0 should be removed")
        self.assertNotIn(-3, details, "Partner row with None should be removed")
        self.assertIn(100, details, "Account row (positive ID) should be kept")

    def test_post_process_matrix_drilldowns(self):
        """
        Test that drilldown arguments are properly added to partner detail rows.
        """
        # test data
        self.kpi.display_details_by_partner = True
        self._create_move(self.partner, 100.0)
        
        matrix = self.instance._compute_matrix()
        
        rows = list(matrix.iter_rows())
        partner_row = next((r for r in rows if hasattr(r, '_partner_label')), None)
        
        if partner_row:
            cells = list(partner_row.iter_cells())
            for cell in cells:
                if cell and hasattr(cell, 'drilldown_arg') and cell.drilldown_arg:
                    self.assertIn('partner_id', cell.drilldown_arg, 
                                 "Drilldown should include partner_id")
                    self.assertIn('period_id', cell.drilldown_arg,
                                 "Drilldown should include period_id")
                    self.assertIn('kpi_id', cell.drilldown_arg,
                                 "Drilldown should include kpi_id (parent)")
                    
                    
def test_compute_matrix_partners_multiple_periods(self):
    """
    Test that partner rows are created based on data in any period (i.e. the combination of all periods).
    """
    # test data
    self.kpi.display_details_by_partner = True
    
    partner_a = self.Partner.create({'name': 'Partner A', 'is_company': True})
    partner_b = self.Partner.create({'name': 'Partner B', 'is_company': True})
    
    # create moves only in December and January (November is empty)
    self.Move.create({
        'journal_id': self.journal.id,
        'date': '2025-12-15',
        'line_ids': [
            (0, 0, {
                'account_id': self.account.id,
                'partner_id': partner_a.id,
                'debit': 500.0,
                'credit': 0,
            }),
            (0, 0, {
                'account_id': self.account.id,
                'partner_id': False,
                'debit': 0,
                'credit': 500.0,
            }),
        ]
    }).action_post()
    
    self.Move.create({
        'journal_id': self.journal.id,
        'date': '2026-01-10',
        'line_ids': [
            (0, 0, {
                'account_id': self.account.id,
                'partner_id': partner_b.id,
                'debit': 750.0,
                'credit': 0,
            }),
            (0, 0, {
                'account_id': self.account.id,
                'partner_id': False,
                'debit': 0,
                'credit': 750.0,
            }),
        ]
    }).action_post()
    
    # test
    matrix = self.instance._compute_matrix()
    
    rows = list(matrix.iter_rows())
    partner_rows = [r for r in rows if hasattr(r, '_partner_label') and hasattr(r.kpi, 'partner_id')]
    
    # assertions
    partner_ids = {r.kpi.partner_id.id for r in partner_rows}
    self.assertIn(partner_a.id, partner_ids, 
                 "Partner A should have a detail row (has data in December)")
    self.assertIn(partner_b.id, partner_ids,
                 "Partner B should have a detail row (has data in January)")
    
    partner_a_row = next(r for r in partner_rows if r.kpi.partner_id.id == partner_a.id)
    cells_a = list(partner_a_row.iter_cells())
    
    self.assertEqual(len(cells_a), 3, "Should have 3 period columns")
    
    if cells_a[0] and cells_a[0].val is not None:
        self.assertAlmostEqual(cells_a[0].val, 0.0, places=2,
                              msg="Partner A should have no value in November")
    
    self.assertIsNotNone(cells_a[1], "Partner A December cell should exist")
    self.assertIsNotNone(cells_a[1].val, "Partner A December cell should have a value")
    self.assertAlmostEqual(cells_a[1].val, 500.0, places=2,
                          msg="Partner A should have 500.0 in December")
    
    if cells_a[2] and cells_a[2].val is not None:
        self.assertAlmostEqual(cells_a[2].val, 0.0, places=2,
                              msg="Partner A should have no value in January")
    
    partner_b_row = next(r for r in partner_rows if r.kpi.partner_id.id == partner_b.id)
    cells_b = list(partner_b_row.iter_cells())
    
    if cells_b[0] and cells_b[0].val is not None:
        self.assertAlmostEqual(cells_b[0].val, 0.0, places=2,
                              msg="Partner B should have no value in November")
    
    if cells_b[1] and cells_b[1].val is not None:
        self.assertAlmostEqual(cells_b[1].val, 0.0, places=2,
                              msg="Partner B should have no value in December")
    
    self.assertIsNotNone(cells_b[2], "Partner B January cell should exist")
    self.assertIsNotNone(cells_b[2].val, "Partner B January cell should have a value")
    self.assertAlmostEqual(cells_b[2].val, 750.0, places=2,
                          msg="Partner B should have 750.0 in January")

def test_compute_matrix_all_periods_empty_no_partner_rows(self):
    """
    Test that when all periods are empty, no partner rows are created.
    """
    # test data
    for month, dates in [
        ('November', ('2025-11-01', '2025-11-30')),
        ('December', ('2025-12-01', '2025-12-31')),
        ('January', ('2026-01-01', '2026-01-31'))
    ]:
        self.Period.create({
            'name': month,
            'report_instance_id': self.instance.id,
            'date_from': dates[0],
            'date_to': dates[1],
            'source': 'actuals',
        })
    
    self.kpi.display_details_by_partner = True
    
    matrix = self.instance._compute_matrix()
    
    # assertions
    rows = list(matrix.iter_rows())
    partner_rows = [r for r in rows if hasattr(r, '_partner_label')]
    
    self.assertEqual(len(partner_rows), 0,
                    "Should have no partner rows when all periods are empty")
    