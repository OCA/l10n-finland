from . import controllers
from . import models

from odoo.exceptions import ValidationError
from odoo import _ 

def before_installation(env):

    partner_autocomplete_installed = env['ir.module.module'].search([
        ('name', '=', 'partner_autocomplete'),
        ('state', '=', 'installed')
    ])
    if partner_autocomplete_installed:
        raise ValidationError("This module conflicts with Odoo's Partner Autocomplete (partner_autocomplete). Please uninstall it first before activating this.")