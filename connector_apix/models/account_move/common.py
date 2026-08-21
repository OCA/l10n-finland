import logging
import zipfile
from io import BytesIO

from lxml import etree

from odoo import fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval, time

from ...constants import APIX_CHANNEL

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    date_einvoice_sent = fields.Date(string="eInvoice sent", copy=False)
    apix_bind_ids = fields.One2many(
        comodel_name="apix.account.invoice",
        inverse_name="odoo_id",
        string="APIX Bindings",
    )

    def get_apix_backend(self):
        self.ensure_one()

        if not self.company_id:
            raise ValidationError(self.env._("This invoice has no company."))

        backend = self.env["apix.backend"].search(
            [
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )

        return backend

    def action_einvoice_send(self):
        for record in self:
            if len(self) > 1:
                # Add sending to queue
                job_kwargs = {
                    "description": self.env._("APIX send invoice '%s'", record.name),
                    "channel": APIX_CHANNEL,
                }
                record.with_delay(**job_kwargs).einvoice_send()
                # Set invoice as being sent
                record.write(
                    {
                        "is_being_sent": True,
                    }
                )
            else:
                # Send eInvoice now
                record.einvoice_send()

    def _get_finvoice_object(self):
        finvoice_object = super()._get_finvoice_object()

        self.add_finvoice_apix_fields(finvoice_object)

        return finvoice_object

    def _get_finvoice_message_sender_details(self):
        MessageSenderDetailsType = super()._get_finvoice_message_sender_details()
        MessageSenderDetailsType.set_FromIntermediator("APIX")

        return MessageSenderDetailsType

    def _get_finvoice_message_receiver_details(self):
        MessageReceiverDetailsType = super()._get_finvoice_message_receiver_details()

        if self.transmit_method_id.code == "printing_service":
            MessageReceiverDetailsType.set_ToIdentifier("TULOSTUS")

        return MessageReceiverDetailsType

    def add_finvoice_apix_fields(self, finvoice_attachment, attachments=False):
        root = etree.fromstring(finvoice_attachment.raw)

        # Add PDF info after EPI details
        # The format is
        # <InvoiceUrlNameText>APIX_PDFFILE</ InvoiceUrlNameText>
        # <InvoiceUrlNameText>APIX_ATTACHMENT</ InvoiceUrlNameText>
        # <InvoiceUrlText>file://invoice.pdf</ InvoiceUrlText>
        # <InvoiceUrlText>attachments.zip</ InvoiceUrlText>

        url_name = etree.Element("InvoiceUrlNameText")
        url_name.text = "APIX_PDFFILE"
        root.append(url_name)

        if attachments:
            url_name = etree.Element("InvoiceUrlNameText")
            url_name.text = "APIX_ATTACHMENT"

            root.append(url_name)

        url_text = etree.Element("InvoiceUrlText")
        url_text.text = "file://invoice.pdf"
        root.append(url_text)

        if attachments:
            url_text = etree.Element("InvoiceUrlText")
            url_text.text = "file://attachments.zip"
            root.append(url_text)

        return etree.tostring(root)

    def get_apix_payload(self):
        self.ensure_one()

        _logger.debug(f"Generating APIX payload for '{self.name}'")
        # Generate PDF
        backend = self.get_apix_backend()
        inv_report = backend.invoice_template_id
        _logger.debug(f"Using report template '{inv_report.report_name}'")
        inv_pdf = inv_report._render_qweb_pdf(inv_report.report_name, self.ids)

        # Get attachments
        attachments = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "account.move"),
                ("res_id", "in", self.ids),
                # ("mimetype", "in", ["application/pdf"]),
            ]
        )

        # Get EDI document (Finvoice document)
        finvoice_xml = self.edi_document_ids.filtered(
            lambda s: s.edi_format_id.code == "finvoice_3_0"
        )

        if not finvoice_xml:
            raise ValidationError(
                self.env._("Could not find a Finvoice document to export")
            )

        # Use the latest document
        finvoice_xml = finvoice_xml[0].sudo()

        # Construct Finvoice XML data
        attachment_names = ["invoice.pdf"]
        attachment_names += attachments.mapped("name")
        finvoice_attachment = finvoice_xml.attachment_id
        finvoice_filename = finvoice_attachment.name
        finvoice_datas = self.add_finvoice_apix_fields(
            finvoice_attachment, len(attachments) > 0
        )

        # Add attachments to zip
        attachments_zip_tmp = BytesIO()
        attachments_payload = False
        if attachments:
            with zipfile.ZipFile(attachments_zip_tmp, "w") as attachments_zip:
                # Iterate through all the attachments
                for attachment in attachments:
                    # Write the file to the cached zip
                    file_name = attachment.name or "attachment"

                    attachments_zip.writestr(file_name, attachment.raw)

            attachments_payload = attachments_zip_tmp.getvalue()

        payload_zip_tmp = BytesIO()
        # Write the payload
        with zipfile.ZipFile(payload_zip_tmp, "w") as payload_zip:
            payload_data = finvoice_datas
            payload_zip.writestr(finvoice_filename, payload_data)

            # Add printed PDF
            payload_zip.writestr("invoice.pdf", inv_pdf[0])
            # Save PDF as attachment
            if inv_report.print_report_name:
                report_name = safe_eval(
                    inv_report.print_report_name, {"object": self, "time": time}
                )
            else:
                report_name = f"{self.name}.pdf"

            self.env["ir.attachment"].create(
                {
                    "name": report_name,
                    "raw": inv_pdf[0],
                    "mimetype": "application/pdf",
                    "res_model": "account.move",
                    "res_id": self.id,
                }
            )

            # Add attachments
            if attachments_payload:
                _logger.debug("Adding attachments")
                payload_zip.writestr("attachments.zip", attachments_payload)

        payload = payload_zip_tmp.getvalue()
        _logger.debug(f"APIX payload for '{self.name}' generated")

        return payload

    def einvoice_send(self):
        for record in self:
            if record.apix_bind_ids:
                raise UserError(
                    self.env._("This invoice has already been sent as an eInvoice")
                )

            record.validate_einvoice()

            # Transmit method name
            transmit_method = record.transmit_method_id.name

            _logger.debug("Sending '%s' as '%s'", record.name, transmit_method)

            backend = record.get_apix_backend()

            if not backend:
                raise Exception(self.env._("No backend found"))

            _logger.debug("Using backend %s", backend.name)

            payload = record.get_apix_payload()

            if backend.debug:
                self.env["ir.attachment"].create(
                    {
                        "name": f"apix_payload_{record.name}.zip",
                        "raw": payload,
                        "mimetype": "application/zip",
                    }
                )
            response = backend.SendInvoiceZIP(payload)

            _logger.debug("Response for '%s': %s", record.name, response)

            record.write(
                {
                    "date_einvoice_sent": fields.Date.today(),
                    "is_move_sent": True,
                    "is_being_sent": False,
                }
            )

            apix_batch_id = response.find(".//Value[@type='BatchID']")
            if apix_batch_id is not None:
                apix_batch_id = apix_batch_id.text

            apix_accepted_document_id = response.find(
                ".//Value[@type='AcceptedDocumentID']"
            )

            if apix_accepted_document_id is not None:
                apix_accepted_document_id = apix_accepted_document_id.text

            apix_cost_in_credits = response.find(".//Value[@type='CostInCredits']")

            if apix_cost_in_credits is not None:
                apix_cost_in_credits = apix_cost_in_credits.text

            binding_values = dict(
                backend_id=backend.id,
                odoo_id=record.id,
                apix_batch_id=apix_batch_id,
                apix_accepted_document_id=apix_accepted_document_id,
                apix_cost_in_credits=apix_cost_in_credits,
            )

            self.sudo().env["apix.account.invoice"].create(binding_values)

            record.message_post(
                body=self.env._("Invoice sent as '%s'", transmit_method)
            )
            _logger.debug("Sent '%s' as '%s'", record.name, transmit_method)

    def validate_einvoice(self):
        result = False
        msg = False
        self.ensure_one()

        # Invoice can be sent only when it is open or paid
        # open: normal invoice
        # paid: for resending (original invoice is not received or not paid)
        if self.state != "posted":
            msg = self.env._("You can only send eInvoice after the invoice is posted")

        # Check these only for eInvoice
        elif self.transmit_method_code in ["einvoice"]:
            # VAT number is missing
            if not self.partner_id.vat:
                msg = self.env._(
                    "Please set VAT number for the customer '%s' before "
                    "sending an eInvoice.",
                    self.partner_id.name,
                )
            # Edicode is missing
            elif not self.partner_id.edicode:
                msg = self.env._(
                    "Please set edicode for the customer '%s' "
                    "before sending an eInvoice.",
                    self.partner_id.name,
                )
            # Operator is missing
            elif not self.partner_id.einvoice_operator_id:
                msg = self.env._(
                    "Please set eInvoice operator for the customer '%s' "
                    "before sending an eInvoice.",
                    self.partner_id.name,
                )

        # Wrong invoice transmit type
        elif self.transmit_method_code not in ["einvoice", "printing_service"]:
            msg = self.env._("This invoice has been marked to be sent manually.")

        elif not self.partner_bank_id:
            msg = self.env._("Please define a bank account for the invoice.")

        else:
            result = True

        if msg:
            raise ValidationError(msg)

        return result
