# Copyright Avoin.Systems 2018
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Finnish Sales Invoice Payment Reference",
    "summary": "Generate a valid invoice payment reference for sales invoices",
    "version": "11.0.1.0.0",
    "category": "Localization",
    "website": "https://github.com/OCA/l10n-finland",
    "author": "Avoin.Systems, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": [
        "account",
    ],
    "installable": True,
    "data": [
        "views/account_invoice.xml",
        "views/res_config.xml",
    ]
}
