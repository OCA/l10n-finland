# Copyright 2026 Cetmix Nordic Ltd
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import re

from odoo import api, fields, models
from odoo.exceptions import UserError


class MisReportTemplateExport(models.TransientModel):
    _name = "mis.report.template.export"
    _description = "Export MIS Report Template"

    report_id = fields.Many2one(
        comodel_name="mis.report",
        string="Report Template",
        required=True,
        ondelete="cascade",
    )
    module_name = fields.Char(
        string="Module",
        required=True,
        help="Technical name of the module the XML file is meant for. Records "
        "that already have an XML id in this module keep it; the others get "
        "new ids derived from the report name.",
    )
    lang = fields.Selection(
        selection="_get_languages",
        string="Language",
        required=True,
        default=lambda self: self.env.lang or "en_US",
        help="Language in which names and descriptions are exported.",
    )
    link_records = fields.Boolean(
        string="Link Records to the Module",
        default=True,
        help="Give the exported records the XML ids used in the file. When the "
        "module is then installed or updated in this database, it updates "
        "these records instead of creating a second copy of the report "
        "template (and of its styles, whose names must be unique). From then "
        "on the module owns the records: changes made in Odoo are overwritten "
        "by the next module update unless they are exported again.",
    )
    file_data = fields.Binary(string="File", readonly=True, attachment=False)
    file_name = fields.Char(readonly=True)

    @api.model
    def _get_languages(self):
        return self.env["res.lang"].get_installed()

    @api.model
    def default_get(self, fields_list):
        """Propose the module of the report's XML id, if it has one."""
        values = super().default_get(fields_list)
        report = self.env["mis.report"].browse(values.get("report_id"))
        if report and "module_name" in fields_list and not values.get("module_name"):
            xmlid = report.get_external_id().get(report.id) or ""
            if xmlid and not xmlid.startswith("__"):
                values["module_name"] = xmlid.split(".", 1)[0]
        return values

    def action_export(self):
        self.ensure_one()
        module = (self.module_name or "").strip()
        if not re.fullmatch(r"[a-z0-9_]+", module):
            raise UserError(
                self.env._(
                    "The module name %(module)s is not a valid technical name: "
                    "use lowercase letters, digits and underscores only.",
                    module=module,
                )
            )
        report = self.report_id.with_context(lang=self.lang)
        xml = report._template_export_xml(module, link=self.link_records)
        self.write(
            {
                "module_name": module,
                "file_data": base64.b64encode(xml.encode()),
                "file_name": f"mis_report_{report._template_export_slug()}.xml",
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": (
                f"/web/content/?model={self._name}&id={self.id}"
                "&field=file_data&filename_field=file_name&download=true"
            ),
            "target": "download",
        }
