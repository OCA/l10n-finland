# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Jarmo Kortetjärvi
#    Copyright 2015 Oy Tawasta OS Technologies Ltd.
#    Copyright 2015 Vizucom Oy
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Finland - Accounting (Liikekirjuri)',
    'category': 'Localization/Account Charts',
    'version': '8.0.1.2.0',
    'author': '''
Vizucom Oy,
Oy Tawasta OS Technologies Ltd.,
Odoo Community Association (OCA)
''',
    'license': 'AGPL-3',
    'website': 'https://github.com/OCA/l10n-finland',
    'depends': [
        'account',
        'account_chart',
        'base_vat',
        'base_iban'
    ],
    'data': [
        'data/account.account.type.csv',
        'data/account.account.template.csv',
        'data/account.tax.code.template.csv',
        'data/account.chart.template.csv',
        'data/account.tax.template.csv',
    ],
    'installable': 'True',
}
