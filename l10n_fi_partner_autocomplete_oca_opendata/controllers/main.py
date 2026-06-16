from odoo.addons.partner_autocomplete_oca.controllers.main import OCAAutocompleteController
import requests

class OCAAutocompleteController(OCAAutocompleteController):
    def _search_for_country(self, country_code, query, api_key, env_type):
        if country_code == 'FI':
            if env_type == 'free':
                return self._search_open_data(query)
        
        return super()._search_for_country(country_code, query, api_key, env_type)

    def _search_open_data(self, query):
        EXTERNAL_API_BASE_URL = "https://avoindata.prh.fi/opendata-ytj-api/v3"
        RESOURCE_PATH = "/companies"

        api_url = f"{EXTERNAL_API_BASE_URL}{RESOURCE_PATH}"
        params = {'name': query} 

        results = []
        try:
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'companies' in data:
                for item in data['companies']:

                    names = item.get('names', []) 
                    active_trade_name_record = next((
                        name_rec for name_rec in names
                        if name_rec.get('type') == "1" and not name_rec.get('endDate')
                    ), None)
                    company_name = active_trade_name_record.get('name', '') if active_trade_name_record else ''
                    if not company_name:
                        continue

                    business_id = item.get('businessId', {}).get('value', '')
                    vat_number = ''
                    registers = item.get('registeredEntries', [])
                    is_vat_registered = next((
                        register for register in registers
                        if register.get('register') == "6" and not register.get('endDate')
                        ), None)
                    if is_vat_registered and business_id and '-' in business_id:
                        clean_bid = business_id.replace('-', '')
                        vat_number = f"FI{clean_bid}"

                    street = ''
                    building_number = ''
                    apartment_number = ''
                    zip_code = ''
                    city = ''
                    addresses = item.get('addresses', [])
                    post_address = next((
                        addr for addr in addresses 
                        if addr.get('type') == 2 and not addr.get('endDate')
                    ), None)
                    if not post_address:
                        post_address = next((
                            addr for addr in addresses 
                            if not addr.get('endDate') and addr.get('type') in [1, 2]
                        ), None)
                    if post_address:
                        street = post_address.get('street', '')
                        building_number = post_address.get('buildingNumber', '')
                        apartment_number = post_address.get('apartmentNumber', '')
                        zip_code = post_address.get('postCode', '')
                        post_offices = post_address.get('postOffices', [])
                        if post_offices:
                            finnish_city = next((p.get('city') for p in post_offices if p.get('languageCode') == '1'), None)
                            city = finnish_city or post_offices[0].get('city', '')

                    website_url = item.get('website', {}).get('url', '')

                    mapped_item = {
                        'name': company_name,
                        'raw_data': {
                            'names': [{'name': company_name}],
                            'addresses': [{
                                'street': street,
                                'building_number': building_number,
                                'apartment_number': apartment_number,
                                'postcode': zip_code,
                                'city': city
                            }],
                            'business_id_value': business_id,
                            'vat_id_value': vat_number,
                            'website': website_url,
                        }
                    }
                    results.append(mapped_item)
            return results
        except requests.exceptions.HTTPError as e:
            return []
        except Exception as e:
            return []