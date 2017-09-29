# -*- coding: utf-8 -*-
# Copyright 2017 Oy Tawasta OS Technologies Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResPartnerIdNumber(models.Model):
    _inherit = 'res.partner.id_number'


