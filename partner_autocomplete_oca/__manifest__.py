{
    'name': "OCA's Partner Autocomplete",
    'version': "18.0.1.0.0",
    'depends': ['base', 'web', 'connector'],
    'author': "Odoo Community Association (OCA) Finland",
    # "website": "https://github.com/OCA/l10n-finland",
    'contributors': [
        'IODO Oy',
    ],
    'category': "Tools",
    'summary': "Autocomplete partner companies. Needs localization modules to work.",
    'description': "Note on Compatibility: The Odoo official Partner Autocomplete module (partner_autocomplete) will override the functionality of this module if installed.",
    'data': [
        'security/ir.model.access.csv',
        'views/partner_views.xml',
        'views/autocomplete_backend_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'partner_autocomplete_oca/static/src/js/form_controller_patch.js',
            'partner_autocomplete_oca/static/src/js/autocomplete.js',
            'partner_autocomplete_oca/static/src/xml/autocomplete_templates.xml',
        ],
    },
    'pre_init_hook': 'before_installation',
    'license': 'LGPL-3',
}