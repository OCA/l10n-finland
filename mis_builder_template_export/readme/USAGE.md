1. Open *Invoicing > Configuration > MIS Reporting > MIS Report Templates* and
   open a report template.
2. Click **Export as XML**.
3. Fill in:
   - **Module**: the technical name of the module the file is for. Records
     that already have an XML id in this module keep it; the others get ids
     derived from the report name, for example `report_balance_sheet` and
     `kpi_balance_sheet_assets`.
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
example a subreport made in Odoo) cannot be exported. Export or link the
referenced report first.
