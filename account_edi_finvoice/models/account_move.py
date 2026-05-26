import logging
import re
from datetime import datetime

from odoo import _, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_edi_decoder(self, file_data, new=False):
        if file_data["type"] == "xml":
            if self._is_finvoice(file_data["xml_tree"]):
                self._import_finvoice(file_data["xml_tree"], self)

        return super()._get_edi_decoder(file_data, new=new)

    def _is_finvoice(self, tree):
        return tree.tag == "Finvoice"

    # flake8: noqa: C901
    def _import_finvoice(self, tree, invoice, company_id=False):
        """
        Import finvoice document as Odoo invoice
        """
        edi_format = self.env["account.edi.format"]
        edi_common = self.env["account.edi.common"]

        def _find_value(xpath, element=tree):
            return edi_common._find_value(xpath, element, element.nsmap)

        ns = tree.nsmap

        # Check XML schema to avoid headaches trying to import invalid files
        edi_format._finvoice_check_xml_schema(tree)

        invoice_type = edi_format._get_invoice_type(
            _find_value("./InvoiceDetails/InvoiceTypeCode")
        )
        if invoice.company_id:
            # Force invoice company
            company_id = invoice.company_id.id
        elif not company_id:
            company_id = self.env.company.id

        invoice = invoice.with_company(company_id).with_context(
            default_move_type=invoice_type
        )

        # region SellerPartyDetails
        spd = "SellerPartyDetails"

        business_code = _find_value(f"./{spd}/SellerPartyIdentifier")
        vat = _find_value(f"./{spd}/SellerOrganisationTaxCode")

        # Hacks for insufficient/defective Finvoice XML
        business_code_regex = "^[0-9]{7}[-][0-9]$"

        # Can't find a VAT, use business id instead
        if not vat and business_code and re.search(business_code_regex, business_code):
            # TODO: this is pretty unreliable
            vat = f"FI{re.sub('[^0-9]', '', business_code)}"
        elif vat and re.search(business_code_regex, vat):
            # Business Code is incorrectly given in VAT field (this happens)
            vat = f"FI{re.sub('[^0-9]', '', vat)}"

        invoice.partner_id = self._lookup_partner_by_vat_or_business_code(
            vat,
            business_code,
            company_id=company_id,
        )

        spad = "SellerPostalAddressDetails"

        partner_vals = {
            "company_registry": business_code,
            "street": _find_value(f"./{spd}/{spad}/SellerStreetName"),
            "city": _find_value(f"./{spd}/{spad}/SellerTownName"),
            "zip": _find_value(f"./{spd}/{spad}/SellerPostCodeIdentifier"),
        }

        if invoice.partner_id:
            # Don't overwrite existing partner data with empty Finvoice fields
            partner_write_vals = {k: v for k, v in partner_vals.items() if v}
            if partner_write_vals:
                invoice.partner_id.write(partner_write_vals)
        else:
            invoice.partner_id = self.env["res.partner"].create(
                dict(
                    partner_vals,
                    name=_find_value(f"./{spd}/SellerOrganisationName")
                    or "Unknown Seller",
                    vat=vat,
                    company_type="company",
                )
            )

        # endregion

        # region InvoiceDetails
        ind = "InvoiceDetails"
        # Per Finvoice 3.0, InvoiceNumber is the seller's invoice number;
        # SellerReferenceIdentifier is the seller's own reference for the
        # buyer (e.g. customer number). The former is the right value for
        # invoice.ref.
        invoice_number = _find_value(f"./{ind}/InvoiceNumber")
        seller_ref = _find_value(f"./{ind}/SellerReferenceIdentifier")
        invoice.ref = invoice_number or seller_ref

        invoice_date = _find_value(f"./{ind}/InvoiceDate")
        invoice.invoice_date = datetime.strptime(invoice_date, "%Y%m%d")
        if hasattr(invoice, "agreement_identifier"):
            invoice.agreement_identifier = _find_value(f"./{ind}/AgreementIdentifier")

        invoice.narration = edi_format._find_values_joined(
            f"./{ind}/InvoiceFreeText",
            tree,
        )
        if seller_ref and invoice_number and seller_ref != invoice_number:
            invoice.narration = (invoice.narration or "") + _(
                "\nSeller Reference: %s", seller_ref
            )

        ptd = "PaymentTermsDetails"
        invoice.narration += edi_format._find_values_joined(
            f"./{ind}/{ptd}/PaymentTermsFreeText", tree
        )
        try:
            invoice_date_due = _find_value(f"./{ind}/{ptd}/InvoiceDueDate")
            invoice.invoice_date_due = datetime.strptime(invoice_date_due, "%Y%m%d")
        except (ValueError, TypeError):
            invoice.invoice_date_due = False

        # endregion

        # region VatSpecificationDetails
        # Build a base_amount -> vat_rate map from invoice-level VAT
        # specifications, used as a fallback when an InvoiceRow lacks
        # RowVatRatePercent. The row's RowVatExcludedAmount can then be
        # matched against a VatBaseAmount to recover its VAT rate.
        vat_spec_map = {}
        for vat_spec in tree.xpath(f"./{ind}/VatSpecificationDetails", namespaces=ns):
            base_amount = edi_format._to_float(
                _find_value("./VatBaseAmount", vat_spec)
            )
            vat_rate = edi_format._to_float(_find_value("./VatRatePercent", vat_spec))
            if base_amount:
                vat_spec_map[base_amount] = vat_rate
        # endregion

        # region InvoiceRows
        lines = tree.xpath("./InvoiceRow", namespaces=ns)
        line_number = 0
        line_count = len(lines)

        for line in lines:
            line_number += 1
            _logger.debug(f"Importing line {line_number}/{line_count}")
            line_values = {"move_id": invoice.id}

            if _find_value("./BuyerArticleIdentifier", line):
                default_code = _find_value("./BuyerArticleIdentifier", line)
            else:
                default_code = _find_value("./ArticleIdentifier", line)

            article_name = _find_value("./ArticleName", line)
            article_description = _find_value("./ArticleDescription", line)
            article_free_text = edi_format._find_values_joined("./RowFreeText", line)

            if not article_name:
                article_name = article_description or article_free_text

            # ean_code = _find_value("./EanCode", line)

            # Construct a unit price
            quantity = 1

            # Try to find UnitPriceAmount
            price_unit = False

            if not price_unit or edi_format._to_float(price_unit) == 0:
                # Didn't find UnitPriceAmount. Try RowVatExcludedAmount
                price_subtotal = _find_value("./RowVatExcludedAmount", line)
                price_subtotal = edi_format._to_float(price_subtotal)
                if price_subtotal:
                    price_unit = price_subtotal / quantity

            if not price_unit:
                price_unit = 0

            if article_name:
                _logger.debug(f"Importing '{article_name}'")

            if line_count > 200 and not price_unit:
                # If invoice has more than 200 lines, skip zero lines to
                # prevent a timeout
                # This can be disabled (or limit raised) after line import
                # is optimized
                _logger.debug("Skipping a zero line due to a long invoice")
                continue

            # Try to find a matching product by default code or article name
            # TODO: an option to auto-create missing products
            product_id = False
            if default_code or article_name:
                product_id = self.env["product.product"]._retrieve_product(
                    default_code=default_code,
                    name=article_name,
                )

            if product_id:
                line_values["product_id"] = product_id.id

                accounts = product_id.product_tmpl_id._get_product_accounts()
                if invoice_type == "in_invoice":
                    line_values["account_id"] = accounts["expense"].id
                elif invoice_type == "out_invoice":
                    line_values["account_id"] = accounts["income"].id

            line_name = ""

            # Construct a line name, if product is not found

            if not product_id:
                if article_name:
                    line_name += f"{article_name}"
                if article_description:
                    line_name += f"\n{article_description}"

            if article_name != article_free_text:
                line_name += "\n" + article_free_text

            line_values["name"] = line_name

            line_values["quantity"] = quantity

            unit_code = edi_format._find_attribute(
                "./InvoicedQuantity", line, "QuantityUnitCode"
            )
            if product_id and unit_code:
                uom = self.env["uom.uom"].search(
                    [("name", "ilike", unit_code)], limit=1
                )
                # TODO: an option to auto-create a missing UOM
                if not uom:
                    uom = self.env.ref("uom.product_uom_unit")

                line_values["product_uom_id"] = uom.id

            line_values["price_unit"] = edi_format._to_float(price_unit)

            line_values["discount"] = edi_format._to_float(
                _find_value("./RowDiscountPercent", line)
            )

            # Taxes
            # We are not using _retrieve_tax()
            # as it might return a tax with prices included
            row_vat_rate = _find_value("./RowVatRatePercent", line)
            if row_vat_rate is not None:
                tax_amount = edi_format._to_float(row_vat_rate)
            else:
                # Row didn't carry a VAT rate; try the invoice-level
                # VatSpecificationDetails by matching the row's excluded
                # amount against a VatBaseAmount.
                line_amount = edi_format._to_float(
                    _find_value("./RowVatExcludedAmount", line)
                )
                tax_amount = vat_spec_map.get(line_amount)
            if tax_amount:
                tax_domain = [
                    ("amount", "=", tax_amount),
                    ("type_tax_use", "=", invoice.journal_id.type),
                    # The subtotal will be saved as untaxed amount
                    ("price_include", "=", False),
                    ("company_id", "=", company_id),
                ]

                tax = self.env["account.tax"].search(
                    tax_domain, order="sequence ASC", limit=1
                )

                if not tax:
                    raise ValidationError(_(f"Could not find a tax for {tax_amount}"))

                line_values["tax_ids"] = tax

            invoice.invoice_line_ids.create(line_values)

            # TODO: handle SubInvoiceRows

        # endregion

        # region EpiDetails
        ede = "EpiDetails"
        epid = "EpiPaymentInstructionDetails"

        # Collect candidates in order of authority. EpiRemittanceInfoIdentifier
        # is the official Finvoice payment reference; EpiReference is a
        # message identifier sometimes (incorrectly) used as a payment
        # reference; SellersBuyerIdentifier is also occasionally repurposed.
        ref_candidates = [
            _find_value(f"./{ede}/{epid}/EpiRemittanceInfoIdentifier"),
            _find_value(f"./{ede}/EpiIdentificationDetails/EpiReference"),
            _find_value(f"./{ind}/SellersBuyerIdentifier"),
        ]

        # Prefer the first candidate that validates as a Finnish national
        # reference or RF (ISO 11649) creditor reference; otherwise fall
        # back to the first non-empty candidate so we still record what the
        # sender provided.
        payment_reference = next(
            (r for r in ref_candidates if r and self._is_valid_payment_reference(r)),
            None,
        )
        if not payment_reference:
            payment_reference = next((r for r in ref_candidates if r), None)

        invoice.payment_reference = payment_reference

        epd = "EpiPartyDetails"

        if not invoice.partner_id:
            # Partner is missing, and needs to be created
            partner_vals.update(
                {
                    "name": _find_value(f"./{spd}/SellerOrganisationName"),
                }
            )
            _logger.debug(f"Creating a partner for with values: {partner_vals}")
            partner = self.env["res.partner"].create(partner_vals)
            invoice.partner_id = partner

        partner_bank_id = edi_format._retrieve_bank_account(
            _find_value(f"./{ede}/{epd}/EpiBeneficiaryPartyDetails/EpiAccountID"),
            partner_id=invoice.partner_id.id,
            bic=_find_value(f"./{ede}/{epd}/EpiBfiPartyDetails/EpiBfiIdentifier"),
            company_id=company_id,
        )

        if partner_bank_id:
            invoice.partner_bank_id = partner_bank_id
        # endregion

        return invoice

    def _lookup_partner_by_vat_or_business_code(self, vat, business_code, company_id):
        Partner = self.env["res.partner"]
        domain = []

        if vat:
            domain.append(("vat", "=", vat))
        if business_code:
            domain.append(("company_registry", "=", business_code))

        if not domain:
            return Partner

        partners = Partner.search(
            ["|"] * (len(domain) - 1) + domain + [("type", "=", "contact")],
            limit=1,
        )

        return partners or Partner

    @staticmethod
    def _is_valid_finnish_reference(ref):
        """Validate a Finnish national payment reference (4-20 digits, 7-3-1 check)."""
        if not ref.isdigit() or not (4 <= len(ref) <= 20):
            return False
        base = ref[:-1]
        check_digit = ref[-1]
        total = sum(
            (7, 3, 1)[idx % 3] * int(val) for idx, val in enumerate(base[::-1])
        )
        return check_digit == str((10 - (total % 10)) % 10)

    @staticmethod
    def _is_valid_rf_reference(ref):
        """Validate an RF creditor reference (ISO 11649, mod 97 check)."""
        ref_upper = ref.upper()
        if not re.match(r"^RF\d{2}\d{4,20}$", ref_upper):
            return False
        rearranged = ref_upper[4:] + ref_upper[:4]
        numeric_str = "".join(
            str(ord(c) - 55) if c.isalpha() else c for c in rearranged
        )
        return int(numeric_str) % 97 == 1

    def _is_valid_payment_reference(self, ref):
        """Check if ref is a valid Finnish national or RF payment reference."""
        return self._is_valid_finnish_reference(ref) or self._is_valid_rf_reference(ref)
