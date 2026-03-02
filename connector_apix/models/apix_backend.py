import base64
import datetime
import hashlib
import logging
from collections import OrderedDict
from io import BytesIO
from mimetypes import MimeTypes
from zipfile import ZipFile

import requests
from lxml import etree as ET

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from ..constants import APIX_CHANNEL

_logger = logging.getLogger(__name__)


class ApixBackend(models.Model):
    # region Private attributes
    _name = "apix.backend"
    _description = "APIX Backend"
    _inherit = "connector.backend"

    _sql_constraints = [
        ("company_uniq", "unique(company_id)", "Company can have only one backend."),
    ]

    _FIELD_STATES = {
        "confirmed": [("readonly", True)],
        "unconfirmed": [("readonly", False)],
    }
    # endregion

    # region Fields declaration
    name = fields.Char(
        default=lambda self: self.env.user.company_id.name,
    )

    # Backends start as unconfirmed
    state = fields.Selection(
        selection=[
            ("unconfirmed", "Unconfirmed"),
            ("confirmed", "Confirmed"),
        ],
        default="unconfirmed",
    )

    # Company for multicompany environments
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.user.company_id.id,
    )

    # Apix username (email)
    username = fields.Char(
        required=True, help="Username used to login to laskumappi.fi"
    )

    # Apix password
    password = fields.Char(
        required=True,
        copy=False,
        help="Password used to login to laskumappi.fi",
    )

    # Apix API version
    version = fields.Selection(
        selection=[("1.14", "v1.14")],
        default="1.14",
        required=True,
    )

    # Apix environment
    environment = fields.Selection(
        selection=[("test", "Test"), ("production", "Production")],
        default="test",
        required=True,
    )

    debug = fields.Boolean(
        string="Debug mode",
        help="Save debugging data, like APIX payload as an attachment",
        default=False,
    )

    # An optional prefix for business ids.
    # Apix may assign this to virtual operators
    prefix = fields.Char(
        help="Optional business code prefix. "
        "Some virtual operators use these. "
        "If you don't know what this is, leave it empty",
    )

    transfer_id = fields.Char(
        string="Transfer id",
        readonly=True,
        copy=False,
        help="The identification used for sending and receiving invoices",
    )

    transfer_key = fields.Char(
        string="Transfer key",
        readonly=True,
        copy=False,
        help="The password used for sending and receiving invoices",
    )

    company_uuid = fields.Char(
        string="Company UUID",
        readonly=True,
        copy=False,
        help="A unique identifier assigned to the company",
    )

    # The "business id".
    # This can be plain business id or a business id with a prefix
    business_id = fields.Char(
        string="Business code",
        compute="_compute_business_id",
    )

    # Qualifier for the identification; y-tunnus, orgnr etc.
    # Usually business id (y-tunnus)
    id_qualifier = fields.Selection(
        selection=[("y-tunnus", "Business ID")],
        string="ID Qualifier",
        default="y-tunnus",
        required=True,
        readonly=True,
    )

    # IdCustomer
    customer_id = fields.Char(
        string="Customer ID",
    )

    # CustomerNumber
    customer_number = fields.Char(
        string="Customer number",
        readonly=True,
    )

    # ContactPerson
    contact_person = fields.Char(
        string="Contact person",
        readonly=True,
    )

    # Email
    contact_email = fields.Char(
        string="Contact email",
        readonly=True,
    )

    # OwnerId
    owner_id = fields.Char(
        string="Owner ID",
        readonly=True,
    )

    # Odoo-settings
    support_email = fields.Char(
        string="Support email",
        help='Replaces "servicedesk@apix.fi" with this address, if set',
    )

    invoice_template_id = fields.Many2one(
        comodel_name="ir.actions.report",
        domain=[("model", "=", "account.move")],
        string="Invoice template",
        help="Report template used when sending invoices via APIX",
        required=True,
        default=lambda s: s.env.ref("account.account_invoices"),
    )
    # endregion

    def _compute_business_id(self):
        for record in self:
            prefix = record.prefix or ""
            business_id = record.company_id.company_registry or ""

            record.business_id = prefix + business_id

    # region Action methods
    def action_authenticate(self):
        # A helper method for testing the authentication
        for record in self:
            record.RetrieveTransferID()
            record.AuthenticateByUser()

            # Everything is fine (no errors). Set this as confirmed
            record.state = "confirmed"

    def action_reset_authentication(self):
        # A helper method for resetting the authentication
        for record in self:
            record.transfer_id = False
            record.transfer_key = False
            record.company_uuid = False
            record.state = "unconfirmed"

    def action_cron_einvoice_fetch(self):
        for backend in self.search([]):
            backend.action_einvoice_fetch()

    def action_einvoice_fetch(self):
        for record in self:
            # Add fetching to queue
            job_kwargs = {
                "description": _("APIX fetch invoices for '%s'") % record.name,
                "channel": APIX_CHANNEL,
            }
            record.with_company(record.company_id.id).with_delay(
                **job_kwargs
            ).list_invoices(refetch=False)

    def action_einvoice_refetch(self):
        for record in self:
            # Add fetching to queue
            job_kwargs = {
                "description": _("APIX refetch invoices for '{}'").format(record.name),
                "channel": APIX_CHANNEL,
            }
            record.with_company(record.company_id.id).with_delay(
                **job_kwargs
            ).list_invoices(refetch=True)

    def list_invoices(self, refetch=False):
        """
        Fetch list of invoices from APIX
        This will always fetch everything as there is no filter options.
        Filtering should be added when it will become available

        :param refetch: Re-fetch already downloaded invoices
        :return:
        """
        self.ensure_one()

        # Fetch einvoices
        invoices = self.ListInvoiceZIPs()

        _logger.debug(f"Invoice XML: {ET.tostring(invoices, pretty_print=True)}")
        for invoice in invoices.findall(".//Group"):
            storage_id = invoice.find(".//Value[@type='StorageID']").text
            storage_key = invoice.find(".//Value[@type='StorageKey']").text
            storage_status = invoice.find(".//Value[@type='StorageStatus']").text

            document_id_element = invoice.find(".//Value[@type='DocumentID']")
            if document_id_element is not None:
                # Document id is better, if it's found
                document_id = document_id_element.text
            else:
                # Storage id is always found, but is less useful
                document_id = storage_id

            # Try to get sender name
            sender_name_element = invoice.find(".//Value[@type='SenderName']")
            if sender_name_element is not None:
                sender_name = sender_name_element.text
            else:
                sender_name = "Unknown"

            if (
                storage_status == "UNRECEIVED"
                or refetch
                and storage_status == "RECEIVED"
            ):
                job_kwargs = {
                    "description": _(
                        f'APIX import invoice "{document_id}" from {sender_name}'
                    ),
                    "channel": APIX_CHANNEL,
                }
                self.with_company(self.company_id.id).with_delay(
                    **job_kwargs
                ).download_invoice(storage_id, storage_key)

    def download_invoice(self, storage_id, storage_key):
        self.ensure_one()

        # Download invoice
        res = self.Download(storage_id, storage_key)

        return _(f"Imported invoice with id '{res.id}'")

    # endregion

    def get_digest(self, values):
        # Returns the digest needed for requests
        digest_src = ""

        for value in values:
            digest_src += values[value] + "+"

        # Strip the last "+"
        digest_src = digest_src[:-1]
        _logger.debug(f"Calculating digest from '{digest_src}'")
        digest = "SHA-256:" + hashlib.sha256(digest_src.encode("utf-8")).hexdigest()

        return digest

    def get_password_hash(self):
        # Returns a hashed password
        password_hash = hashlib.sha256(self.password.encode("utf-8")).hexdigest()

        return password_hash

    def get_timestamp(self):
        # Returns the timestamp in the correct format for the REST API

        now = datetime.datetime.today()

        # Construct the timestamp
        timestamp = now.strftime("%Y%m%d%H%M%S")

        return timestamp

    def get_url(self, command, variables=False):
        # Returns the REST URL based on the environment, command and variables
        # Please note that variables should always be in OrderedDict,
        # as APIX API expects the variables in a certain order

        if not variables:
            variables = {}

        terminal_commands = ["list", "list2", "receive", "download", "metadata"]

        if self.environment == "production":
            if command in terminal_commands:
                url = "https://terminal.apix.fi/"
            else:
                url = "https://api.apix.fi/"
        else:
            if command in terminal_commands:
                url = "https://test-terminal.apix.fi/"
            else:
                url = "https://test-api.apix.fi/"

        url += f"{command}?"

        for key, value in variables.items():
            url += f"{key}={value}&"  # Add variables to the url

        if variables:
            url = url.rstrip("&")  # Strip the last &

        _logger.debug(f"Using url '{url}")

        return url

    def get_values_from_url(self, url):
        response = requests.get(url, timeout=30)
        html = response.text.encode("latin-1")
        root = ET.fromstring(html)

        # Get response status
        res_status = " ".join([status.text for status in root.findall("Status")])
        res_status_code = " ".join(
            [status.text for status in root.findall("StatusCode")]
        )
        res_free_text = " ".join([status.text for status in root.findall("FreeText")])

        msg = f"{res_status} [{res_status_code}]: {res_free_text}"

        if res_status == "ERR":
            _logger.warning(msg)  # Log error message and error
            raise ValidationError(res_free_text)  # Show the human-readable part
        else:
            _logger.debug(msg)

        groups = list()
        for group in root.iter("Group"):
            values = dict()
            for value in group.iter("Value"):
                values[value.attrib["type"]] = value.text

            groups.append(values)

        # Only one item
        if len(groups) == 1:
            groups = groups[0]

        return groups

    # RetrieveTransferID API method
    def RetrieveTransferID(self):
        _logger.debug("APIX RetrieveTransferId")

        values = OrderedDict()
        values["id"] = self.business_id
        values["idq"] = self.id_qualifier
        values["uid"] = self.username
        values["ts"] = self.get_timestamp()
        values["d"] = self.get_password_hash()

        # Get the digest hash
        values["d"] = self.get_digest(values)

        command = "app-transferID"
        url = self.get_url(command, values)
        response = self.get_values_from_url(url)

        if response:
            self.transfer_id = response.get("TransferID", False)
            self.transfer_key = response.get("TransferKey", False)
            self.company_uuid = response.get("UniqueCompanyID", False)

    # AuthenticateByUser API method
    def AuthenticateByUser(self):
        _logger.debug("APIX AuthenticateByUser")

        values = OrderedDict()
        values["uid"] = self.username
        values["t"] = self.get_timestamp()
        values["d"] = self.get_password_hash()

        # Get the digest hash
        values["d"] = self.get_digest(values)

        # Add pass to variables
        values["pass"] = self.password

        command = "authuser"
        url = self.get_url(command, values)
        response = self.get_values_from_url(url)

        if isinstance(response, list):
            # For some reason the res can also be a list with one dict in it (?)
            response = response[0]

        if response:
            self.customer_id = response.get("IdCustomer", False)
            self.customer_number = response.get("CustomerNumber", False)
            self.contact_person = response.get("ContactPerson", False)
            self.contact_email = response.get("Email", False)
            self.owner_id = response.get("OwnerId", False)

    def get_default_url_attributes(
        self,
        show_soft=True,  # Software
        show_ver=True,  # Software version
        storage_id=False,  # StorageID
        storage_key=False,  # StorageKey
        mark_received=False,  # Mark invoice as received
    ):
        values = OrderedDict()

        if show_soft:
            values["soft"] = "Standard"

        if show_ver:
            values["ver"] = "1.0"

        if mark_received:
            values["markReceived"] = "yes"

        # Use SID OR TraID, never both
        if storage_id:
            values["SID"] = storage_id
        else:
            values["TraID"] = self.transfer_id

        values["t"] = self.get_timestamp()

        if storage_key:
            values["StorageKey"] = storage_key
        else:
            values["TraKey"] = self.transfer_key

        # Get the digest hash
        values["d"] = self.get_digest(values)

        # Remove TransferKey and StorageKey. We don't want them to the url
        values.pop("TraKey", None)
        values.pop("StorageKey", None)

        _logger.debug(f"Using values '{values}")

        return values

    def SendInvoiceZIP(self, payload):
        _logger.debug("APIX SendInvoiceZIP")
        values = self.get_default_url_attributes()

        command = "invoices"
        url = self.get_url(command, values)

        # Post the file to the server
        res = requests.put(url, data=payload, timeout=30)
        res.raise_for_status()

        utf8_parser = ET.XMLParser(encoding="utf-8")
        res_etree = ET.fromstring(res.text.encode("utf-8"), parser=utf8_parser)

        self.validateResponse(res_etree)

        return res_etree

    def ListInvoiceZIPs(self):
        _logger.debug("APIX ListInvoiceZIPs")

        values = self.get_default_url_attributes(show_soft=False, show_ver=False)

        command = "list2"
        url = self.get_url(command, values)

        # Get invoices from server
        res = requests.get(url, timeout=30)
        res.raise_for_status()

        utf8_parser = ET.XMLParser(encoding="utf-8")
        res_etree = ET.fromstring(res.text.encode("utf-8"), parser=utf8_parser)

        return res_etree

    def Download(self, storage_id, storage_key):
        _logger.debug("APIX Download")
        values = self.get_default_url_attributes(
            show_soft=False,
            show_ver=False,
            mark_received=False,
            storage_id=storage_id,
            storage_key=storage_key,
        )

        command = "download"
        company_id = self.company_id.id
        url = self.get_url(command, values)

        # Download invoice from server
        res = requests.get(url, timeout=30)
        res.raise_for_status()

        zip_file = ZipFile(BytesIO(res.content))
        mime = MimeTypes()

        ir_attachment = self.env["ir.attachment"]
        attachment_ids = self.env["ir.attachment"]

        invoice = False
        for file_name in zip_file.namelist():
            # Save to attachments without res_id
            file_data = zip_file.read(file_name)
            datas = base64.b64encode(file_data)
            values = dict(
                name=file_name,
                type="binary",
                datas=datas,
                res_model="account.move",
                mimetype=mime.guess_type(file_name)[0],
                company_id=company_id,
            )

            if file_name == "invoice.xml":
                # The actual invoice data
                invoice = self.env["account.move"]._import_finvoice(
                    ET.fromstring(file_data),
                    self.env["account.move"].create(
                        {
                            "move_type": "in_invoice",
                            "company_id": company_id,
                        }
                    ),
                    company_id,
                )
            else:
                attachment_ids += ir_attachment.create(values)

        if not invoice:
            raise ValidationError(_("Could not create invoice"))

        attachment_ids.write({"res_id": invoice.id})

        return invoice

    def validateResponse(self, response):
        _logger.debug(f"Response: {ET.tostring(response)}")

        response_status = response.find(".//Status")

        if response_status is None:
            raise ValidationError(_("Invalid response: response status not found"))

        _logger.debug(f"Response status: '{response_status.text}'")

        if response_status.text == "ERR":
            try:
                error = response.find(".//Value[@type='ValidateText']")
                if error:
                    error = error.text
                else:
                    error = ". ".join([r.text for r in response.findall(".//FreeText")])
            except Exception as e:
                error = _("Unknown error")
                _logger.error(e)

            try:
                statuscode = response.find(".//StatusCode").text
            except Exception as e:
                statuscode = _("Unknown status code")
                _logger.error(e)

            msg = f"API Error ({statuscode}): {error}"

            # Replace the support address shown in the message
            if self.support_email:
                msg = msg.replace("servicedesk@apix.fi", self.support_email)

            raise ValidationError(msg)

        elif response_status == "OK":
            # Response is OK, no actions
            return
