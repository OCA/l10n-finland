import logging
import re
from datetime import datetime

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    finvoice_expected_total = fields.Monetary(
        string="Finvoice Expected Total",
        currency_field="currency_id",
        copy=False,
    )
    finvoice_expected_total_incl = fields.Monetary(
        string="Finvoice Expected Total (incl. VAT)",
        currency_field="currency_id",
        copy=False,
    )
    finvoice_total_warning = fields.Char(
        compute="_compute_finvoice_total_warning",
    )

    @api.depends(
        "finvoice_expected_total",
        "finvoice_expected_total_incl",
        "amount_untaxed",
        "amount_total",
    )
    def _compute_finvoice_total_warning(self):
        for move in self:
            expected_excl = move.finvoice_expected_total
            expected_incl = move.finvoice_expected_total_incl
            if not expected_excl and not expected_incl:
                move.finvoice_total_warning = False
                continue
            currency = move.currency_id
            untaxed = move.amount_untaxed
            total = move.amount_total
            # The warning is suppressed as long as any of the three header
            # figures can be reconciled with what Odoo computed. Senders vary:
            # Ilmarinen puts a pre-adjustment gross in VatExcludedAmount and
            # the real remaining total in VatIncludedAmount, and DNA rounds
            # per-invoice VAT differently from Odoo's per-line rounding so
            # amount_untaxed drifts by a cent even though amount_total lines
            # up with VatIncludedAmount exactly.
            matches = (
                (expected_excl and currency.compare_amounts(expected_excl, untaxed) == 0)
                or (expected_incl and currency.compare_amounts(expected_incl, untaxed) == 0)
                or (expected_incl and currency.compare_amounts(expected_incl, total) == 0)
            )
            if matches:
                move.finvoice_total_warning = False
                continue
            expected = expected_excl or expected_incl
            diff = expected - untaxed
            move.finvoice_total_warning = _(
                "The Finvoice total is %(expected)s %(currency)s "
                "but invoice lines total %(actual)s %(currency)s "
                "(difference: %(diff)s %(currency)s). "
                "Check for missing charges (e.g. shipping, handling).",
                expected=formatLang(move.env, expected, currency_obj=currency),
                actual=formatLang(move.env, untaxed, currency_obj=currency),
                diff=formatLang(move.env, diff, currency_obj=currency),
                currency=currency.name,
            )

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
            vat = "FI%s" % re.sub("[^0-9]", "", business_code)
        elif vat and re.search(business_code_regex, vat):
            # Business Code is incorrectly given in VAT field (this happens)
            vat = "FI%s" % re.sub("[^0-9]", "", vat)

        spad = "SellerPostalAddressDetails"

        # Try Finnish-specific partner lookup first (by VAT or business code)
        partner = self._lookup_partner_by_vat_or_business_code(
            vat, business_code, company_id=company_id
        )
        if partner:
            invoice.partner_id = partner
        else:
            # Fall back to standard Odoo partner matching
            edi_common._import_retrieve_and_fill_partner(
                invoice,
                name=_find_value(f"./{spd}/SellerOrganisationName"),
                phone=_find_value(f"./{spd}/SellerPhoneNumberIdentifier"),
                mail=_find_value(f"./{spd}/SellerEmailaddressIdentifier"),
                vat=vat,
            )

        partner_vals = {
            "company_registry": business_code,
            "street": _find_value(f"./{spd}/{spad}/SellerStreetName"),
            "city": _find_value(f"./{spd}/{spad}/SellerTownName"),
            "zip": _find_value(f"./{spd}/{spad}/SellerPostCodeIdentifier"),
        }

        if invoice.partner_id:
            invoice.partner_id.write(partner_vals)
        else:
            invoice.partner_id = self.env["res.partner"].create(
                dict(
                    partner_vals,
                    name=_find_value(f"./{spd}/SellerOrganisationName") or "Unknown Seller",
                    vat=vat,
                    company_type="company",
                )
            )
        # endregion

        # region InvoiceDetails
        ind = "InvoiceDetails"

        expected_total = edi_format._to_float(
            _find_value(f"./{ind}/InvoiceTotalVatExcludedAmount")
        )
        if expected_total:
            invoice.finvoice_expected_total = expected_total

        expected_total_incl = edi_format._to_float(
            _find_value(f"./{ind}/InvoiceTotalVatIncludedAmount")
        )
        if expected_total_incl:
            invoice.finvoice_expected_total_incl = expected_total_incl

        invoice.ref = _find_value(f"./{ind}/SellerReferenceIdentifier") or _find_value(
            f"./{ind}/InvoiceNumber"
        )

        invoice_date = _find_value(f"./{ind}/InvoiceDate")
        invoice.invoice_date = datetime.strptime(invoice_date, "%Y%m%d")
        if hasattr(invoice, "agreement_identifier"):
            invoice.agreement_identifier = _find_value(f"./{ind}/AgreementIdentifier")

        invoice.narration = edi_format._find_values_joined(
            f"./{ind}/InvoiceFreeText",
            tree,
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

        # region VatSpecificationDetails - build a map of base_amount -> vat_rate
        # Used as fallback when individual rows lack RowVatRatePercent
        vat_specs = tree.xpath(
            f"./{ind}/VatSpecificationDetails", namespaces=ns
        )
        vat_spec_map = {}  # base_amount -> vat_rate
        for vat_spec in vat_specs:
            base_amount = edi_format._to_float(
                _find_value("./VatBaseAmount", vat_spec)
            )
            vat_rate = edi_format._to_float(
                _find_value("./VatRatePercent", vat_spec)
            )
            if base_amount:
                vat_spec_map[base_amount] = vat_rate
        # endregion

        # region InvoiceRows
        lines = tree.xpath("./InvoiceRow", namespaces=ns)
        line_number = 0
        line_count = len(lines)

        # Pre-pass: decide whether SubInvoiceRows should be imported as real
        # lines or ignored as decoration. Some senders (Ilmarinen) use a
        # SubInvoiceRow for a real prior-payment credit; others (DNA) use
        # SubInvoiceRows as section headers and summary totals that duplicate
        # amounts already present in regular InvoiceRow elements. We decide by
        # reconciliation: if the sum of regular row amounts already matches
        # the header's VAT-included total minus the header VAT amount, sub
        # rows are decorative and must be skipped to avoid double-counting.
        header_total_incl = edi_format._to_float(
            _find_value(f"./{ind}/InvoiceTotalVatIncludedAmount")
        )
        header_total_vat = edi_format._to_float(
            _find_value(f"./{ind}/InvoiceTotalVatAmount")
        ) or 0.0
        real_row_sum = 0.0
        for candidate in lines:
            row_excl = edi_format._to_float(
                _find_value("./RowVatExcludedAmount", candidate)
            )
            if not row_excl:
                row_qty = (
                    edi_format._to_float(
                        _find_value("./InvoicedQuantity", candidate)
                    )
                    or 1
                )
                row_unit = edi_format._to_float(
                    _find_value("./UnitPriceAmount", candidate)
                )
                if row_unit:
                    row_excl = row_unit * row_qty
            if row_excl:
                real_row_sum += row_excl
        import_sub_rows = True
        if header_total_incl:
            target_excl = header_total_incl - header_total_vat
            if abs(real_row_sum - target_excl) < 0.01:
                import_sub_rows = False

        def _find_tax_by_rate(tax_amount):
            if tax_amount is None:
                return None
            tax = self.env["account.tax"].search(
                [
                    ("amount", "=", tax_amount),
                    ("type_tax_use", "=", invoice.journal_id.type),
                    # The subtotal will be saved as untaxed amount
                    ("price_include", "=", False),
                    ("company_id", "=", company_id),
                ],
                order="sequence ASC",
                limit=1,
            )
            if not tax:
                raise ValidationError(_(f"Could not find a tax for {tax_amount}"))
            return tax

        for line in lines:
            line_number += 1
            _logger.debug("Importing line {}/{}".format(line_number, line_count))
            line_values = {"move_id": invoice.id}

            raw_sub_rows = line.xpath("./SubInvoiceRow", namespaces=ns)
            sub_rows = raw_sub_rows if import_sub_rows else []

            if _find_value("./BuyerArticleIdentifier", line):
                default_code = _find_value("./BuyerArticleIdentifier", line)
            else:
                default_code = _find_value("./ArticleIdentifier", line)
            article_name = _find_value("./ArticleName", line)
            article_description = _find_value("./ArticleDescription", line)
            article_free_text = edi_format._find_values_joined("./RowFreeText", line)
            ean_code = _find_value("./EanCode", line)

            if not article_name:
                article_name = article_description or article_free_text

            # Construct a unit price
            quantity = (
                edi_format._to_float(_find_value("./InvoicedQuantity", line)) or 1
            )
            # Try to find UnitPriceAmount
            price_unit = _find_value("./UnitPriceAmount", line)

            if not price_unit or edi_format._to_float(price_unit) == 0:
                # Didn't find UnitPriceAmount. Try RowVatExcludedAmount
                price_subtotal = _find_value("./RowVatExcludedAmount", line)
                price_subtotal = edi_format._to_float(price_subtotal)
                if price_subtotal:
                    price_unit = price_subtotal / quantity

            if not price_unit:
                price_unit = 0

            # Reconcile with the authoritative row total when present. Some
            # senders price per N pieces without flagging it (WAGO ships
            # per-100 prices but fills InvoicedQuantity with the piece count,
            # so qty × unit over-counts 100x); others drift by per-row VAT
            # rounding (Kärkkäinen, ±0.02 €); and others hit Odoo's 2-decimal
            # price_unit precision when the implied unit price has more
            # decimals than cents (Kiinteistö: 127.49 / 40 = 3.18725 → stored
            # as 3.19 → subtotal 127.60 instead of 127.49). In all cases
            # RowVatExcludedAmount is the authoritative line total in
            # Finvoice. When the naive qty × round(unit, 2) × (1 - discount)
            # wouldn't produce it, collapse to 1 × row_excl so Odoo's
            # price_unit precision can't erase cents, and keep the original
            # pricing info in the name. Discount must be factored in (Mage
            # Guys 10%, Onninen 53%) or the collapse would trust a row_excl
            # that ALREADY has the discount applied and then Odoo would apply
            # it a second time.
            row_vat_excluded_raw = _find_value("./RowVatExcludedAmount", line)
            discount = edi_format._to_float(
                _find_value("./RowDiscountPercent", line)
            ) or 0
            reconciliation_note = ""
            if row_vat_excluded_raw:
                row_vat_excluded = edi_format._to_float(row_vat_excluded_raw)
                current_price_unit = edi_format._to_float(price_unit) or 0
                discount_factor = 1 - discount / 100
                stored_subtotal = round(
                    round(current_price_unit, 2) * quantity * discount_factor, 2
                )
                if round(stored_subtotal - row_vat_excluded, 2) != 0:
                    original_desc = (
                        f"({quantity:g} × {current_price_unit:g} EUR"
                        + (f" - {discount:g}%)" if discount else ")")
                    )
                    reconciliation_note = original_desc
                    quantity = 1
                    price_unit = row_vat_excluded
                    discount = 0

            if article_name:
                _logger.debug("Importing '{}'".format(article_name))

            if line_count > 200 and not price_unit:
                # If invoice has more than 200 lines, skip zero lines to prevent a timeout
                # This can be disabled (or limit raised) after line import is optimized
                _logger.debug("Skipping a zero line due to a long invoice")
                continue

            # Try to find a product by default code, name or barcode
            product_id = edi_format._retrieve_product(
                default_code=default_code,
                name=article_name,
                barcode=ean_code,
            )
            # TODO: An option to auto-create products

            if product_id:
                line_values["product_id"] = product_id.id

            if product_id:
                accounts = product_id.product_tmpl_id._get_product_accounts()

                if invoice_type == "in_invoice":
                    line_values["account_id"] = accounts["expense"].id
                elif invoice_type == "out_invoice":
                    line_values["account_id"] = accounts["income"].id

            # Construct a line name, if product is not found
            line_name = ""
            if not product_id:
                if article_name:
                    line_name += f"{article_name}"
                if article_description:
                    line_name += f"\n{article_description}"

            if article_name != article_free_text:
                line_name += "\n" + article_free_text
            if reconciliation_note:
                line_name = (line_name + "\n" + reconciliation_note).lstrip("\n")
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

            line_values["discount"] = discount

            # Taxes
            # We are not using _retrieve_tax()
            # as it might return a tax with prices included
            row_vat_rate = _find_value("./RowVatRatePercent", line)
            if row_vat_rate is not None:
                tax_amount = edi_format._to_float(row_vat_rate)
            else:
                # RowVatRatePercent missing - try to determine from
                # invoice-level VatSpecificationDetails by matching base amount
                line_amount = edi_format._to_float(
                    _find_value("./RowVatExcludedAmount", line)
                )
                tax_amount = vat_spec_map.get(line_amount)
            tax = _find_tax_by_rate(tax_amount)
            if tax:
                line_values["tax_ids"] = tax

            # A parent row is a pure container when it has no article or
            # amount of its own but does have SubInvoiceRow children. Some
            # senders (DNA) use these as decorative section headers whose
            # sub rows the pre-pass has decided not to import; others
            # (Ilmarinen) use them to carry a real adjustment in the sub
            # row. In both cases the parent line itself has nothing to
            # contribute, so skip creating it.
            parent_is_container = (
                not article_name and not default_code and bool(raw_sub_rows)
            )
            if not parent_is_container:
                invoice.invoice_line_ids.create(line_values)

            for sub_row in sub_rows:
                sub_name = _find_value("./SubArticleName", sub_row)
                sub_description = _find_value("./SubArticleDescription", sub_row)
                sub_free_text = edi_format._find_values_joined(
                    "./SubRowFreeText", sub_row
                )
                if not sub_name:
                    sub_name = sub_description or sub_free_text

                sub_qty = (
                    edi_format._to_float(_find_value("./SubInvoicedQuantity", sub_row))
                    or 1
                )

                sub_price = edi_format._to_float(
                    _find_value("./SubUnitPriceAmount", sub_row)
                )
                if not sub_price:
                    sub_excl = edi_format._to_float(
                        _find_value("./SubRowVatExcludedAmount", sub_row)
                    )
                    if sub_excl:
                        sub_price = sub_excl / sub_qty
                if not sub_price:
                    sub_total = edi_format._to_float(
                        _find_value("./SubRowAmount", sub_row)
                    )
                    if sub_total:
                        sub_price = sub_total / sub_qty
                if not sub_price:
                    continue

                sub_vat_rate = _find_value("./SubRowVatRatePercent", sub_row)
                if sub_vat_rate is not None:
                    sub_tax_amount = edi_format._to_float(sub_vat_rate)
                elif row_vat_rate is not None:
                    sub_tax_amount = edi_format._to_float(row_vat_rate)
                else:
                    sub_base = edi_format._to_float(
                        _find_value("./SubRowVatExcludedAmount", sub_row)
                    )
                    sub_tax_amount = vat_spec_map.get(sub_base)

                sub_line_name = ""
                if sub_name:
                    sub_line_name += sub_name
                if sub_description and sub_description != sub_name:
                    sub_line_name += f"\n{sub_description}"
                if sub_free_text and sub_free_text != sub_name:
                    sub_line_name += f"\n{sub_free_text}"

                sub_values = {
                    "move_id": invoice.id,
                    "name": sub_line_name,
                    "quantity": sub_qty,
                    "price_unit": sub_price,
                }
                sub_tax = _find_tax_by_rate(sub_tax_amount)
                if sub_tax:
                    sub_values["tax_ids"] = sub_tax
                invoice.invoice_line_ids.create(sub_values)

        # endregion

        # region EpiDetails
        ede = "EpiDetails"
        epid = "EpiPaymentInstructionDetails"

        # Collect reference candidates (authoritative source first)
        ref_candidates = [
            _find_value(f"./{ede}/{epid}/EpiRemittanceInfoIdentifier"),
            _find_value(f"./{ede}/EpiIdentificationDetails/EpiReference"),
            _find_value(f"./{ind}/SellersBuyerIdentifier"),
        ]

        # Pick the first valid Finnish/RF payment reference
        payment_reference = None
        for ref in ref_candidates:
            if ref and self._is_valid_payment_reference(ref):
                payment_reference = ref
                break

        # If no valid reference found, use the first non-empty candidate as-is
        if not payment_reference:
            payment_reference = next((r for r in ref_candidates if r), None)

        invoice.payment_reference = payment_reference

        epd = "EpiPartyDetails"

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

    @staticmethod
    def _is_valid_finnish_reference(ref):
        """Validate a Finnish national payment reference (4-20 digits, 7-3-1 check)."""
        if not ref.isdigit() or not (4 <= len(ref) <= 20):
            return False
        base = ref[:-1]
        check_digit = ref[-1]
        total = sum(
            (7, 3, 1)[idx % 3] * int(val)
            for idx, val in enumerate(base[::-1])
        )
        return check_digit == str((10 - (total % 10)) % 10)

    @staticmethod
    def _is_valid_rf_reference(ref):
        """Validate an RF creditor reference (ISO 11649, mod 97 check)."""
        ref_upper = ref.upper()
        if not re.match(r'^RF\d{2}\d{4,20}$', ref_upper):
            return False
        rearranged = ref_upper[4:] + ref_upper[:4]
        numeric_str = ''.join(
            str(ord(c) - 55) if c.isalpha() else c for c in rearranged
        )
        return int(numeric_str) % 97 == 1

    def _is_valid_payment_reference(self, ref):
        """Check if ref is a valid Finnish national or RF payment reference."""
        return self._is_valid_finnish_reference(ref) or self._is_valid_rf_reference(ref)

    def _lookup_partner_by_vat_or_business_code(self, vat, business_code, company_id=False):
        """Look up partner by VAT number or Finnish business code (Y-tunnus)."""
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
