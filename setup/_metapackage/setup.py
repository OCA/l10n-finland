import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo11-addons-oca-l10n-finland",
    description="Meta package for oca-l10n-finland Odoo addons",
    version=version,
    install_requires=[
        'odoo11-addon-l10n_fi_banks',
        'odoo11-addon-l10n_fi_business_code',
        'odoo11-addon-l10n_fi_business_code_validate',
        'odoo11-addon-l10n_fi_payment_reference',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
