##############################################################################
#
#    Author: Futural Oy
#    Copyright 2017 Futural Oy (https://futural.fi)
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
    "name": "APIX Connector",
    "summary": "APIX EDI connector for receiving and sending eInvoices",
    "version": "19.0.1.0.0",
    "category": "Connector",
    "website": "https://github.com/OCA/l10n-finland",
    "author": "Odoo Community Association (OCA), Futural",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "external_dependencies": {
        "python": [],
        "bin": [],
    },
    "depends": [
        "account_edi_finvoice",
        "account_invoice_transmit_method",
        "connector",
        "l10n_fi_edicode",
    ],
    "post_init_hook": "init_apix_data",
    "data": [
        "data/ir_cron.xml",
        "security/ir.model.access.csv",
        "views/account_invoice_form.xml",
        "views/apix_backend_form.xml",
        "views/apix_backend_menu.xml",
    ],
    "demo": [],
}
