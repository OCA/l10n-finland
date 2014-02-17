# -*- coding: utf-8 -*-
##############################################################################
#
#   Copyright (c) 2014 - Vizucom Oy (http://www.vizucom.com)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'FI - Accounting',
    'category': 'Localization/Account Charts',
    'version': '1.0',
    'author': 'Vizucom Oy',
    'website': 'http://www.vizucom.com',
    'depends': ['sale_stock','report_webkit','account'],
    'description': """
Finnish accounts charts
==================================
A Finnish accounts charts localization for OpenERP.
Based on 'Liikekirjurit' account chart (http://www.kirjurituote.fi/) version 7.0.
-------------------------------------------------------------------------------------
""",
    'depends': ['base_iban', 'base_vat', 'account_chart'],
    'data': [
        'data/account.account.type.csv',
        'data/account.account.template.csv',
        'data/account.tax.code.template.csv',
        'data/account.chart.template.csv',
        'data/account.tax.template.csv',
    ],
    'installable': 'True',
    'images': [],
}
