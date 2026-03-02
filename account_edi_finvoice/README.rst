.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==================================
Import/Export invoices as Finvoice
==================================

Import/Export Finvoice 3.0 invoices

For dependencies, see
https://github.com/OCA/l10n-finland/

Configuration
=============
Your company should have following information configured:
- Bank account with bank and BIC
- Business code and VAT
- Edicode and eInvoice operator

Missing information won't cause an error in Finvoice generation,
but will likely cause a rejection when trying to import the Finvoice.

Usage
=====
\-

Known issues / Roadmap
======================
This module would benefit from rewrite.
Lots of logic is coming from 14.0 an outdated/complicated.

Credits
=======

Contributors
------------

* Jarmo Kortetjärvi <jarmo.kortetjarvi@futural.fi>

Maintainer
----------

.. image:: https://futural.fi/web/image/website/1/logo/Futural
   :alt: Futural Oy
   :target: https://futural.fi/

This module is maintained by Futural Oy
