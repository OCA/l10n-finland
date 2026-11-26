# Copyright 2026 Cetmix Nordic Ltd
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "MIS Builder Template Export",
    "summary": "Export a MIS report template as Odoo data XML",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Cetmix Nordic Ltd, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-finland",
    "category": "Reporting",
    "depends": ["account", "mis_builder"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/mis_report_template_export_views.xml",
        "views/mis_report_views.xml",
    ],
    "installable": True,
}
