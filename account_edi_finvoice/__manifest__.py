##############################################################################
#
#    Author: Futural Oy
#    Copyright 2022 Futural Oy (https://futural.fi)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see http://www.gnu.org/licenses/lgpl.html
#
##############################################################################

{
    "name": "Import/Export invoices as Finvoice",
    "summary": "Import/Export Finvoice 3.0 invoices",
    "version": "18.0.1.0.5",
    "category": "Accounting",
    "website": "https://github.com/OCA/l10n-finland",
    "author": "Odoo Community Association (OCA), Futural",
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "external_dependencies": {"python": [], "bin": []},
    "depends": [
        "account",
        "account_edi",
        "account_edi_ubl_cii",
        "l10n_fi_edicode",
    ],
    "data": [
        "data/finvoice_template.xml",
        "data/account_edi_data.xml",
    ],
    "demo": [],
}
