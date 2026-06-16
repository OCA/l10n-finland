# -*- coding: utf-8 -*-
{
    'name': 'MIS Report Partner Details',
    'version': '18.0.1.0.0',
    'category': 'Reporting',
    'summary': 'Add partner detail expansion to MIS Reports',
    'description': """
        This module extends MIS Reports to allow automatic expansion
        of account balances by partner.
        
        Features:
        - Adds "Display by Partner" checkbox in KPI configuration
        - Automatically shows balance for each partner
        - Works with receivable and payable account types
    """,
    'depends': [
        'mis_builder',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/mis_report_kpi_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mis_report_partner_details/static/src/css/mis_report_partner_details.css',
            'mis_report_partner_details/static/src/js/mis_report_partner_details.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
