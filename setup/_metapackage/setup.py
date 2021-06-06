import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-oca-l10n-finland",
    description="Meta package for oca-l10n-finland Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-l10n_fi_banks',
        'odoo14-addon-l10n_fi_business_code',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
