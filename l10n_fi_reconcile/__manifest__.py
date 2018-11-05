# Copyright Avoin.Systems 2018
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "Finnish Reconciliation",
    'summary': "Finnish bank statement reconciliation extensions",
    'version': '11.0.1.0.0',
    'category': 'Invoicing & Payments',
    'website': "https://avoin.systems",
    'author': "Avoin.Systems, Odoo Community Association (OCA)",
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'depends': [
        'l10n_fi_payment_reference',
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
