# Copyright 2017 Oy Tawasta OS Technologies Ltd.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    business_code = fields.Char(
        string="Business ID",
    )

    same_business_code_partner_id = fields.Many2one(
        "res.partner",
        string="Partner with the same Business ID",
        compute="_compute_same_business_code_partner_id",
        store=False,
    )

    def _commercial_fields(self):
        return super()._commercial_fields() + ["business_code"]

    @api.depends("business_code")
    def _compute_same_business_code_partner_id(self):
        # Check if a company with this business code already exists
        for partner in self:
            # use _origin to deal with onchange()
            partner_id = partner._origin.id
            domain = [("business_code", "=", partner.business_code)]
            if partner_id:
                domain += [
                    ("id", "!=", partner_id),
                    "!",
                    ("id", "child_of", partner_id),
                ]
            partner.same_business_code_partner_id = (
                bool(partner.business_code)
                and not partner.parent_id
                and self.env["res.partner"].search(domain, limit=1)
            )
