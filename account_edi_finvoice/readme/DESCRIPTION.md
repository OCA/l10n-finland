Import/Export invoices as Finvoice 3.0 XML.

Provides:

- Outbound: an EDI format `finvoice_3_0` that renders posted invoices to a Finvoice 3.0 XML attachment, validated against the official XSD.
- Inbound: an importer that turns a Finvoice 3.0 XML into a draft `account.move`, mapping seller, partner bank, payment reference, lines, taxes and unit-of-measure. Robust against the most common quirks observed from Finnish senders: missing `RowVatRatePercent` on lines, per-N pricing, decorative `SubInvoiceRow` elements, FedEx-style VAT-included pricing, and partner addresses that drop fields.

A warning banner is shown on imported invoices when the totals declared in the source XML don't reconcile with what Odoo computed from the lines.
