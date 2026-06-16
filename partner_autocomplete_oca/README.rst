================================
Partner Autocomplete OCA Finland
================================

Autocomplete partner companies using external APIs.

Installation
============

To install this module you need to

1. Install the base Partner Autocomplete OCA module (:code:`partner_autocomplete_oca`)
2. Install the specific country localization module/modules (e.g. :code:`l10n_fi_partner_autocomplete_oca_opendata`)

Depencies
=========

:Mandatory modules: base, web, connector
:Voluntary modules: Localization modules for specific countries (:code:`l10n_x_partner_autocomplete_oca_x`)

Odoo Configuration
===================

Requires one or more backend configurations to work.

.. note::
    If you install a specific country's 'Free: Open Data' localization module (e.g.,
    :code:`l10n_fi_partner_autocomplete_oca_opendata`), the necessary default backend 
    configuration for that country may be created automatically upon installation.
    However, paid environments or custom setups require manual configuration.

Manual configuration after installation

1. Go to **Connectors** -> **Autocomplete** -> **Backends**
2. Create a new backend configuration:
    * **Default Country:** The country this backend serves (e.g. Finland).
    * **Environment Type:** Select between 'Free: Open Data' or 'Paid: IODO\'s Data'.
    * **API Key:** Set the required key if you chose the paid environment.
    * **Active:** Sets the backend as the default fallback. Only one backend can be set as the active default at any time.

Note on Compatibility: The Odoo official Partner Autocomplete module (partner_autocomplete) will override the functionality of this module if installed.

Usage
================

1. When creating a new **Company** record (res.partner), type at least 3 characters into the **Name** field
2. A list of matching companies will appear below the field
3. Click on a company name to automatically populate fields

Features
========

- Free localization version offers limited information such as name, address, VAT/Business ID and website if they are found from Open Data API
- Paid localization version offers in addition critical financial data such as e-invoicing addresses. This ensures automated, error-free invoicing and eliminates the need for manual data entry in core financial processes.

Source/Repository Link
======================

The source code is found at `GitHub <https://github.com/OCA/l10n-finland>`_.

Credits
=======

Contributors
------------

* IODO Oy

Maintainer
----------

.. image:: https://www.iodo.fi/web/image/website/1/logo/IODO?unique=5574ac3
   :alt: IODO Oy
   :target: https://iodo.fi/

This module is maintained by IODO Oy