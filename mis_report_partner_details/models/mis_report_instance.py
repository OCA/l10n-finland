# -*- coding: utf-8 -*-
import logging
import re

from odoo import _, models
from odoo.exceptions import UserError
from odoo.osv import expression

from odoo.addons.mis_builder.models.aep import AccountingExpressionProcessor as AEP
from odoo.addons.mis_builder.models.kpimatrix import KpiMatrixRow
from odoo.addons.mis_builder.models.expression_evaluator import ExpressionEvaluator

_logger = logging.getLogger(__name__)

class MisReportInstance(models.Model):
    """
    The MIS report instance overriding computation to include partner KPIs.
    """
    _inherit = 'mis.report.instance'
    
    def _compute_matrix(self):
        """
        This is the main method that computes the KPI matrix for the report instance while
        injecting partner KPIs where applicable and adding drilldowns.
        """

        if not any(kpi.display_details_by_partner for kpi in self.report_id.kpi_ids):
            return super()._compute_matrix()

        aep = AEP(
            self.query_company_ids,
            self.currency_id,
            self.report_id.account_model
        )
        for kpi in self.report_id.all_kpi_ids:
            for expression in kpi.expression_ids:
                if expression.name:
                    aep.parse_expr(expression.name)

        matrix = self.report_id.prepare_kpi_matrix(self.multi_company)

        partner_kpis_by_parent = self._build_partner_kpis_by_parent()

        for partner_kpis in partner_kpis_by_parent.values():
            for partner_kpi in partner_kpis:
                if partner_kpi.expression:
                    aep.parse_expr(partner_kpi.expression)

        aep.done_parsing()

        self._add_partner_detail_rows(matrix, partner_kpis_by_parent)

        self._compute_matrix_for_periods(
            self.report_id,
            aep,
            matrix,
            partner_kpis_by_parent,
        )

        matrix.compute_comparisons()
        matrix.compute_sums()

        self._filter_empty_partner_rows(matrix, partner_kpis_by_parent)
        
        self._post_process_matrix_drilldowns(matrix)

        return matrix


    def _build_partner_kpis_by_parent(self):
        """
        Build a dictionary of partner KPIs grouped by their parent KPI.
        """
        partner_kpis_by_parent = {}
        
        for kpi in self.report_id.kpi_ids:
            if not kpi.display_details_by_partner:
                continue

            if not self._is_expression_valid_for_partner_breakdown(kpi.expression):
                _logger.info(f"Skipping partner breakdown for KPI {kpi.name}: unsuitable expression")
                continue
            
            partners = self._get_partners_for_kpi(kpi)
            
            if not partners:
                continue
                
            partner_kpis = []
            sequence = kpi.sequence
            for idx, partner_info in enumerate(partners, 1):
                partner_kpi = self._create_partner_kpi(
                    kpi, partner_info, sequence + (idx * 0.01)
                )
                partner_kpis.append(partner_kpi)
            
            partner_kpis_by_parent[kpi] = partner_kpis
        
        return partner_kpis_by_parent

    def _add_partner_detail_rows(self, matrix, partner_kpis_by_parent):
        """
        Add partner KPIs as detail rows in the matrix, similar to account details.
        """
        class PartnerKpiMatrixRow(KpiMatrixRow):
            def __init__(self, matrix, kpi, partner_label, parent_row=None):
                super().__init__(matrix, kpi, account_id=None, parent_row=parent_row)
                self._partner_label = partner_label
            
            @property
            def label(self):
                return self._partner_label
        
        if not hasattr(matrix, '_partner_row_map'):
            matrix._partner_row_map = {}
            matrix._next_partner_row_id = -1

        for parent_kpi, partner_kpis in partner_kpis_by_parent.items():
            if parent_kpi not in matrix._kpi_rows:
                continue
                
            parent_row = matrix._kpi_rows[parent_kpi]
            
            if parent_kpi not in matrix._detail_rows:
                matrix._detail_rows[parent_kpi] = {}
            
            for partner_kpi in partner_kpis:
                string_key = f"partner_{partner_kpi.partner_id}_acc_{partner_kpi.account_id}"
                
                detail_key = matrix._next_partner_row_id
                matrix._next_partner_row_id -= 1
                matrix._partner_row_map[string_key] = detail_key
                
                detail_row = PartnerKpiMatrixRow(
                    matrix, 
                    partner_kpi, 
                    partner_kpi.description,
                    parent_row=parent_row
                )
                matrix._detail_rows[parent_kpi][detail_key] = detail_row

    def _compute_period(self, report, aep, matrix, period, partner_kpis_by_parent):
        """
        Compute a single period column based on its source.
        """
        description = None
        if period.mode != "none" and self.display_columns_description:
            if period.date_from == period.date_to and period.date_from:
                description = self._format_date(period.date_from)
            elif period.date_from and period.date_to:
                date_from = self._format_date(period.date_from)
                date_to = self._format_date(period.date_to)
                description = _(
                    "from %(date_from)s to %(date_to)s",
                    date_from=date_from,
                    date_to=date_to,
                )

        if period.source in ("actuals", "actuals_alt"):
            if not period.date_from or not period.date_to:
                raise UserError(
                    _("Column %s with move lines source must have from/to dates.")
                    % (period.name,)
                )

            report.declare_and_compute_period(
                matrix,
                period.id,
                period.name,
                description,
                aep,
                period.date_from,
                period.date_to,
                subkpis_filter=period.subkpi_ids,
                get_additional_move_line_filter=period._get_additional_move_line_filter,
                get_additional_query_filter=period._get_additional_query_filter,
                no_auto_expand_accounts=self.no_auto_expand_accounts,
            )
            
            self._compute_partner_details_for_period(matrix, period, aep, partner_kpis_by_parent)
            
        elif period.source == "sumcol":
            self._add_column_sumcol(aep, matrix, period, period.name, description)
        elif period.source == "cmpcol":
            self._add_column_cmpcol(aep, matrix, period, period.name, description)

    def _compute_partner_details_for_period(self, matrix, period, aep, partner_kpis_by_parent):
        """
        Compute values for partner detail rows for a given period.
        """
        _logger.info(f"Computing partner details for period {period.name}")
        expression_evaluator = ExpressionEvaluator(
            aep,
            period.date_from,
            period.date_to,
            period._get_additional_move_line_filter(),
            period.source_aml_model_name,
        )
        
        for parent_kpi, partner_kpis in partner_kpis_by_parent.items():
            _logger.info(f"Processing {len(partner_kpis)} partner KPIs for parent {parent_kpi.name}")
            
            for partner_kpi in partner_kpis:
                string_key = f"partner_{partner_kpi.partner_id}_acc_{partner_kpi.account_id}"
                detail_key = getattr(matrix, '_partner_row_map', {}).get(string_key)
                
                if parent_kpi not in matrix._detail_rows:
                    _logger.warning(f"Parent KPI {parent_kpi.name} not in detail_rows")
                    continue
                if detail_key is None or detail_key not in matrix._detail_rows[parent_kpi]:
                    _logger.warning(f"Detail key {detail_key} not found in detail_rows for {parent_kpi.name}")
                    continue
                
                _logger.info(f"Computing values for partner KPI {partner_kpi.name} (expression: {partner_kpi.expression})")
                
                expressions = partner_kpi._get_expressions(period.subkpi_ids if period.subkpi_ids else None)
                
                locals_dict = self.report_id.prepare_locals_dict()
                
                try:
                    vals, drilldown_args, name_error = expression_evaluator.eval_expressions(
                        expressions, 
                        locals_dict
                    )
                    
                    _logger.info(f"Partner KPI {partner_kpi.name} evaluated to: {vals}")
                    
                    if name_error:
                        _logger.warning(f"Name error evaluating partner KPI {partner_kpi.name}")
                    
                    matrix.set_values_detail_account(
                        parent_kpi,
                        period.id,
                        detail_key,
                        vals,
                        drilldown_args
                    )
                except Exception as e:
                    _logger.error(
                        f"Error computing partner KPI {partner_kpi.name}: {e}",
                        exc_info=True
                    )

    def _compute_matrix_for_periods(self, report, aep, matrix, partner_kpis_by_parent):
        """
        Iterate through periods and compute their values.
        """
        for period in self.period_ids:
            self._compute_period(report, aep, matrix, period, partner_kpis_by_parent)

    def _filter_empty_partner_rows(self, matrix, partner_kpis_by_parent):
        """
        Remove partner rows that have no values (0.0) in any column, including comparison columns.
        """
        for parent_kpi in partner_kpis_by_parent.keys():
            if parent_kpi not in matrix._detail_rows:
                continue
                
            for detail_key in list(matrix._detail_rows[parent_kpi].keys()):
                if not isinstance(detail_key, int) or detail_key >= 0:
                    continue
                    
                row = matrix._detail_rows[parent_kpi][detail_key]
                
                has_value = False
                for cell in row.iter_cells():
                    if cell and cell.val is not None:
                        val = cell.val
                        if val == 0:
                            continue
                        if isinstance(val, float) and abs(val) < 0.00001:
                            continue
                        
                        has_value = True
                        break
                
                if not has_value:
                    _logger.info(f"Removing partner detail row {row.label} with zero values")
                    del matrix._detail_rows[parent_kpi][detail_key]

    def _post_process_matrix_drilldowns(self, matrix):
        """
        Iterate through the matrix to fix/add drilldown arguments.
        """
        for row in matrix.iter_rows():
            kpi = row.kpi
            
            is_partner_detail = hasattr(row, '_partner_label')

            if is_partner_detail:
                partner_id = kpi.partner_id
                parent_kpi_id = row.parent_row.kpi.id if row.parent_row else kpi.id

            for cell, period in zip(row.iter_cells(), self.period_ids):
                if cell is None:
                    continue

                if is_partner_detail:
                    if not cell.drilldown_arg:
                        cell.drilldown_arg = {"expr": kpi.expression}

                    if cell.drilldown_arg:
                        cell.drilldown_arg["kpi_id"] = parent_kpi_id
                        cell.drilldown_arg["partner_id"] = partner_id.id
                        cell.drilldown_arg["period_id"] = period.id
                elif not cell.drilldown_arg:
                    cell.drilldown_arg = {
                        "period_id": period.id,
                        "kpi_id": kpi.id,
                    }

    def _is_expression_valid_for_partner_breakdown(self, expression):
        """
        Check if an expression is suitable for partner breakdown, 
        that is excludes expressions without an accounting variable, 
        or with partner already specified.
        """
        if not expression:
            return False
        
        if not AEP.has_account_var(expression):
            return False
        
        if re.search(r"['\"]partner_id['\"]", expression):
            _logger.info(f"Expression already filters by partner_id: {expression}")
            return False
        
        if re.search(r"['\"]commercial_partner_id['\"]", expression):
            _logger.info(f"Expression already filters by commercial_partner_id: {expression}")
            return False
        
        return True

    def _get_partners_for_kpi(self, kpi):
        """
        Get list of partners for this KPI across ALL periods.
        """
        if not self.period_ids:
            return []
        
        temp_aep = self.report_id._prepare_aep(self.query_company_ids, self.currency_id)
        
        all_partners = {}
        
        for period in self.period_ids:
            model_name, fields_to_read, has_balance = self._get_kpi_query_params(period)
            if not model_name:
                continue
            
            domain = self._get_kpi_query_domain(kpi, temp_aep, period, model_name)
            if domain is None:
                continue

            Model = self.env[model_name]
            
            groups = Model.read_group(
                domain, 
                fields_to_read, 
                ['partner_id', 'account_id'],
                lazy=False
            )
            
            period_partners = self._process_partner_groups(groups, has_balance)
            
            for partner_info in period_partners:
                key = (partner_info['partner_id'], partner_info['account_id'])
                if key not in all_partners:
                    all_partners[key] = partner_info
        
        result = list(all_partners.values())
        result.sort(key=lambda x: (x['account_name'], abs(x.get('balance', 0))), reverse=True)
        
        return result

    def _get_kpi_query_params(self, period):
        """
        Determine model, fields to read and balance availability.
        """
        model_name = period.source_aml_model_name
        if not model_name and self.report_id.move_lines_source:
            model_name = self.report_id.move_lines_source.model
        if not model_name:
            model_name = 'account.move.line'
        
        Model = self.env[model_name]
        
        if 'partner_id' not in Model._fields or 'account_id' not in Model._fields:
            return None, None, None
            
        fields_to_read = ['partner_id', 'account_id']
        has_balance = 'balance' in Model._fields
        has_debit_credit = 'debit' in Model._fields and 'credit' in Model._fields
        
        if has_balance:
            fields_to_read.append('balance')
        elif has_debit_credit:
            fields_to_read.extend(['debit', 'credit'])
        else:
            return None, None, None
            
        return model_name, fields_to_read, has_balance

    def _get_kpi_query_domain(self, kpi, aep, period, model_name):
        """
        Construct the domain for the KPI query.
        """
        try:
            domain = aep.get_aml_domain_for_expr(
                kpi.expression, 
                period.date_from, 
                period.date_to
            )
        except Exception as e:
            _logger.warning(
                f"Could not extract domain from expression {kpi.expression}: {e}"
            )
            return None

        target_move_domain = self.report_id._get_target_move_domain(
            self.target_move, model_name
        )
        return expression.AND([domain, target_move_domain])

    def _process_partner_groups(self, groups, has_balance):
        """
        Process read_group results to aggregate by company.
        """
        partner_ids = {g['partner_id'][0] for g in groups if g.get('partner_id')}
        partners = self.env['res.partner'].browse(partner_ids)
        partner_map = {p.id: p.commercial_partner_id for p in partners}
        
        account_ids = {g['account_id'][0] for g in groups if g.get('account_id')}
        accounts = self.env['account.account'].browse(account_ids)
        account_map = {a.id: a for a in accounts}

        company_balances = {}
        for group in groups:
            partner_data = group.get('partner_id')
            account_data = group.get('account_id')
            if not partner_data or not account_data:
                continue
            
            p_id = partner_data[0]
            commercial_partner = partner_map.get(p_id)
            if not commercial_partner or not commercial_partner.is_company:
                continue

            acc_id = account_data[0]
            account = account_map.get(acc_id)
            if not account:
                continue

            partner_id = commercial_partner.id
            partner_name = commercial_partner.name
            
            account_name = f"{account.code} {account.name}"
            if self.multi_company:
                account_name = f"{account_name} [{account.company_id.name}]"

            if has_balance:
                balance = group['balance']
            else:
                balance = (group.get('debit') or 0.0) - (group.get('credit') or 0.0)
            
            key = (partner_id, acc_id)
            if key not in company_balances:
                company_balances[key] = {
                    'partner_id': partner_id,
                    'partner_name': partner_name,
                    'partner_vat': commercial_partner.vat and commercial_partner.vat.strip() or False,
                    'account_id': acc_id,
                    'account_name': account_name,
                    'balance': 0.0,
                }
            company_balances[key]['balance'] += balance

        result = [cb for cb in company_balances.values() if abs(cb['balance']) > 0.01]
        result.sort(key=lambda x: (x['account_name'], abs(x['balance'])), reverse=True)
        
        return result

    def _create_partner_kpi(self, kpi, partner_info, sequence):
        """
        Create a partner sub-KPI.
        """
        partner_id = partner_info['partner_id']
        partner_name = partner_info['partner_name']
        partner_vat = partner_info.get('partner_vat') or False
        account_id = partner_info['account_id']
        account_name = partner_info['account_name']
        expression = self._add_partner_filter_to_expression(kpi.expression, partner_id, account_id)
        
        vat_cc = False
        vat_num = False
        if partner_vat:
            m = re.match(r'^\s*([A-Za-z]{2})\s*(.+)$', partner_vat.strip())
            if m:
                vat_cc = m.group(1).upper()
                vat_num = m.group(2).strip()
            else:
                vat_num = partner_vat.strip()

        description = f"{account_name} → {partner_name}"
        if kpi.show_vat_columns:
            if vat_cc and vat_num:
                description = f"{description} ({vat_cc} {vat_num})"
            elif partner_vat:
                description = f"{description} ({partner_vat})"

        subkpi_vals = {
            'report_id': kpi.report_id.id,
            'sequence': sequence,
            'description': description,
            'name': f"{kpi.name}_acc{account_id}_partner_{partner_id}",
            'type': 'num',
            'expression': expression,
            'expression_ids': [(0, 0, {'name': expression})],
            'compare_method': kpi.compare_method or 'diff',
            'account_id': account_id,
            'partner_id': partner_id,
            'parent_kpi_id': kpi.id,
            'partner_vat': partner_vat,
            'partner_vat_country': vat_cc or False,
            'partner_vat_number': vat_num or False,
        }
        
        if kpi.style_id_for_partner_details:
            subkpi_vals['style_id'] = kpi.style_id_for_partner_details.id

        return self.env['mis.report.kpi'].new(subkpi_vals)
    
    def _add_partner_filter_to_expression(self, expression, partner_id, account_id):
        if not expression or not partner_id or not account_id:
            return expression

        partner_filter = f"('partner_id', 'child_of', {partner_id})"
        account_filter = f"('account_id', '=', {account_id})"

        def add_filter(match):
            kw = match.group('kw')
            acc_domain = match.group('acc')
            aml_domain = match.group('aml')
            
            filters = f"{partner_filter}, {account_filter}"
            
            if not acc_domain:
                return f"{kw}[][{filters}]"
            
            if not aml_domain:
                return f"{kw}{acc_domain}[{filters}]"
            
            return f"{kw}{acc_domain}{aml_domain[:-1]}, {filters}]"

        acc_re = re.compile(
            r"(?P<kw>\b(?:bal|pbal|nbal|cbal|dbal|crd|deb|avg|pavg|navg|cavg|davg|sum|balp)\b)\s*(?P<acc>\[.*?\])?\s*(?P<aml>\[.*?\])?",
            re.IGNORECASE
        )

        return acc_re.sub(add_filter, expression)


    def drilldown(self, arg):
        """
        Handle drilldown for partner sub-KPIs.
        """
        self.ensure_one()
        action = super().drilldown(arg)
                
        if action and isinstance(arg, dict) and arg.get("partner_id"):
            partner = self.env['res.partner'].browse(arg["partner_id"])
            if partner.exists():
                partner_display = partner.display_name
                vat = partner.commercial_partner_id.vat and partner.commercial_partner_id.vat.strip()
                if vat:
                    partner_display = f"{partner_display} ({vat})"
                action['name'] = f"{action.get('name', '')} - {partner_display}"

        return action
    