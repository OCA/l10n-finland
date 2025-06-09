# See LICENSE for licensing information

{
    "name": "Payment References for Sale Refunds",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "summary": "Automatically generate payment references for sale refunds",
    "author": "Avoin.Systems, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-finland",
    # `category`: check
    # https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml # noqa B950
    # for the full list
    "category": "Accounting",
    "depends": ["account"],
    "data": [],
    # `installable`: can the module be installed or not
    "installable": True,
    # `auto_install`: Will be installed automatically as soon as all
    # the dependencies are installed.
    "auto_install": False,
    # `application`: False = module or True = app.
    # Explanation here: http://stackoverflow.com/a/32734931/403053
    "application": False,
    # `external_dependencies`: list of libraries for correct work of module
    # The module cannot be installed if these are missing from the system
    "external_dependencies": {"python": [], "bin": []},
}
