.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==============
APIX Connector
==============

APIX EDI connector for receiving and sending eInvoices via APIX

Features
========
- Setup APIX account
- Use any invoice template for outgoing invoices
- Send sale invoices (as einvoice or via printing service)
- Send sale credit notes (refunds)
- Receive purchase invoices
- Receive purchase credit notes (refunds)


Configuration
=============
- Set up a connector backend from Connectors->APIX->Backends
- Start sending/receiving invoices

Usage
=====
- If invoice transmit method is einvoice or printing service, a button for sending will appear
- A scheduled job will fetch purchase invoices periodically

Known issues / Roadmap
======================
- markReceived is not working: purchase invoices are being unnecessarily re-fetches

Credits
=======

Contributors
------------

* Jarmo Kortetjärvi <jarmo.kortetjarvi@futural.fi>

Maintainer
----------

.. image:: https://futural.fi/logo.png?company=1
   :alt: Futural Oy
   :target: https://futural.fi/

This module is maintained by Futural Oy
