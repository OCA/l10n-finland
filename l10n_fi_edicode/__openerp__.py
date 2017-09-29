# -*- coding: utf-8 -*-
##############################################################################
#
#   Copyright (c) 2014- Vizucom Oy (http://www.vizucom.com)
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
    'name': 'Partner Edicode Fields',
    'category': 'CRM',
    'version': '8.0.0.3.2',
    'author': 'Vizucom Oy',
    'website': 'http://www.vizucom.com',
    'depends': [],
    'data': [
        'view/res_partner.xml',

        'data/res_partner_operator_einvoice.xml',

        'security/ir.model.access.csv',
    ],
}
