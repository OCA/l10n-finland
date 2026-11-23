##############################################################################
#
#    Author: Futural Oy
#    Copyright 2022 Futural Oy (https://futural.fi)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see http://www.gnu.org/licenses/agpl.html
#
##############################################################################
{
    "name": "Profit & Loss / Balance sheet MIS templates subsections",
    "summary": "Add subsections for MIS templates",
    "version": "19.0.1.0.0",
    "category": "Localization",
    "website": "https://github.com/OCA/l10n-finland",
    "author": "Odoo Community Association (OCA), Futural",
    "maintainer": "Odoo Community Association (OCA), Futural",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["l10n_fi", "mis_template_financial_report"],
    "data": [
        "data/mis_report_kpi_bs.xml",
        "data/mis_report_kpi_pl.xml",
        "data/mis_report_kpi_vat.xml",
    ],
    "external_dependencies": {"python": [], "bin": []},
    "assets": {},
}
