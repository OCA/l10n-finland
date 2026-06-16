from odoo import _, fields, models, api
from odoo.tools import sql

class AutocompleteBackend(models.Model):
    _inherit = "connector.backend"
    _name = "autocomplete.backend"
    _description = "Autocomplete Backend"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company.id,
        help="The Company associated with this Autocomplete Backend."
    )

    name = fields.Char(
        string="Name",
        help="Differentiate between your Connections saved in Odoo.",
    )
    
    available_country_ids = fields.Many2many(
        'res.country', 
        compute='_compute_available_countries',
        string="Available Countries",
        store=False
    )

    @api.depends('name', 'company_id')
    def _compute_available_countries(self):
        EnvironmentModel = self.env['autocomplete.country.environment'].sudo()
        grouped_data = EnvironmentModel.read_group(domain=[], fields=['country_id'], groupby=['country_id'])
        country_ids = [data['country_id'][0] for data in grouped_data if data['country_id']]
        for record in self:
            if country_ids:
                record.available_country_ids = [fields.Command.set(country_ids)]
            else:
                record.available_country_ids = False

    default_country_id = fields.Many2one(
        comodel_name="res.country",
        domain="[('id', 'in', available_country_ids)]",
        string="Country",
        required=True,
        help="The specific country configured for this Autocomplete backend. The backend will only return results relevant to this country."
    )
    
    is_country_active = fields.Boolean(
        string="Default",
        default=False,
        help="Sets this backend as the default fallback for OCA's Partner Autocomplete. If no country is specified in the search, this value will be used instead. Only one backend can be set as the active default at any time."
    )

    country_environment_id = fields.Many2one(
        'autocomplete.country.environment',
        string="Environment Type",
        required=True,
        domain="[('country_id', '=', default_country_id)]",
        help="Select the data environment available for the chosen country."
    )
    
    environment_type_code = fields.Selection(
        related='country_environment_id.environment_type',
        string="Environment Type Code",
        readonly=True
    )

    api_key = fields.Char(string="Api Key")

    _sql_constraints = [
        (
            'unique_default_country_id',
            'UNIQUE (default_country_id)',
            'The Default Country must be unique across all Autocomplete Backends. Only one Backend can be set per country.'
        )
    ]

    def init(self):
        index_name_country = self._table + '_single_active_country_id_idx'
        sql.drop_constraint(self._cr, self._table, index_name_country)
        
        self._cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS %s ON %s (default_country_id)
            WHERE is_country_active = TRUE;
        """ % (index_name_country, self._table))

        index_name_active = self._table + '_single_active_backend_idx'
        sql.drop_constraint(self._cr, self._table, index_name_active)

        self._cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS %s ON %s ((1))
            WHERE is_country_active = TRUE;
        """ % (index_name_active, self._table))