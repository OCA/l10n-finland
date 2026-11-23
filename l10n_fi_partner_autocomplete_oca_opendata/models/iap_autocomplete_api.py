import requests

from odoo import api, models
from odoo.exceptions import ValidationError


class IapAutocompleteApi(models.AbstractModel):
    _inherit = "iap.autocomplete.api"

    @api.model
    def _contact_iap(self, local_endpoint, action, params, timeout=15):
        iap_account = self.env["iap.account"].get("partner_autocomplete")
        query = params.get("query")
        # TODO: When using global search, country code is False.
        # We could fall back to Odoo IAP, but it would require credits
        # country_code = query.get("country_code") if query else None

        if iap_account.provider == "prh":
            create_industry = False
            if action == "search_by_name":
                if query and len(query) == 9 and query[7] == "-":
                    # If query looks like a business id, search by business id
                    # Business ID is something like "1234567-1"
                    params["businessId"] = query
                else:
                    # Otherwise, search by name
                    params["name"] = query
            elif action == "enrich_by_duns":
                # This is the action to enrich company details.
                # We are misusing it a bit
                params["businessId"] = params.get("duns")
                create_industry = iap_account.prh_use_industry

            base_url = "https://avoindata.prh.fi/opendata-ytj-api/v3/"
            endpoint = "companies"
            api_url = f"{base_url}{endpoint}"
            response = requests.get(api_url, params=params, timeout=10)

            companies = self._parse_prh_response(
                iap_account,
                response,
                create_industry=create_industry,
            )

            if action == "enrich_by_duns":
                # Only return the first finding
                companies = companies[0] if companies else {}

            res = {"data": companies}
        else:
            res = super()._contact_iap(local_endpoint, action, params, timeout=timeout)

        return res

    def _parse_prh_response(self, iap_account, response, create_industry=False):
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise ValidationError(self.env._("PRH API request failed: %s", e)) from e

        companies = response.json().get("companies", [])

        company_list = []

        for company in companies:
            values = self._prh_parse_company(
                iap_account, company, create_industry=create_industry
            )

            company_list.append(values)

        return company_list

    def _prh_parse_company(self, iap_account, company, create_industry=True):
        values = {}
        # TODO: can we get the country from response?
        country_code = "FI"
        values["country_code"] = country_code
        values["preferred_language"] = "fi_FI"

        values["name"] = self._prh_get_company_name(company)

        if company.get("businessId"):
            business_id = company.get("businessId").get("value")
            vat_number = ""

            registers = company.get("registeredEntries", [])
            is_vat_registered = next(
                (
                    register
                    for register in registers
                    if register.get("register") == "6" and not register.get("endDate")
                ),
                None,
            )
            if is_vat_registered and business_id and "-" in business_id:
                clean_bid = business_id.replace("-", "")
                vat_number = f"{country_code}{clean_bid}"

            values["company_registry"] = business_id
            values["vat"] = vat_number
            # We are misusing this field a bit here
            values["duns"] = business_id

        if company.get("website"):
            values["website"] = company["website"].get("url")

        # Update address details
        addresses = company.get("addresses", [])
        if addresses:
            street = []

            post_address = next(
                (
                    addr
                    for addr in addresses
                    if addr.get("type") == 2 and not addr.get("endDate")
                ),
                None,
            )
            if not post_address:
                post_address = next(
                    (
                        addr
                        for addr in addresses
                        if not addr.get("endDate") and addr.get("type") in [1, 2]
                    ),
                    None,
                )
            if post_address:
                if post_address.get("street"):
                    street.append(post_address.get("street"))
                if post_address.get("buildingNumber"):
                    street.append(post_address.get("buildingNumber"))
                if post_address.get("apartmentNumber"):
                    street.append(post_address.get("apartmentNumber"))

                values["zip"] = post_address.get("postCode", "")

                post_offices = post_address.get("postOffices", [])
                if post_offices:
                    finnish_city = next(
                        (
                            p.get("city")
                            for p in post_offices
                            if p.get("languageCode") == "1"
                        ),
                        None,
                    )
                    values["city"] = finnish_city or post_offices[0].get("city", "")

            if street:
                # Construct the street
                values["street"] = " ".join(street)

            business_line = company.get("mainBusinessLine")
            if create_industry and business_line:
                industry = self._get_or_create_industry(iap_account, business_line)
                values["industry_id"] = {
                    "id": industry.id,
                    "display_name": industry.display_name,
                }

        return values

    def _prh_get_company_name(self, company):
        res = ""
        company_names = company.get("names", [])
        if company_names:
            # Use the first found name
            active_trade_name_record = next(
                (
                    name_rec
                    for name_rec in company_names
                    if name_rec.get("type") == "1" and not name_rec.get("endDate")
                ),
                None,
            )
            # If no active trade name is found, fallback to the any available name
            if not active_trade_name_record:
                active_trade_name_record = next(
                    (
                        name_rec
                        for name_rec in company_names
                        if name_rec.get("type") == "1"
                    ),
                    None,
                )

            res = active_trade_name_record.get("name", "")

        return res

    def _get_or_create_industry(self, iap_account, business_line):
        # Get or create an industry

        language_code = iap_account.prh_language_code
        name = ""

        for desc in business_line.get("descriptions"):
            if desc.get("languageCode") == language_code:
                name = desc.get("description")

        code = business_line.get("type")

        industry_model = self.env["res.partner.industry"].sudo()
        industry = industry_model.search([("name", "=ilike", name)], limit=1)

        if not industry:
            industry = industry_model.create(
                {
                    "name": name,
                    "full_name": f"[{code}] {name}",
                }
            )

        return industry
