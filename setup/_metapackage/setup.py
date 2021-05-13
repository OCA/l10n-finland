import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo13-addons-oca-l10n-finland",
    description="Meta package for oca-l10n-finland Odoo addons",
    version=version,
    install_requires=[
        'odoo13-addon-l10n_fi_banks',
        'odoo13-addon-l10n_fi_business_code',
        'odoo13-addon-l10n_fi_edicode',
        'odoo13-addon-l10n_fi_payment_terms',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
