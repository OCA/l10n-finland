import logging

import odoo

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("Copy the first business id from partner categories")
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    cr.execute(
        """
    UPDATE res_partner AS p
    SET business_code = i.name
    FROM
      (SELECT num.partner_id, num.name
       FROM res_partner_id_number AS num
       INNER JOIN res_partner_id_category AS cat
       ON cat.id = num.category_id AND cat.code = 'business_id') AS i
    WHERE p.id = i.partner_id
    RETURNING id;
    """
    )
    partner_ids = [x[0] for x in cr.fetchall()]
    partners = env["res.partner"].browse(partner_ids)

    for partner in partners:
        partner._commercial_sync_to_children()

    _logger.info("Delete legacy business id values from partner identification")
    cr.execute(
        """
    DELETE FROM res_partner_id_number
    WHERE category_id =
    (SELECT id FROM res_partner_id_category WHERE code = 'business_id');
    """
    )
