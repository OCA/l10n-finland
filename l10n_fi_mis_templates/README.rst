.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=======================================================
Profit & Loss / Balance sheet MIS templates subsections
=======================================================

Add subsections for MIS templates.
This should make the templates more "familiar" for Finnish users.

Installation
============
\-

Configuration
=============
\-


Usage
=====
\-

Known issues / Roadmap
======================

* The Balance Sheet template references 30 ``l10n_fi`` account tags that were
  removed when Odoo consolidated the Finnish chart of accounts' long/short
  liability tags in 19.0. The module installs and the Profit & Loss and VAT
  reports compute correctly; the affected Balance Sheet KPI lines still need to
  be remapped to their surviving 19.0 tags.

Bug Tracker
===========

Bugs are tracked on `GitLab Issues
<https://gitlab.com/tawasta/odoo/l10n-finland/-/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smash it by providing detailed and welcomed feedback.

Credits
=======

Contributors
------------

* Jarmo Kortetjärvi <jarmo.kortetjarvi@futural.fi>
* Alexander Stadnitski <alexander@goodahead.com>


Maintainer
----------

.. image:: https://futural.fi/templates/tawastrap/images/logo.png
   :alt: Futural Oy
   :target: https://futural.fi/

This module is maintained by Futural Oy
