# Copyright 2026 Cetmix Nordic Ltd
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re
import unicodedata
from xml.sax.saxutils import escape, quoteattr

from odoo import models
from odoo.exceptions import UserError

# Fields that are never written to the exported XML.
SKIP_FIELDS = {
    "id",
    "display_name",
    "create_uid",
    "create_date",
    "write_uid",
    "write_date",
}


def _slug(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_") or "report"


class MisReport(models.Model):
    _inherit = "mis.report"

    def _template_export_slug(self):
        self.ensure_one()
        return _slug(self.with_context(lang="en_US").name)

    def _template_export_xml(self, module, link=False):
        """Return the report template as Odoo data XML.

        The XML contains the report, its sub-KPIs, queries, KPIs, KPI
        expressions of multi KPIs and subreports, and the styles they use that
        have no XML id. Records with an XML id in ``module`` keep it, the
        others get ids derived from the report name. Translatable fields are
        written in the language of the context.

        With ``link``, the exported records that had no XML id get the ids
        used in the file, so that installing or updating ``module`` in this
        database updates them instead of creating copies (a copied style would
        also violate the unique style name).
        """
        self.ensure_one()
        exporter = _TemplateExporter(self, module)
        xml = exporter.export()
        if link:
            exporter.link()
        return xml


class _TemplateExporter:
    def __init__(self, report, module):
        self.report = report
        self.env = report.env
        self.module = module
        self.ids = {}  # record -> XML id used in the exported file
        self.generated = set()  # records whose XML id is generated
        # names already used by the module, so generated ids do not clash
        self.used = set(
            self.env["ir.model.data"]
            .sudo()
            .search([("module", "=", module)])
            .mapped("name")
        )
        self.missing = []

    # --- XML ids -----------------------------------------------------------

    def _stable_xmlid(self, record):
        """XML id that a module can reference, preferring the target module.

        Returns '' when the record has none (ids of data exports, which start
        with '__', do not count).
        """
        xmlids = [
            xmlid
            for xmlid in record._get_external_ids().get(record.id, [])
            if not xmlid.startswith("__")
        ]
        own = [x for x in xmlids if x.startswith(self.module + ".")]
        return (own or xmlids or [""])[0]

    def _local(self, xmlid):
        prefix = self.module + "."
        return xmlid[len(prefix) :] if xmlid.startswith(prefix) else xmlid

    def _assign(self, record, generated):
        xmlid = self._stable_xmlid(record)
        if xmlid.startswith(self.module + "."):
            local = self._local(xmlid)
        else:
            local, n = generated, 2
            while local in self.used:
                local, n = f"{generated}_{n}", n + 1
            self.generated.add(record)
        self.used.add(local)
        self.ids[record] = local

    def _ref(self, target, record, fname):
        if target in self.ids:
            return self.ids[target]
        xmlid = self._stable_xmlid(target)
        if not xmlid:
            self.missing.append(
                f"{record._description} '{record.display_name}', field {fname}: "
                f"{target._description} '{target.display_name}'"
            )
            return "MISSING"
        return self._local(xmlid)

    # --- Fields ------------------------------------------------------------

    @staticmethod
    def _exported_fields(record):
        for fname, field in record._fields.items():
            if fname in SKIP_FIELDS or field.type in ("one2many", "binary"):
                continue
            if field.related or field.company_dependent:
                continue
            if field.compute and not field.inverse:
                continue
            if not field.store and not field.inverse:
                continue
            if (
                record._name == "mis.report.kpi"
                and fname == "expression"
                and record.multi
            ):
                # multi KPIs keep their expressions in expression_ids
                continue
            yield fname, field

    def _field_xml(self, record, fname, field):
        value = record[fname]
        name = quoteattr(fname)
        if field.type == "boolean":
            return f"<field name={name} eval={quoteattr(str(bool(value)))} />"
        if field.type == "many2one":
            if not value:
                return f'<field name={name} eval="False" />'
            ref = quoteattr(self._ref(value, record, fname))
            return f"<field name={name} ref={ref} />"
        if field.type == "many2many":
            refs = ", ".join(f"ref({self._ref(v, record, fname)!r})" for v in value)
            return f"<field name={name} eval={quoteattr(f'[(6, 0, [{refs}])]')} />"
        if field.type in ("integer", "float", "monetary"):
            return f"<field name={name}>{value}</field>"
        if value is False or value is None or value == "":
            return None
        return f"<field name={name}>{escape(str(value))}</field>"

    def _record_xml(self, record):
        lines = [
            f"    <record id={quoteattr(self.ids[record])} "
            f"model={quoteattr(record._name)}>"
        ]
        for fname, field in self._exported_fields(record):
            line = self._field_xml(record, fname, field)
            if line:
                lines.append(f"        {line}")
        lines.append("    </record>")
        return "\n".join(lines)

    # --- Export ------------------------------------------------------------

    def link(self):
        """Give the exported records without an XML id the ids of the file."""
        IrModelData = self.env["ir.model.data"].sudo()
        for record in self.generated:
            if self._stable_xmlid(record):
                continue  # owned by another module: the file holds a copy
            IrModelData.create(
                {
                    "module": self.module,
                    "name": self.ids[record],
                    "model": record._name,
                    "res_id": record.id,
                }
            )

    def export(self):
        report = self.report
        rslug = report._template_export_slug()
        self._assign(report, f"report_{rslug}")
        subkpis = report.subkpi_ids.sorted(lambda s: (s.sequence, s.id))
        for subkpi in subkpis:
            self._assign(subkpi, f"subkpi_{rslug}_{subkpi.name}")
        queries = report.query_ids.sorted("id")
        for query in queries:
            self._assign(query, f"query_{rslug}_{query.name}")
        kpis = report.kpi_ids.sorted(lambda k: (k.sequence, k.id))
        expressions = self.env["mis.report.kpi.expression"]
        for kpi in kpis:
            self._assign(kpi, f"kpi_{rslug}_{kpi.name}")
            if kpi.multi:
                for expression in kpi.expression_ids:
                    expressions |= expression
                    sub_name = expression.subkpi_id.name or str(expression.id)
                    self._assign(expression, f"kpi_{rslug}_{kpi.name}_{sub_name}")
        subreports = report.subreport_ids.sorted("id")
        for subreport in subreports:
            self._assign(subreport, f"subreport_{rslug}_{subreport.name}")

        # Styles without an XML id, or owned by the target module, are
        # exported with the report (a module drops records it no longer
        # declares, so its own styles must stay in the file).
        styles = self.env["mis.report.style"]
        for record in [report, *subkpis, *queries, *kpis, *expressions]:
            for fname, field in self._exported_fields(record):
                if field.type != "many2one":
                    continue
                if field.comodel_name != "mis.report.style":
                    continue
                style = record[fname]
                if not style or style in self.ids:
                    continue
                xmlid = self._stable_xmlid(style)
                if not xmlid or xmlid.startswith(self.module + "."):
                    styles |= style
        for style in styles:
            self._assign(style, f"style_{_slug(style.name)}")

        records = [
            *styles,
            report,
            *subkpis,
            *queries,
            *kpis,
            *expressions,
            *subreports,
        ]
        body = "\n".join(self._record_xml(record) for record in records)
        if self.missing:
            raise UserError(
                self.env._(
                    "These references point to records without an XML id, so "
                    "they cannot be exported:\n%(missing)s",
                    missing="\n".join(self.missing),
                )
            )
        title = escape(report.name.replace("--", "- -"))
        return (
            '<?xml version="1.0" encoding="utf-8" ?>\n'
            f"<!-- MIS report template: {title} -->\n"
            f"<odoo>\n{body}\n</odoo>\n"
        )
