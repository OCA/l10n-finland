import logging

from odoo.tests import common

_logger = logging.getLogger(__name__)


class TestIapAutocompleteApi(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._init_partner_autocomplete()
        # Change the IAP account provider

    @classmethod
    def _init_partner_autocomplete(cls):
        iap_service = cls.env["iap.service"].search(
            [("technical_name", "=", "partner_autocomplete")], limit=1
        )
        _logger.info("Using IAP service: %s", iap_service)

        iap_account = cls.env["iap.account"].create(
            {
                "name": "Partner Autocomplete",
                "provider": "prh",
                "service_id": iap_service.id,
                "prh_use_industry": True,
                "prh_language_code": "1",
            }
        )
        _logger.info("Created IAP account: %s", iap_account)

        cls.iap_account = iap_account

    def test_get_or_create_industry(self):
        iap_autocomplete_api = self.env["iap.autocomplete.api"]

        business_line = {
            "type": "62100",
            "descriptions": [
                {"languageCode": "3", "description": "Computer programming activities"},
                {"languageCode": "2", "description": "Dataprogrammering"},
                {
                    "languageCode": "1",
                    "description": "Ohjelmistojen suunnittelu ja valmistus",
                },
            ],
            "typeCodeSet": "TOIMI4",
            "registrationDate": "2026-01-01",
            "source": "2",
        }

        iap_autocomplete_api._get_or_create_industry(self.iap_account, business_line)

        self.assertTrue(
            self.env["res.partner.industry"].search(
                [("name", "=ilike", "Ohjelmistojen suunnittelu ja valmistus")]
            )
        )

    def test_prh_get_company_name(self):
        iap_autocomplete_api = self.env["iap.autocomplete.api"]

        company = {
            "names": [
                {"type": "1", "name": "Old Trade Name", "endDate": "2023-01-01"},
                {"type": "1", "name": "New Trade Name", "endDate": None},
            ]
        }

        company_name = iap_autocomplete_api._prh_get_company_name(company)
        self.assertEqual(company_name, "New Trade Name")

    def test_prh_parse_company(self):
        iap_autocomplete_api = self.env["iap.autocomplete.api"]

        company = {
            "businessId": {
                "value": "1935052-9",
                "registrationDate": "2004-12-13",
                "source": "3",
            },
            "euId": {"value": "FIFPRO.1935052-9", "source": "1"},
            "names": [
                {
                    "name": "Futural Oy",
                    "type": "1",
                    "registrationDate": "2024-10-23",
                    "version": 1,
                    "source": "1",
                },
                {
                    "name": "Oy Tawasta OS Technologies Ltd.",
                    "type": "1",
                    "registrationDate": "2005-01-03",
                    "endDate": "2024-10-23",
                    "version": 2,
                    "source": "1",
                },
            ],
            "mainBusinessLine": {
                "type": "62100",
                "descriptions": [
                    {
                        "languageCode": "3",
                        "description": "Computer programming activities",
                    },
                    {"languageCode": "2", "description": "Dataprogrammering"},
                    {
                        "languageCode": "1",
                        "description": "Ohjelmistojen suunnittelu ja valmistus",
                    },
                ],
                "typeCodeSet": "TOIMI4",
                "registrationDate": "2026-01-01",
                "source": "2",
            },
            "website": {
                "url": "www.futural.fi",
                "registrationDate": "2025-02-14",
                "source": "0",
            },
            "companyForms": [
                {
                    "type": "16",
                    "descriptions": [
                        {"languageCode": "2", "description": "Aktiebolag"},
                        {"languageCode": "3", "description": "Limited company"},
                        {"languageCode": "1", "description": "Osakeyhtiö"},
                    ],
                    "registrationDate": "2005-01-03",
                    "version": 1,
                    "source": "1",
                }
            ],
            "companySituations": [],
            "registeredEntries": [
                {
                    "type": "80",
                    "descriptions": [
                        {
                            "languageCode": "1",
                            "description": "Liiketoiminnasta arvonlisäverovelvollinen",
                        },
                        {
                            "languageCode": "2",
                            "description": "Momsskyldig för rörelseverksamhet",
                        },
                        {
                            "languageCode": "3",
                            "description": "VAT-liable for business activity",
                        },
                    ],
                    "registrationDate": "2004-12-01",
                    "register": "6",
                    "authority": "1",
                },
            ],
            "addresses": [
                {
                    "type": 1,
                    "street": "Sibeliuksenkatu",
                    "postCode": "13100",
                    "postOffices": [
                        {
                            "city": "HÄMEENLINNA",
                            "languageCode": "1",
                            "municipalityCode": "109",
                        },
                        {
                            "city": "HÄMEENLINNA",
                            "languageCode": "2",
                            "municipalityCode": "109",
                        },
                    ],
                    "buildingNumber": "25",
                    "entrance": "B",
                    "apartmentNumber": "12",
                    "apartmentIdSuffix": "",
                    "co": "",
                    "registrationDate": "2023-02-24",
                    "source": "0",
                },
                {
                    "type": 2,
                    "postCode": "33101",
                    "postOffices": [
                        {
                            "city": "TAMPERE",
                            "languageCode": "1",
                            "municipalityCode": "837",
                        },
                        {
                            "city": "TAMPERE",
                            "languageCode": "2",
                            "municipalityCode": "837",
                        },
                    ],
                    "postOfficeBox": "82",
                    "registrationDate": "2009-04-01",
                    "source": "0",
                },
            ],
            "tradeRegisterStatus": "1",
            "status": "2",
            "registrationDate": "2005-01-03",
        }

        values = iap_autocomplete_api._prh_parse_company(self.iap_account, company)

        self.assertEqual(values["name"], "Futural Oy")
        self.assertEqual(values["company_registry"], "1935052-9")
        self.assertEqual(values["vat"], "FI19350529")
        self.assertEqual(values["city"], "TAMPERE")
        # TODO: check partner values like street, zip code, etc.

    def test_contact_iap(self):
        # TODO: Implement test for _contact_iap method using mock API responses
        # iap_autocomplete_api = self.env["iap.autocomplete.api"]

        # local_endpoint = "/api/dnb/1"
        # action_search = "search_by_name"
        # params1 = {'query': 'Futural Oy', 'query_country_code': 'FI'}
        # params2 = {'query': '1935052-9', 'query_country_code': 'FI'}

        # TODO: A mock api
        # search_result1 = iap_autocomplete_api._contact_iap(
        # local_endpoint, action_search, params1)
        # search_result2 = iap_autocomplete_api._contact_iap(
        # local_endpoint, action_search, params2)

        # action_enrich = "enrich_by_duns"
        # params3 = {'duns': '1935052-9'}

        # result3 = iap_autocomplete_api._contact_iap(
        # local_endpoint, action_enrich, params3)

        self.assertTrue(True)
