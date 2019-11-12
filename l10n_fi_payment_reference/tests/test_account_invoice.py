from odoo.tests import common


class TestAccountInvoiceCommon(common.TransactionCase):

    def setUp(self):
        super(TestAccountInvoiceCommon, self).setUp()

        env = self.env
        get_res_id = env["ir.model.data"].xmlid_to_res_id
        user_ctx = {
            "no_reset_password": True,
            "mail_create_nosubscribe": True,
            "tracking_disable": True,
        }
        user_model = env["res.users"].with_context(**user_ctx)
        self.company = env.user.company_id

        # create billing user
        account_group_id = get_res_id("account.group_account_invoice")
        account_user_vals = {
            "name": "Test User With Right For Account",
            "login": "account.user@example.com",
            "email": "account.user@example.com",
            "notification_type": "inbox",
            "groups_id": [(4, account_group_id)],
        }
        account_user = user_model.create(account_user_vals)
        uid = account_user.id
        self.account_uid = uid

        # create out invoice invoice

        # create product
        product_vals = {
            "name": "Test Product Name",
        }
        product_tmpl = env["product.template"].create(product_vals)
        product = product_tmpl.product_variant_ids[0]

        # create payment term
        payment_term_vals = {
            "name": "Test Payment Term",
        }
        payment_term = env["account.payment.term"].create(payment_term_vals)

        # prepare invoice line data
        tax = env["account.tax"].create({
            "name": "Tax 15.0",
            "amount": 15.0,
            "amount_type": "percent",
            "type_tax_use": "sale",
        })

        line_account_type_id = get_res_id("account.data_account_type_revenue")
        line_account = env["account.account"].search(
            [("user_type_id", "=", line_account_type_id)],
            limit=1,
        )

        inv_line_vals = {
            "product_id": product.id,
            "name": "Test Invoice Line",
            "quantity": 5.0,
            "price_unit": 750,
            "account_id": line_account.id,
            "invoice_line_tax_ids": [(6, 0, [tax.id])],
        }

        # prepare invoice data
        inv_partner = account_user.partner_id
        inv_journal = env["account.journal"].search(
            [("type", "=", "sale")],
            limit=1,
        )
        inv_vals = {
            "partner_id": inv_partner.id,
            "account_id": inv_partner.property_account_payable_id.id,
            "reference_type": "none",
            "payment_term_id": payment_term.id,
            "journal_id": inv_journal.id,
            "type": "out_invoice",
            "invoice_line_ids": [(0, 0, inv_line_vals)],
        }
        out_invoice = env["account.invoice"].sudo(uid).create(inv_vals)
        out_invoice.invoice_line_ids._onchange_product_id()
        self.out_invoice = out_invoice


class TestAccountInvoice(TestAccountInvoiceCommon):

    def test_010_test_fi_ref_creation_on_invoice_validate(self):
        """
        Finnish Payment Reference generated on invoice validation when
        company reference type is "Finnish"
        """

        self.company.payment_reference_type = "fi"

        invoice = self.out_invoice.sudo(self.account_uid)
        invoice.action_date_assign()
        invoice.action_move_create()
        invoice.invoice_validate()

        self.assertEqual(
            invoice.payment_reference,
            invoice._compute_payment_reference_fi(invoice.number),
        )

    def test_020_test_rf_ref_creation_on_invoice_validate(self):
        """
        RF Payment Reference generated on invoice validation if company
        reference type is "RF"
        """

        self.company.payment_reference_type = "rf"

        invoice = self.out_invoice.sudo(self.account_uid)
        invoice.action_date_assign()
        invoice.action_move_create()
        invoice.invoice_validate()

        self.assertEqual(
            invoice.payment_reference,
            invoice._compute_payment_reference_rf(invoice.number),
        )
