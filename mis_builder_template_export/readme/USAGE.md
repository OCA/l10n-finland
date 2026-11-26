1. Open *Invoicing > Configuration > MIS Reporting > MIS Report Templates* and
   open a report template, or open a report instance in *Invoicing >
   Reporting > MIS Reporting > MIS Reports*.
2. Click **Export as XML**. From a report instance, the instance is already
   chosen in **Report Instances**.
3. Fill in:
   - **Module**: the technical name of the module the file is for. Records
     that already have an XML id in this module keep it; the others get ids
     derived from the report name, for example `report_balance_sheet` and
     `kpi_balance_sheet_assets`.
   - **Report Instances**: report instances of the template to export with
     their periods. Leave empty to export the template only.
   - **Export the Report Template**: shown when instances are exported. Turn
     it off to export the instances only; they then refer to the template by
     its XML id. It is off by default when the template belongs to another
     module, for example a template delivered by a localization module.
   - **Language**: the language of names and descriptions in the file.
   - **Link Records to the Module**: gives the exported records the XML ids of
     the file. Keep it on when the module will be installed or updated in the
     same database: the module then updates these records instead of creating
     a second copy of the report template. Without it, installing the file in
     the same database fails if the template uses its own styles, because
     style names must be unique.
4. Click **Export** and save the downloaded file in the module's `data`
   folder, then add it to the `data` list of the manifest.

After linking, the module owns the records: changes made in Odoo are
overwritten by the next module update unless they are exported again. Export
the template again after each change made in Odoo.

A reference to a record that has no XML id and is not part of the export (for
example a subreport made in Odoo, or a budget used by a period) cannot be
exported. Export or link the referenced record first.

Temporary report instances, the previews opened from a report template, cannot
be exported.
