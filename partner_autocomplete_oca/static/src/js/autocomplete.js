/** @odoo-module */
/** @depends web.web **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class PartnerAutocompleteOCA extends Component {
    static template = "partner_autocomplete_oca.PartnerAutocompleteOCA";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        super.setup();
        this.state = useState({
            results: [],
            showResults: false,
            inputValue: this.props.value || '',
        });

        this.searchTimeout = null;
        this.preventBlur = false;

        onWillStart(async () => {
            const initialValue = this.props.record.data[this.props.name] || '';
            this.state.inputValue = initialValue;
        });
        
        onWillUpdateProps((nextProps) => {
            const nextModelValue = nextProps.record.data[nextProps.name] || '';
            if (nextModelValue !== this.state.inputValue) {
                this.state.inputValue = nextModelValue || '';
            }
        });
        
        this.discardListener = this.onDiscardEvent.bind(this);
        this.env.bus.addEventListener('oca-autocomplete-discard', this.discardListener);
    }

    onInput(ev) {
        const query = ev.target.value;
        this.state.inputValue = query;

        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        if (!query || query.length < 3) {
            this.state.showResults = false;
            this.state.results = [];
            return;
        }

        this.searchTimeout = setTimeout(async () => {
            const countryField = this.props.record.data.country_id;
            const current_country_id = countryField ? countryField[0] : false;

            const results = await rpc("/partner_autocomplete_oca/search_company_data", {
                query: query,
                country_id: current_country_id,
            });

            if (results && results.length > 0) {
                results.sort((a, b) => {
                    const nameA = a.name || "";
                    const nameB = b.name || "";
                    return nameA.localeCompare(nameB, undefined, { sensitivity: 'base' });
                });
            }

            if (this.state.inputValue === query && results.length > 0) {
                this.state.results = results;
                this.state.showResults = true;
            } else {
                this.state.results = [];
                this.state.showResults = false;
            }
        }, 300);
    }

    onResultMouseDown(ev) {
        ev.preventDefault();
        this.preventBlur = true;
    }
    
    onResultClick(result) {
        const company = result.raw_data;

        const companyName = company.names?.[0]?.name || result.name || '';

        const toTitleCase = (str) => {
            if (!str) return '';
            return str.toLocaleLowerCase().split(' ').map(word => {return word.charAt(0).toLocaleUpperCase() + word.slice(1);}).join(' ');
        };

        const addressData = company.addresses?.[0];
        const rawStreet = addressData?.street || '';
        let street = toTitleCase(rawStreet);
        const buildingNumber = addressData?.building_number || '';
        const apartmentNumber = addressData?.apartment_number|| '';
        const addressParts = [
            street,
            buildingNumber,
            apartmentNumber
        ];
        const fullStreet = addressParts.filter(part => part).join(' ');
        const rawCity = addressData?.city || '';

        const updateData = {
            [this.props.name]: companyName,
            "street": fullStreet,
            "zip": addressData?.postcode || '',
            "city": toTitleCase(rawCity),
            "company_registry": company.business_id_value || '',
            "vat": company.vat_id_value || '', 
            "website": company.website || '',
        };
        
        this.props.record.update(updateData);
        this.state.inputValue = companyName;
        
        this.state.showResults = false;
        this.state.results = [];

        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = null;
        }

        this.preventBlur = false;
    }

    onBlur() {
        if (this.preventBlur) {
            this.preventBlur = false;
            return;
        }

        if (this.state.showResults) {
            this.state.showResults = false;
        }

        const modelValue = this.props.record.data[this.props.name] || '';

        if (modelValue !== this.state.inputValue) {
             this.props.record.update({ [this.props.name]: this.state.inputValue });
        }
    }

    onDiscardEvent() {
        if (this.props.name in this.props.record.data) {
            const cleanValue = this.props.record.data[this.props.name] || '';
            
            this.state.inputValue = cleanValue;
            this.state.showResults = false;
        }
    }

    willUnmount() {
        this.env.bus.removeEventListener('oca-autocomplete-discard', this.discardListener);
    }
}

export const partnerAutocompleteField = {
    component: PartnerAutocompleteOCA,
    supportedTypes: ["char"],
};

registry.category("fields").add("partner_autocomplete", partnerAutocompleteField);