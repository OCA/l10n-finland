def migrate(cr, version):
    # Add temporary `einvoice_operator` partner column
    cr.execute(
        """
            ALTER TABLE
                res_partner
            ADD
                temporary_einvoice_operator int
        """,
    )
    # Sane value from previous column to temporary one
    cr.execute(
        """
            UPDATE
                res_partner
            SET
               temporary_einvoice_operator = einvoice_operator
            WHERE
                einvoice_operator IS NOT NULL
        """,
    )
