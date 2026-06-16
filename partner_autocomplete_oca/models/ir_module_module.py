from odoo import models, _
from odoo.exceptions import UserError

class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    def button_immediate_install(self):
        conflicting_module_name = 'partner_autocomplete'
        
        is_my_module_installed = self.env['ir.module.module'].search([
            ('name', '=', 'partner_autocomplete_oca'),
            ('state', '=', 'installed')
        ], limit=1)

        error_message = _(
            "MODULE CONFLICT: INSTALLATION PREVENTED\n"
            "The module '%s' cannot be installed because it is incompatible with your already installed module '%s'."
            "\n\n"
            "NOTE ON COMPATIBILITY: Installing the Odoo official Partner Autocomplete module will override the functionality of %s. "
            "Please uninstall this custom module first before attempting to install the official one."
            ) % (conflicting_module_name, is_my_module_installed.name, is_my_module_installed.display_name)

        if self.name == conflicting_module_name and is_my_module_installed:
            raise UserError(error_message)
        
        return super(IrModuleModule, self).button_immediate_install()