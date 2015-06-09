# -*- coding: utf-8 -*-
from openerp.osv import osv, fields

class res_partner(osv.Model):

    _inherit = 'res.partner'

    _columns = {
        'edicode': fields.char(string='Edicode'),
        'einvoice_operator': fields.char(string='eInvoice Operator'),
        'einvoice_operator_identifier': fields.char(string='Operator ID'),
    }