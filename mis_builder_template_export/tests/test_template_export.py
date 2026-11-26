# Copyright 2026 Cetmix Nordic Ltd
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io

from odoo import Command
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
