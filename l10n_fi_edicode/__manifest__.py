# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Vizucom Oy, Oy Tawasta OS Technologies Ltd.
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
##############################################################################

{
    'name': 'Finnish EDI code',
    'summary': 'Finnish Electronic Data Interchange code',
    'version': '10.0.0.3.5',
    'category': 'CRM',
    'website': 'https://github.com/Tawasta/l10n-finland/',
    'author': 'Vizucom Oy, Oy Tawasta Technologies Ltd.',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'external_dependencies': {
        'python': [],
        'bin': [],
    },
    'depends': [
        'crm',
    ],
    'data': [
        'view/res_partner.xml',
        'data/res_partner_operator_einvoice.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
}
