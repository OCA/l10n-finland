/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

patch(FormController.prototype, {
    async discard() {
        const result = await super.discard(...arguments);
        this.env.bus.trigger('oca-autocomplete-discard');
        return result;
    }
});