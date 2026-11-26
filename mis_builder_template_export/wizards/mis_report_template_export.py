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
    instance_ids = fields.Many2many(
        comodel_name="mis.report.instance",
        string="Report Instances",
        domain="[('report_id', '=', report_id), ('temporary', '=', False)]",
        help="Report instances exported with their periods.",
    )
    export_report = fields.Boolean(
        string="Export the Report Template",
        compute="_compute_export_report",
        store=True,
        readonly=False,
        help="Write the report template to the same file. Without it, the "
        "instances refer to the template by its XML id, for example a "
        "template delivered by another module.",
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
        """Propose the module of the XML id of the exported instances or, when
        exporting a report template, of the report."""
        values = super().default_get(fields_list)
        instances = self.env["mis.report.instance"].browse(
            self._ids_of(values.get("instance_ids"))
        )
        if instances and not values.get("report_id"):
            values["report_id"] = instances[:1].report_id.id
        report = self.env["mis.report"].browse(values.get("report_id"))
        if "module_name" in fields_list and not values.get("module_name"):
            for record in instances or report:
                xmlid = record.get_external_id().get(record.id) or ""
                if xmlid and not xmlid.startswith("__"):
                    values["module_name"] = xmlid.split(".", 1)[0]
                    break
        return values

    @api.model
    def _ids_of(self, value):
        """Record ids of a many2many default: a list of ids or commands."""
        ids = []
        for item in value or []:
            if isinstance(item, int):
                ids.append(item)
            elif item[0] == fields.Command.SET:
                ids += item[2]
            elif item[0] == fields.Command.LINK:
                ids.append(item[1])
        return ids

    @api.depends("report_id", "module_name")
    def _compute_export_report(self):
        for wizard in self:
            module = (wizard.module_name or "").strip()
            wizard.export_report = not (
                wizard.report_id
                and module
                and not wizard.report_id._template_export_owned(module)
            )

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
        if self.instance_ids.report_id - self.report_id:
            raise UserError(
                self.env._(
                    "Only instances of the report template %(report)s can be "
                    "exported with it.",
                    report=self.report_id.display_name,
                )
            )
        with_report = self.export_report or not self.instance_ids
        report = self.report_id.with_context(lang=self.lang)
        xml = report._template_export_xml(
            module,
            link=self.link_records,
            instances=self.instance_ids,
            with_report=with_report,
        )
        if with_report or len(self.instance_ids) > 1:
            file_name = f"mis_report_{report._template_export_slug()}.xml"
        else:
            slug = self.instance_ids._template_export_slug()
            file_name = f"mis_report_instance_{slug}.xml"
        self.write(
            {
                "module_name": module,
                "file_data": base64.b64encode(xml.encode()),
                "file_name": file_name,
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
