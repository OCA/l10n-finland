from odoo.tests.common import TransactionCase


class TestAccountEdiFormat(TransactionCase):

    def setUp(self):
        super().setUp()

    def test_get_edi_decoder(self):
        """
        Test getting the correct decoder for Finvoice
        """
        # TODO
        return True
    
    def test_is_finvoice(self):
        """
        Test that the xml is identified as Finvoice
        """
        # TODO
        return True

    def test_import_finvoice(self):
        """
        Test that the import function works and creates an invoice
        """

        # TODO
        return True
    
    def test_lookup_partner_by_vat_or_business_code(self):
        """
        Test that the correct partner is found by VAT or business code
        """

        # TODO
        return True