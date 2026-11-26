# Copyright 2026 Cetmix Nordic Ltd
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tools.convert import convert_xml_import

from odoo.addons.base.tests.common import BaseCommon

MODULE = "test_mis_template_export"


class TestTemplateExport(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.style = cls.env["mis.report.style"].create(
            {
                "name": "Export Test Bold",
                "font_weight_inherit": False,
                "font_weight": "bold",
                "indent_level_inherit": False,
                "indent_level": 2,
            }
        )
        cls.report = cls.env["mis.report"].create(
            {
                "name": "Export Test Report",
                "description": "Report used by the export tests",
                "style_id": cls.style.id,
            }
        )
        cls.subkpi_a = cls.env["mis.report.subkpi"].create(
            {"report_id": cls.report.id, "name": "sub_a", "description": "Sub A"}
        )
        cls.subkpi_b = cls.env["mis.report.subkpi"].create(
            {
                "report_id": cls.report.id,
                "name": "sub_b",
                "description": "Sub B",
                "sequence": 2,
            }
        )
        cls.kpi_sales = cls.env["mis.report.kpi"].create(
            {
                "report_id": cls.report.id,
                "name": "sales",
                "description": "Sales",
                "expression": "-balp[('account_type', '=', 'income')][]",
                "auto_expand_accounts": True,
                "style_id": cls.style.id,
                "sequence": 10,
            }
        )
        cls.kpi_multi = cls.env["mis.report.kpi"].create(
            {
                "report_id": cls.report.id,
                "name": "split",
                "description": "Split",
                "multi": True,
                "sequence": 20,
                "expression_ids": [
                    Command.create({"name": "sales", "subkpi_id": cls.subkpi_a.id}),
                    Command.create({"name": "sales * 2", "subkpi_id": cls.subkpi_b.id}),
                ],
            }
        )
        cls.query = cls.env["mis.report.query"].create(
            {
                "report_id": cls.report.id,
                "name": "lines",
                "model_id": cls.env.ref("account.model_account_move_line").id,
                "field_ids": [
                    Command.set(
                        [cls.env.ref("account.field_account_move_line__debit").id]
                    )
                ],
                "date_field": cls.env.ref("account.field_account_move_line__date").id,
                "aggregate": "sum",
            }
        )

    def _import(self, xml):
        xml_file = io.BytesIO(xml.encode())
        xml_file.name = "mis_report_export_test_report.xml"
        convert_xml_import(self.env, MODULE, xml_file, mode="init")
        return self.env.ref(f"{MODULE}.report_export_test_report")

    def test_export_copy(self):
        """Without linking, the file creates a copy of the report template."""
        xml = self.report._template_export_xml(MODULE)
        self.assertIn('id="style_export_test_bold"', xml)
        self.assertIn('id="kpi_export_test_report_sales"', xml)
        self.assertFalse(
            self.env["ir.model.data"].search([("module", "=", MODULE)]),
            "Nothing is linked without link=True",
        )

        # style names are unique: free the name for the copy
        self.style.name = "Export Test Bold (original)"
        self.env.flush_all()
        copy = self._import(xml)
        self.assertNotEqual(copy, self.report)
        self.assertEqual(copy.name, self.report.name)
        self.assertEqual(copy.description, self.report.description)

        # The style without an XML id is exported and used by the copy.
        copy_style = self.env.ref(f"{MODULE}.style_export_test_bold")
        self.assertNotEqual(copy_style, self.style)
        self.assertEqual(copy.style_id, copy_style)
        self.assertEqual(copy_style.font_weight, "bold")
        self.assertFalse(copy_style.font_weight_inherit)
        self.assertEqual(copy_style.indent_level, 2)

        self.assertEqual(
            copy.kpi_ids.sorted("sequence").mapped("name"), ["sales", "split"]
        )
        sales = copy.kpi_ids.filtered(lambda k: k.name == "sales")
        self.assertEqual(sales.expression, self.kpi_sales.expression)
        self.assertTrue(sales.auto_expand_accounts)
        self.assertEqual(sales.style_id, copy_style)

        self.assertEqual(copy.subkpi_ids.mapped("name"), ["sub_a", "sub_b"])
        split = copy.kpi_ids.filtered(lambda k: k.name == "split")
        self.assertTrue(split.multi)
        self.assertEqual(
            {(e.subkpi_id.name, e.name) for e in split.expression_ids},
            {("sub_a", "sales"), ("sub_b", "sales * 2")},
        )

        self.assertEqual(copy.query_ids.name, "lines")
        self.assertEqual(copy.query_ids.field_ids, self.query.field_ids)
        self.assertEqual(copy.query_ids.date_field, self.query.date_field)

    def test_export_linked(self):
        """Linked records are updated by the module instead of copied."""
        # an id from a data export must not be mistaken for the module's
        self.env["ir.model.data"].create(
            {
                "module": "__export__",
                "name": "mis_report_style_1_abc",
                "model": "mis.report.style",
                "res_id": self.style.id,
            }
        )
        xml = self.report._template_export_xml(MODULE, link=True)
        self.assertEqual(
            self.env.ref(f"{MODULE}.report_export_test_report"), self.report
        )
        self.assertEqual(self.env.ref(f"{MODULE}.style_export_test_bold"), self.style)
        self.assertEqual(
            self.env.ref(f"{MODULE}.kpi_export_test_report_split_sub_b"),
            self.kpi_multi.expression_ids.filtered(
                lambda e: e.subkpi_id == self.subkpi_b
            ),
        )

        self.kpi_sales.description = "Changed in Odoo"
        self.assertEqual(self._import(xml), self.report)
        self.assertEqual(self.kpi_sales.description, "Sales")
        self.assertEqual(
            self.env["mis.report"].search_count([("name", "=", "Export Test Report")]),
            1,
        )
        self.assertEqual(len(self.report.kpi_ids), 2)
        self.assertEqual(len(self.kpi_multi.expression_ids), 2)

        # exporting again gives the same file and links nothing new
        data_count = self.env["ir.model.data"].search_count([("module", "=", MODULE)])
        self.assertEqual(self.report._template_export_xml(MODULE, link=True), xml)
        self.assertEqual(
            self.env["ir.model.data"].search_count([("module", "=", MODULE)]),
            data_count,
        )

    def test_existing_xml_ids_are_kept(self):
        self.env["ir.model.data"].create(
            {
                "module": MODULE,
                "name": "my_report",
                "model": "mis.report",
                "res_id": self.report.id,
            }
        )
        xml = self.report._template_export_xml(MODULE)
        self.assertIn('<record id="my_report" model="mis.report">', xml)
        self.assertIn('ref="my_report"', xml)

    def test_reference_without_xml_id(self):
        other = self.env["mis.report"].create({"name": "Other Report"})
        self.env["mis.report.subreport"].create(
            {"report_id": self.report.id, "name": "other", "subreport_id": other.id}
        )
        with self.assertRaisesRegex(UserError, "Other Report"):
            self.report._template_export_xml(MODULE)

    def test_wizard(self):
        wizard = (
            self.env["mis.report.template.export"]
            .with_context(default_report_id=self.report.id)
            .create({"module_name": MODULE})
        )
        action = wizard.action_export()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(wizard.file_name, "mis_report_export_test_report.xml")
        xml = base64.b64decode(wizard.file_data).decode()
        self.assertIn('id="report_export_test_report"', xml)
        self.assertTrue(wizard.link_records)
        self.assertEqual(
            self.env.ref(f"{MODULE}.report_export_test_report"), self.report
        )

        wizard.module_name = "Not Valid"
        with self.assertRaises(UserError):
            wizard.action_export()

    def test_wizard_proposes_module_of_xml_id(self):
        self.env["ir.model.data"].create(
            {
                "module": MODULE,
                "name": "my_report",
                "model": "mis.report",
                "res_id": self.report.id,
            }
        )
        values = (
            self.env["mis.report.template.export"]
            .with_context(default_report_id=self.report.id)
            .default_get(["report_id", "module_name"])
        )
        self.assertEqual(values["module_name"], MODULE)

    # --- Report instances ---------------------------------------------------

    def _instance(self):
        """A comparison instance whose compare and sum columns come before
        the columns they use, with a date range type that has no XML id."""
        range_type = self.env["date.range.type"].create(
            {"name": "Export Test Quarters", "allow_overlap": False}
        )
        instance = self.env["mis.report.instance"].create(
            {
                "name": "Export Test Instance",
                "report_id": self.report.id,
                "comparison_mode": True,
                "landscape_pdf": True,
            }
        )
        Period = self.env["mis.report.instance.period"]
        current = Period.create(
            {
                "report_instance_id": instance.id,
                "name": "Current",
                "sequence": 30,
                "mode": "relative",
                "type": "date_range",
                "date_range_type_id": range_type.id,
                "offset": 0,
            }
        )
        fixed = Period.create(
            {
                "report_instance_id": instance.id,
                "name": "Year 2025",
                "sequence": 40,
                "mode": "fix",
                "manual_date_from": "2025-01-01",
                "manual_date_to": "2025-12-31",
                "subkpi_ids": [Command.set(self.subkpi_a.ids)],
            }
        )
        compare = Period.create(
            {
                "report_instance_id": instance.id,
                "name": "Change",
                "sequence": 10,
                "mode": "none",
                "source": "cmpcol",
                "source_cmpcol_from_id": fixed.id,
                "source_cmpcol_to_id": current.id,
            }
        )
        total = Period.create(
            {
                "report_instance_id": instance.id,
                "name": "Total",
                "sequence": 20,
                "mode": "none",
                "source": "sumcol",
                "source_sumcol_ids": [
                    Command.create({"period_to_sum_id": current.id, "sign": "+"}),
                    Command.create({"period_to_sum_id": fixed.id, "sign": "-"}),
                ],
            }
        )
        return instance, range_type, (current, fixed, compare, total)

    def test_export_instance_copy(self):
        instance, range_type, _periods = self._instance()
        xml = self.report._template_export_xml(MODULE, instances=instance)
        self.assertIn('id="instance_export_test_instance"', xml)
        self.assertIn('id="date_range_type_export_test_quarters"', xml)
        self.assertNotIn('name="company_id"', xml)
        self.assertNotIn('name="comparison_mode"', xml)
        # a period is written after the periods it compares or sums
        positions = [
            xml.index(f'id="instance_export_test_instance_{name}"')
            for name in ("current", "year_2025", "change", "total")
        ]
        self.assertEqual(positions, sorted(positions))

        self.style.name = "Export Test Bold (original)"
        range_type.name = "Export Test Quarters (original)"
        self.env.flush_all()
        self._import(xml)
        copy = self.env.ref(f"{MODULE}.instance_export_test_instance")
        self.assertNotEqual(copy, instance)
        self.assertEqual(
            copy.report_id, self.env.ref(f"{MODULE}.report_export_test_report")
        )
        self.assertTrue(copy.comparison_mode)
        self.assertTrue(copy.landscape_pdf)
        self.env.invalidate_all()  # periods in their database order
        self.assertEqual(copy.company_id, self.env.company)
        self.assertEqual(
            copy.period_ids.mapped("name"), ["Change", "Total", "Current", "Year 2025"]
        )
        by_name = {period.name: period for period in copy.period_ids}
        self.assertEqual(
            by_name["Current"].date_range_type_id,
            self.env.ref(f"{MODULE}.date_range_type_export_test_quarters"),
        )
        self.assertEqual(str(by_name["Year 2025"].manual_date_to), "2025-12-31")
        self.assertEqual(by_name["Year 2025"].subkpi_ids.name, "sub_a")
        self.assertEqual(by_name["Change"].source_cmpcol_from_id, by_name["Year 2025"])
        self.assertEqual(by_name["Change"].source_cmpcol_to_id, by_name["Current"])
        self.assertEqual(
            {
                (s.period_to_sum_id.name, s.sign)
                for s in by_name["Total"].source_sumcol_ids
            },
            {("Current", "+"), ("Year 2025", "-")},
        )
        self.assertEqual(
            by_name["Current"].source_aml_model_id,
            self.env.ref("account.model_account_move_line"),
        )
        # the column takes its dates from the copied date range type
        quarter = self.env["date.range"].create(
            {
                "name": "Export Test Quarter",
                "type_id": by_name["Current"].date_range_type_id.id,
                "date_start": fields.Date.subtract(fields.Date.today(), days=30),
                "date_end": fields.Date.add(fields.Date.today(), days=30),
            }
        )
        self.assertTrue(by_name["Current"].valid)
        self.assertEqual(by_name["Current"].date_from, quarter.date_start)
        self.assertEqual(by_name["Current"].date_to, quarter.date_end)

    def test_exported_instance_computes(self):
        report = self.env["mis.report"].create(
            {
                "name": "Export Test Simple",
                "kpi_ids": [
                    Command.create(
                        {
                            "name": "income",
                            "description": "Income",
                            "expression": "-balp[('account_type', '=', 'income')]",
                        }
                    )
                ],
            }
        )
        instance = self.env["mis.report.instance"].create(
            {
                "name": "Export Test Simple Instance",
                "report_id": report.id,
                "comparison_mode": False,
                "date_from": "2026-01-01",
                "date_to": "2026-12-31",
            }
        )
        xml = instance._template_export_xml(MODULE)
        xml_file = io.BytesIO(xml.encode())
        xml_file.name = "mis_report_export_test_simple.xml"
        convert_xml_import(self.env, MODULE, xml_file, mode="init")
        copy = self.env.ref(f"{MODULE}.instance_export_test_simple_instance")
        self.assertNotEqual(copy, instance)
        self.assertNotEqual(copy.report_id, report)
        result = copy.compute()
        self.assertEqual([row["label"] for row in result["body"]], ["Income"])

    def test_export_instance_linked(self):
        """A linked instance in non-comparison mode keeps its single period."""
        instance = self.env["mis.report.instance"].create(
            {
                "name": "Export Test Single",
                "report_id": self.report.id,
                "comparison_mode": False,
                "date_from": "2026-01-01",
                "date_to": "2026-03-31",
            }
        )
        self.assertFalse(instance.comparison_mode)
        period = instance.period_ids
        self.assertEqual(len(period), 1)
        xml = instance._template_export_xml(MODULE, link=True)
        self.assertIn('id="report_export_test_report"', xml)
        instance.date_to = "2026-06-30"
        self._import(xml)
        self.assertEqual(
            self.env.ref(f"{MODULE}.instance_export_test_single"), instance
        )
        self.assertEqual(str(instance.date_to), "2026-03-31")
        self.assertEqual(instance.period_ids, period)
        self.assertFalse(instance.comparison_mode)
        self.assertEqual(
            self.env["mis.report.instance"].search_count(
                [("name", "=", "Export Test Single")]
            ),
            1,
        )
        self.assertEqual(instance._template_export_xml(MODULE, link=True), xml)

    def test_export_instance_of_other_module(self):
        """An instance of a template of another module refers to it."""
        for record, name in ((self.report, "report"), (self.subkpi_a, "sub_a")):
            self.env["ir.model.data"].create(
                {
                    "module": "other_module",
                    "name": name,
                    "model": record._name,
                    "res_id": record.id,
                }
            )
        instance, _range_type, _periods = self._instance()
        xml = instance._template_export_xml(MODULE)
        self.assertNotIn('model="mis.report"', xml)
        self.assertNotIn("style_export_test_bold", xml)
        self.assertIn('<field name="report_id" ref="other_module.report" />', xml)
        self.assertIn("ref('other_module.sub_a')", xml)
        self.assertIn("MIS report instances of", xml)
        # a template without an XML id must be exported with the instance
        own = self.env["mis.report"].create({"name": "Own Report"})
        own_instance = self.env["mis.report.instance"].create(
            {"name": "Own", "report_id": own.id}
        )
        with self.assertRaisesRegex(UserError, "Own Report"):
            own_instance._template_export_xml(MODULE, with_report=False)

    def test_export_temporary_instance(self):
        instance = self.env["mis.report.instance"].create(
            {"name": "Preview", "report_id": self.report.id, "temporary": True}
        )
        with self.assertRaisesRegex(UserError, "temporary"):
            self.report._template_export_xml(MODULE, instances=instance)

    def test_wizard_instance(self):
        instance, _range_type, _periods = self._instance()
        Wizard = self.env["mis.report.template.export"].with_context(
            default_instance_ids=[instance.id]
        )
        values = Wizard.default_get(["report_id", "instance_ids", "module_name"])
        self.assertEqual(values["report_id"], self.report.id)
        wizard = Wizard.create({"module_name": MODULE})
        self.assertEqual(wizard.report_id, self.report)
        self.assertEqual(wizard.instance_ids, instance)
        self.assertTrue(wizard.export_report)
        wizard.action_export()
        self.assertEqual(wizard.file_name, "mis_report_export_test_report.xml")
        xml = base64.b64decode(wizard.file_data).decode()
        self.assertIn('id="report_export_test_report"', xml)
        self.assertIn('id="instance_export_test_instance"', xml)

        # the template of another module is not exported by default
        self.env["ir.model.data"].search(
            [
                ("module", "=", MODULE),
                ("res_id", "=", self.report.id),
                ("model", "=", "mis.report"),
            ]
        ).module = "other_module"
        wizard = Wizard.create({"module_name": MODULE})
        self.assertFalse(wizard.export_report)
        wizard.action_export()
        self.assertEqual(
            wizard.file_name, "mis_report_instance_export_test_instance.xml"
        )
        xml = base64.b64decode(wizard.file_data).decode()
        self.assertNotIn('model="mis.report"', xml)

        other = self.env["mis.report"].create({"name": "Other Report"})
        wizard.report_id = other
        with self.assertRaises(UserError):
            wizard.action_export()
