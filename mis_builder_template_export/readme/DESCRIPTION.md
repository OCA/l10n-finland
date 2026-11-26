This module adds an **Export as XML** button to MIS report templates. It
exports the template as an Odoo data XML file that can be added to a module, so
that a report template can be designed in Odoo and then delivered as module
data.

The file contains the report template with its KPIs, sub-KPIs, queries and
subreports, and the styles they use that have no XML id of their own. All
stored fields are exported, including fields added by other modules.
