##############################################################################
#
#    Author: Oy Tawasta OS Technologies Ltd.
#    Copyright 2017 Oy Tawasta OS Technologies Ltd. (http://www.tawasta.fi)
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
{
    "name": "Partner EDI code",
    "summary": "Adds EDI code field and operators",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "website": "https://github.com/OCA/l10n-finland",
    "author": ("Tawasta" ", Odoo Community Association (OCA)" ", Avoin.Systems"),
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "external_dependencies": {"python": [], "bin": []},
    "depends": ["account"],
    "data": [
        "data/res_partner_operator_einvoice.xml",
        "security/ir.model.access.csv",
        "views/menuitems.xml",
        "views/res_partner_view.xml",
        "views/res_company_view.xml",
        "views/res_config_settings_view.xml",
        "views/res_partner_operator_einvoice_view.xml",
    ],
    "demo": [],
    "qweb": [],
}
