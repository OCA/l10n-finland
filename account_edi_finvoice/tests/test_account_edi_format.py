from odoo.tests.common import TransactionCase


class TestAccountEdiFormat(TransactionCase):
    def setUp(self):
        super().setUp()

    def test_get_move_applicability(self):
        """
        Test that the EDI format correctly identifies applicable moves.
        If code = "finvoice", it should return Finvoice-functions
        """

        # TODO
        return True

    def test_post_invoice_edi_finvoice(self):
        """
        Test that EDI invoie posting works with Finvoice.
        """

        # TODO
        return True

    def test_cancel_invoice_edi_finvoice(self):
        """
        Test that EDI invoice cancellation works with Finvoice.
        """

        # TODO
        return True

    def test_edi_content_invoice_edi_finvoice(self):
        """
        Test that a sane XML is generated
        """

        # TODO
        return True

    def test_get_finvoice_values(self):
        """
        Test that the correct default values are retrieved
        """

        # TODO
        return True

    def test_export_finvoice(self):
        """
        Test that the export function works and generates an attachment
        """

        # TODO
        return True

    def test_is_compatible_with_journal(self):
        """
        Test that correct journal type is returned
        """

        # TODO
        return True

    def test_finvoice_get_xml_schema(self):
        """
        Test that the correct XML schema is returned
        """

        # TODO
        return True

    def test_finvoice_check_xml_schema(self):
        """
        Test that the XML schema check works
        """

        # TODO
        return True

    def test_create_invoice_from_xml_tree(self):
        """
        Test that an invoice can be imported from Finvoice XML
        """

        # TODO
        return True

    def test_update_invoice_from_xml_tree(self):
        """
        Test that an invoice can be updated from Finvoice XML
        """

        # TODO
        return True

    def test_find_attribute(self):
        """
        Test that the find attribute function works
        """

        # TODO
        return True

    def test_find_values_joined(self):
        """
        Test that the find values joined function works
        """

        # TODO
        return True

    def test_get_invoice_type(self):
        """
        Test that the correct invoice type is returned
        """

        # TODO
        return True

    def test_to_float(self):
        """
        Test that the strings are converted to float correctly
        """

        # TODO
        return True

    def test_retrieve_bank_account(self):
        """
        Test that the bank account retrieval works
        """

        # TODO
        return True
