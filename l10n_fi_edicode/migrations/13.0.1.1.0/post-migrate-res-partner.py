def migrate(cr, version):
    # update new `einvoice_operator` column with the temporary one
    cr.execute(
        """
            UPDATE
                res_partner
            SET
                einvoice_operator_id = temporary_einvoice_operator
            WHERE
                temporary_einvoice_operator IS NOT NULL
        """,
    )
    # Drop temporary column
    cr.execute(
        """
            ALTER TABLE
                res_partner
            DROP COLUMN
                temporary_einvoice_operator
        """,
    )
