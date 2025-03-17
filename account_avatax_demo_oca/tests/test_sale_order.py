# Copyright 2025 Kencove, Open Source Integrators
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import json
import logging
import os

from odoo.tests.common import tagged

from odoo.addons.account_avatax_oca.tests.common import TestAvataxCommon

_logger = logging.getLogger(__name__)


@tagged("-at_install", "post_install")
class TestAvataxSaleOrder(TestAvataxCommon):
    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()

        cls.company = cls.env.user.company_id
        cls.company.write(
            {
                "street": "255 Executive Park Blvd",
                "city": "San Francisco",
                "state_id": cls.env.ref("base.state_us_5").id,
                "country_id": cls.env.ref("base.us").id,
                "zip": "94134",
            }
        )

        cls.NT_product = cls.env["product.product"].create(
            {
                "name": "NT Product",
                "list_price": 100,
                "sale_ok": True,
                "tax_code_id": cls.env.ref(
                    "account_avatax_oca.avatax_product_taxcodeNT"
                ).id,
            }
        )

        cls.taxed_product = cls.env["product.product"].create(
            {
                "name": "Taxed Product",
                "list_price": 33,
                "sale_ok": True,
            }
        )

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
                "is_company": True,
                "street": "77 Santa Barbara Rd",
                "city": "Pleasant Hill",
                "state_id": cls.env.ref("base.state_us_5").id,
                "country_id": cls.env.ref("base.us").id,
                "zip": "94523",
            }
        )

        # Create sale order
        cls.order = cls.env["sale.order"].create(
            {
                "company_id": cls.company.id,
                "partner_id": cls.partner.id,
            }
        )
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.order.write(
            {
                "order_line": [
                    (
                        0,
                        False,
                        {
                            "product_id": cls.NT_product.id,
                            "name": "NT Product",
                            "product_uom": cls.uom_unit.id,
                            "product_uom_qty": 1.0,
                        },
                    ),
                    (
                        0,
                        False,
                        {
                            "product_id": cls.taxed_product.id,
                            "name": "Taxed Product",
                            "product_uom": cls.uom_unit.id,
                            "product_uom_qty": 1.0,
                        },
                    ),
                ]
            }
        )

        return res

    def read_json(self, file_name):
        module_path = os.path.dirname(__file__)
        file_path = os.path.join(module_path, file_name)
        with open(file_path) as file:
            data = json.load(file)
            return data

    def test_compute_taxes_for_quotation(self):
        """
        Order:
            -   Order Line 1: NT Product
            -   Order Line 2: Taxed Product
            -   Exemption Code: None
        Expect:
            -   Only order line 2 has tax applied
        """
        so_2_response = self.read_json("SaleOrder_response.json")
        for line in so_2_response["lines"]:
            if line["description"] == "NT Product":
                line["lineNumber"] = self.order.order_line[0].id

            if line["description"] == "Taxed Product":
                line["lineNumber"] = self.order.order_line[1].id

        with self._capture_create_or_adjust_transaction(return_value=so_2_response):
            self.order._avatax_compute_tax()
            for order_line in self.order.order_line:
                if order_line.name == "NT Product":
                    tax_names = order_line.tax_id.mapped("name")
                    self.assertIn(
                        "AVATAX", tax_names, "AVATAX tax not found in Non-Tax Product"
                    )

                if order_line.name == "Taxed Product":
                    tax_names = order_line.tax_id.mapped("name")
                    self.assertTrue(order_line.tax_id)
                    self.assertNotIn(
                        "AVATAX", tax_names, "AVATAX tax found in Taxed Product"
                    )
