from odoo import fields, models, api

class AutocompleteCountryEnvironment(models.Model):
    _name = "autocomplete.country.environment"
    _description = "Available Environment for Country"
    _rec_name = 'display_name'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    
    country_id = fields.Many2one(
        'res.country', 
        string="Country", 
        required=True,
        ondelete='cascade'
    )

    environment_type = fields.Selection(
        [('free', 'Free: Open Data'), ('paid', "Paid: IODO's Data")],
        string="Environment Type",
        required=True
    )

    display_name = fields.Char(compute='_compute_display_name', store=True)
           
    @api.depends('country_id', 'environment_type')
    def _compute_display_name(self):
        type_labels = dict(self._fields['environment_type'].selection)
        for record in self:
            type_label = type_labels.get(record.environment_type, record.environment_type)
            record.display_name = type_label

    _sql_constraints = [
        ('unique_country_environment', 'unique(country_id, environment_type)', 
         'This environment type is already configured for this country.')
    ]