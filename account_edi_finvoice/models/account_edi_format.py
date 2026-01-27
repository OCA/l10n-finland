import logging
import re
import textwrap
from datetime import datetime

from lxml import etree

from odoo import _, api, models, tools
from odoo.exceptions import UserError
from odoo.tools import float_repr, html2plaintext

_logger = logging.getLogger(__name__)

INVOICE_TYPES = {
    "REQ01": "TARJOUSPYYNTÖ",
    "QUO01": "TARJOUS",
    "ORD01": "TILAUS",
    "ORC01": "TILAUSVAHVISTUS",
    "DEV01": "TOIMITUSILMOITUS",
    "INV01": "LASKU",
    "INV02": "HYVITYSLASKU",
    "INV03": "KORKOLASKU",
    "INV04": "SISÄINEN LASKU",
    "INV05": "PERINTÄLASKU",
    "INV06": "PROFORMALASKU",
    "INV07": "ITSELASKUTUS",
    "INV08": "HUOMAUTUSLASKU",
    "INV09": "SUORAMAKSU",
    "TES01": "TESTILASKU",
    "PRI01": "HINNASTO",
    "INF01": "TIEDOTE",
    "DEN01": "TOIMITUSVIRHEILMOITUS",
    "SEI01-09": "TURVALASKU",
    "REC01-09": "KUITTI",
    "RES01-09": "TURVAKUITTI",
    "SDD01": "Suoraveloituksen ennakkoilmoitus",
}


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    def _get_move_applicability(self, move):
        if self.code != "finvoice_3_0":
            return super()._get_move_applicability(move)

        return {
            "post": self._post_invoice_edi_finvoice,
            "cancel": self._cancel_invoice_edi_finvoice,
            "edi_content": self._edi_content_invoice_edi_finvoice,
        }

    def _post_invoice_edi_finvoice(self, invoice):
        if not invoice.transmit_method_id:
            return {}

        if self.code != "finvoice_3_0":
            return super()._post_invoice_edi(invoice)

        res = {}
        attachment = self._export_finvoice(invoice)
        res[invoice] = {
            "success": True,
            "attachment": attachment,
            "message": None,
            "response": None,
        }
        # We could post finvoice to a service here
        return res

    def _cancel_invoice_edi_finvoice(self, invoice):
        if self.code != "finvoice_3_0":
            return super()._cancel_invoice_edi(invoice)

        # We could delete EDI documents here
        return

    def _edi_content_invoice_edi_finvoice(self, invoice):
        xml_string = self.env["ir.qweb"]._render(
            "account_edi_finvoice.export_finvoice", self._get_finvoice_values(invoice)
        )

        # Validate the content. This will NOT raise an error for user
        self._finvoice_check_xml_schema(xml_string)

        # Add file encoding (schema validation doesn't want this)
        # xml_string = b"<?xml version='1.0' encoding='UTF-8'?>" + xml_string

        return xml_string

    def _get_finvoice_values(self, invoice):
        def format_monetary(amount):
            amount = float_repr(amount, invoice.currency_id.decimal_places)
            amount = str(amount).replace(".", ",")

            return amount

        def format_date(dt=False):
            # Returns unhyphenated ISO-8601 date
            # CCYY-MM-DD becomes CCYYMMDD
            # 2020-01-02 becomes 20200102

            dt = dt or datetime.now()

            date_format = "%Y%m%d"

            return dt.strftime(date_format)

        # Normal sales invoice
        type_code = "INV01"
        origin_code = "Original"

        if invoice.move_type == "out_refund":
            # Refund invoice
            type_code = "INV02"
            origin_code = "Cancel"

        # Each instance of InvoiceFreeText can be 512 characters
        if invoice.narration:
            free_texts = textwrap.wrap(html2plaintext(invoice.narration), 512)
        else:
            free_texts = []

        if hasattr(invoice, "overdue_interest"):
            # Allows implementing overdue fine percent
            overdue_fine_percent = invoice.overdue_interest
        else:
            overdue_fine_percent = False

        if hasattr(invoice, "agreement_identifier"):
            # Allows implementing agreement identifier
            agreement_identifier = invoice.agreement_identifier
        else:
            agreement_identifier = invoice.ref or invoice.name

        return {
            "record": invoice,
            "format_monetary": format_monetary,
            "format_date": format_date,
            "message_timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "type_code": type_code,
            "type_text": INVOICE_TYPES.get(type_code, ""),
            "origin_code": origin_code,
            "free_texts": free_texts,
            "overdue_fine_percent": overdue_fine_percent,
            "agreement_identifier": agreement_identifier,
        }

    def _export_finvoice(self, invoice):
        self.ensure_one()

        xml_string = self._edi_content_invoice_edi_finvoice(invoice)

        xml_name = f"{invoice.name.replace('/', '_')}_finvoice_3_0.xml"
        return self.env["ir.attachment"].create(
            {
                "name": xml_name,
                "raw": xml_string,
                "mimetype": "application/xml",
                "res_model": "account.move",
            }
        )

    def _is_compatible_with_journal(self, journal):
        self.ensure_one()
        res = super()._is_compatible_with_journal(journal)
        if self.code != "finvoice_3_0":
            return res
        return journal.type == "sale"

    def _finvoice_get_xml_schema(self, version="3.0"):
        xsd_file = f"account_edi_finvoice/static/schema/Finvoice{version}.xsd"
        xsd_etree_obj = etree.parse(tools.file_open(xsd_file))
        finvoice_schema = etree.XMLSchema(xsd_etree_obj)

        return finvoice_schema

    @api.model
    def _finvoice_check_xml_schema(self, xml, version="3.0"):
        """Validate the XML file against the XSD"""
        finvoice_schema = self._finvoice_get_xml_schema(version)

        if isinstance(xml, str):
            t = etree.ElementTree(etree.fromstring(xml))
        elif isinstance(xml, bytes):
            t = etree.ElementTree(etree.fromstring(xml.decode("UTF-8")))
        else:
            t = xml

        try:
            finvoice_schema.assertValid(t)
        except etree.DocumentInvalid as e:
            # if the validation of the XSD fails, we arrive here
            _logger.warning("The XML file is invalid against the XML Schema Definition")
            _logger.warning(xml)
            _logger.warning(e)

            msg = _(
                "The Finvoice XML file is not valid against the official "
                "XML Schema Definition. The XML file and the "
                "full error have been written in the server logs. "
                "Here is the error, which may give you an idea on the "
                f"cause of the problem : {e}."
            )

            _logger.error(msg)
        return True

    def _create_invoice_from_xml_tree(self, filename, tree, journal=None):
        self.ensure_one()
        ctx = self._context
        company_id = False
        if ctx.get("allowed_company_ids"):
            company_id = ctx.get("allowed_company_ids")[0]

        if self._is_finvoice(filename, tree):
            return self._import_finvoice(
                tree, self.env["account.move"], company_id=company_id
            )
        return super()._create_invoice_from_xml_tree(filename, tree, journal)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if self._is_finvoice(filename, tree):
            return self._import_finvoice(tree, invoice)
        return super()._update_invoice_from_xml_tree(filename, tree, invoice)

    def _find_attribute(self, xpath, element, attribute):
        element = element.xpath(xpath, namespaces=element.nsmap)
        return element[0].attrib.get(attribute) if element else None

    def _find_values_joined(self, xpath, element, join_character="\n"):
        """
        Get a joined string from multiple values
        """
        elements = element.xpath(xpath, namespaces=element.nsmap)
        return join_character.join(x.text for x in elements)

    def _get_invoice_type(self, inv_type_code):
        """
        Get invoice type from Finvoice type code
        """

        if inv_type_code in ["INV01", "INV03", "INV04", "INV05", "INV08"]:
            # INV01 Invoice (Lasku)
            # INV03 Interest Invoice (Korkolasku)
            # INV04 Internal Invoice (Sisäinen lasku)
            # INV05 Collection Bill (Perintälasku)
            # INV08 Notification Invoice (Huomatuslasku)

            inv_type = "in_invoice"
        elif inv_type_code == "INV02":
            # INV02 Refund (Hyvityslasku)
            inv_type = "in_refund"
        else:
            raise UserError(_("This Finvoice XML file is not an invoice/refund file"))

        return inv_type

    def _to_float(self, string_number):
        # Format a '1 234,56' string as float 1234.56

        float_number = 0

        if isinstance(string_number, float):
            float_number = string_number
        elif isinstance(string_number, int):
            float_number = float(string_number)
        elif isinstance(string_number, str):
            if "." in string_number and "," in string_number:
                # TODO: Add support for comma as thousands separator (1,000.00)
                msg = _(
                    "Using comma as thousands separator not supported! ({})"
                ).format(string_number)
                raise UserError(msg)

            # Replace comma with period
            string_number = string_number.replace(",", ".")

            # Replace non-numeric
            string_number = re.sub(r"[^\d.-]", "", string_number)

            float_number = float(string_number)

        return float_number

    def _retrieve_bank_account(
        self, account_number, partner_id, bic=False, company_id=False
    ):
        """
        Search for bank account or create a new one
        """
        if not account_number:
            return None

        if not company_id:
            company_id = self.env.company.id

        account_numbers = [account_number, account_number.replace(" ", "")]
        partner_bank = self.env["res.partner.bank"]

        domain = [
            ("acc_number", "in", account_numbers),
            # In some cases (e.g. business groups, organizations) the partner
            # is not the owner of the bank account.
            # This would cause an error, as we try to create an overlapping
            # bank account number
            # ("partner_id", "=", partner_id),
            ("company_id", "in", [company_id, False]),
        ]
        bank_account = partner_bank.search(domain, limit=1)

        if not bank_account:
            account_vals = {
                "acc_number": account_number,
                "partner_id": partner_id,
                "company_id": company_id,
                # Automatic journal selection doesn't work
                "journal_id": False,
            }
            if bic:
                bank_id = self.env["res.bank"].search(
                    [("bic", "=", bic.upper())], limit=1
                )
                if bank_id:
                    account_vals["bank_id"] = bank_id.id

            bank_account = partner_bank.create(account_vals)

        return bank_account
