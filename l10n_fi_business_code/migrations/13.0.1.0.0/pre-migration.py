from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    # Rename business_id to business_code
    openupgrade.rename_fields(
        env, [("res.partner", "res_partner", "business_id", "business_code",)],
    )
