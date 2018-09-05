# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Avoin.Systems.
#    Copyright 2017 Avoin.Systems.
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
# noinspection PyStatementEffect
{
    'name': "Finnish Reconciliation",
    'summary': "Finnish bank statement reconciliation extensions",
    'version': '10.0.0.1.0',
    'category': 'Invoicing & Payments',
    'website': "https://avoin.systems",
    'author': "Avoin.Systems",
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'depends': [
        'l10n_fi',
    ],
    'data': [
        "views/account_view.xml",

    ],
    'demo': [

    ],
    'qweb': [
        'static/src/xml/account_reconciliation.xml',
    ],
}
