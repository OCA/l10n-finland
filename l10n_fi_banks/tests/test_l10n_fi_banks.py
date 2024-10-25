# Copyright 2024 ForgeFlow
# @author: Jordi Masvidal <jordi.masvidal@forgeflow.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests import common


class TestL10nFIBanks(common.TransactionCase):
    """Simple test for the CI"""

    def test_bank_created(self):
        """Test bank data is created"""
        self.assertTrue(self.env.ref("l10n_fi_banks.res_bank_HELSFIHH").exists())
