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

# Fields of a model that are not written to the exported XML.
SKIP_MODEL_FIELDS = {
    # Follows from the periods and dates; writing it would replace the
    # periods with a default one.
    "mis.report.instance": {"comparison_mode", "temporary"},
}

# Records of these models are referenced from the exported records but not
# written to the file: company relations, so that the records belong to the
# company that installs the module, and date ranges, which only fill in the
# dates that are exported themselves.
SKIP_COMODELS = {"res.company", "date.range"}

# Models of records exported along with the records that use them, when they
# have no XML id of their own (or one in the target module), and the prefix
# of their generated XML ids.
SHARED_MODELS = {
    "mis.report.style": "style",
    "date.range.type": "date_range_type",
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

    def _template_export_owned(self, module):
        """Whether an export for ``module`` must contain this template: it has
        no XML id, or one in ``module``."""
        self.ensure_one()
        xmlid = _TemplateExporter.stable_xmlid(self, module)
        return not xmlid or xmlid.startswith(module + ".")

    def _template_export_xml(
        self, module, link=False, instances=None, with_report=True
    ):
        """Return the report template as Odoo data XML.

        The XML contains the report, its sub-KPIs, queries, KPIs, KPI
        expressions of multi KPIs and subreports, the ``instances`` of the
        report with their periods, and the styles and date range types they
        use that have no XML id. Records with an XML id in ``module`` keep it,
        the others get ids derived from their names. Translatable fields are
        written in the language of the context.

        With ``link``, the exported records that had no XML id get the ids
        used in the file, so that installing or updating ``module`` in this
        database updates them instead of creating copies (a copied style would
        also violate the unique style name).

        Without ``with_report`` only the instances are exported, and they
        refer to the report by its XML id.
        """
        self.ensure_one()
        exporter = _TemplateExporter(
            self, module, instances=instances, with_report=with_report
        )
        xml = exporter.export()
        if link:
            exporter.link()
        return xml


class MisReportInstance(models.Model):
    _inherit = "mis.report.instance"

    def _template_export_slug(self):
        self.ensure_one()
        return _slug(self.with_context(lang="en_US").name)

    def _template_export_xml(self, module, link=False, with_report=None):
        """Return the report instances as Odoo data XML.

        The report template is exported with them when ``with_report`` is
        true. By default it is, unless the template has an XML id of another
        module: then the instances refer to it.
        """
        report = self.report_id
        if len(report) != 1:
            raise UserError(
                self.env._("Only instances of one report template can be exported.")
            )
        if with_report is None:
            with_report = report._template_export_owned(module)
        return report.with_env(self.env)._template_export_xml(
            module, link=link, instances=self, with_report=with_report
        )


class _TemplateExporter:
    def __init__(self, report, module, instances=None, with_report=True):
        self.report = report
        self.env = report.env
        self.module = module
        self.with_report = with_report
        instances = instances or report.env["mis.report.instance"]
        # read the instances in the language of the export
        self.instances = report.env["mis.report.instance"].browse(instances.ids)
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

    @staticmethod
    def stable_xmlid(record, module):
        """XML id that a module can reference, preferring ``module``.

        Returns '' when the record has none (ids of data exports, which start
        with '__', do not count).
        """
        xmlids = [
            xmlid
            for xmlid in record._get_external_ids().get(record.id, [])
            if not xmlid.startswith("__")
        ]
        own = [x for x in xmlids if x.startswith(module + ".")]
        return (own or xmlids or [""])[0]

    def _stable_xmlid(self, record):
        return self.stable_xmlid(record, self.module)

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
        skip = SKIP_MODEL_FIELDS.get(record._name, set())
        for fname, field in record._fields.items():
            if fname in SKIP_FIELDS or fname in skip:
                continue
            if field.type in ("one2many", "binary"):
                continue
            if field.related or field.company_dependent:
                continue
            if field.compute and not field.inverse:
                # computed fields that users can edit are kept
                if field.readonly or not field.store:
                    continue
            if not field.store and not field.inverse:
                continue
            if field.relational and field.comodel_name in SKIP_COMODELS:
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

    def _report_records(self, rslug):
        report = self.report
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
        return [report, *subkpis, *queries, *kpis, *expressions, *subreports]

    @staticmethod
    def _sorted_periods(instance):
        """Periods in sequence order, but a period compared or summed by
        another one first: a record can only refer to records above it."""
        periods = instance.period_ids.sorted(lambda p: (p.sequence, p.id))
        done, result = set(), []

        def add(period, path=()):
            if period in done or period in path:
                return
            depends = (
                period.source_cmpcol_from_id
                | period.source_cmpcol_to_id
                | period.source_sumcol_ids.period_to_sum_id
            ) & periods
            for other in depends.sorted(lambda p: (p.sequence, p.id)):
                add(other, (*path, period))
            done.add(period)
            result.append(period)

        for period in periods:
            add(period)
        return result

    def _instance_records(self):
        records = []
        for instance in self.instances:
            if instance.temporary:
                raise UserError(
                    self.env._(
                        "The report instance %(name)s is temporary and cannot "
                        "be exported.",
                        name=instance.display_name,
                    )
                )
            islug = instance._template_export_slug()
            self._assign(instance, f"instance_{islug}")
            periods = self._sorted_periods(instance)
            sums = []
            for period in periods:
                pslug = _slug(period.with_context(lang="en_US").name)
                self._assign(period, f"instance_{islug}_{pslug}")
                for n, colsum in enumerate(
                    period.source_sumcol_ids.sorted("id"), start=1
                ):
                    self._assign(colsum, f"instance_{islug}_{pslug}_sum_{n}")
                    sums.append(colsum)
            records += [instance, *periods, *sums]
        return records

    def _shared_records(self, records):
        """Styles and date range types used by ``records`` that have no XML
        id, or one in the target module (a module drops records it no longer
        declares, so its own ones must stay in the file)."""
        shared = []
        for record in records:
            for fname, field in self._exported_fields(record):
                if field.type != "many2one" or field.comodel_name not in SHARED_MODELS:
                    continue
                target = record[fname]
                if not target or target in self.ids or target in shared:
                    continue
                xmlid = self._stable_xmlid(target)
                if not xmlid or xmlid.startswith(self.module + "."):
                    shared.append(target)
        for target in shared:
            prefix = SHARED_MODELS[target._name]
            self._assign(target, f"{prefix}_{_slug(target.name)}")
        return shared

    def export(self):
        report = self.report
        records = []
        if self.with_report:
            records += self._report_records(report._template_export_slug())
        records += self._instance_records()
        records = self._shared_records(records) + records
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
        what = "MIS report template" if self.with_report else "MIS report instances of"
        return (
            '<?xml version="1.0" encoding="utf-8" ?>\n'
            f"<!-- {what}: {title} -->\n"
            f"<odoo>\n{body}\n</odoo>\n"
        )
