{
    'name': "OCA's Partner Autocomplete: Finland Open Data",
    'version': "18.0.1.0.0",
    'depends': ['base', 'partner_autocomplete_oca'],
    'author': "Odoo Community Association (OCA) Finland",
    # "website": "https://github.com/OCA/l10n-finland",
    'contributors': [
        'IODO Oy',
    ],
    'category': "Localization",
    'summary': "Enables autocomplete of company information from Finnish Open Data (PRH Avoin Data).",
    'description': "OCA's Partner Autocomplete: Finnish Localization",
    'data': [
        'data/environment_data.xml',
        'data/autocomplete_default_backend.xml',
    ],
    'license': 'LGPL-3',
}