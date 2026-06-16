from odoo import http
from odoo.http import request

class OCAAutocompleteController(http.Controller):

    @http.route('/partner_autocomplete_oca/search_company_data', type='json', auth='user', methods=['POST'])
    def search_company_data(self, **kwargs):
        query = kwargs.get('query','')
        current_country_id = kwargs.get('country_id')

        if not query:
            return []
        
        backend = None

        if current_country_id:
            backend = request.env['autocomplete.backend'].sudo().search([
                ('default_country_id', '=', current_country_id),
                ('company_id', '=', request.env.company.id)
            ], limit=1)
            
            if not backend:
                return []

        if not backend:
            backend = request.env['autocomplete.backend'].sudo().search([
                ('is_country_active', '=', True), 
                ('company_id', '=', request.env.company.id)
            ], limit=1)
            
            if not backend:
                return []

        country_code = backend.default_country_id.code
        api_key = backend.api_key
        env_type = backend.country_environment_id.environment_type

        return self._search_for_country(country_code, query, api_key, env_type)

    def _search_for_country(self, country_code, query, api_key, env_type):
        return []