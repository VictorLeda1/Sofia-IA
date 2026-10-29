from datetime import datetime, timedelta, timezone
from unittest import TestCase

from commerce.service import (
    add_item, apply_coupon, finalize_order, generate_pix, get_order, new_session,
    product_amounts, quote_shipping, remove_item, simulate_payment, totals,
    zone_for_cep,
)


class FreightCases(TestCase):
    def test_all_cases_from_section_5_6(self):
        a = quote_shipping("01310-100", 1200, 25000)
        self.assertEqual((a["zona"], a["peso_cobrado_g"]), ("Z1", 1400))
        self.assertEqual(a["opcoes"]["economica"]["valor_centavos"], 2290)
        self.assertEqual(a["opcoes"]["expressa"]["valor_centavos"], 3590)
        self.assertEqual(a["faltam_frete_gratis_centavos"], 4900)
        self.assertEqual(a["opcoes"]["economica"]["prazo_dias_uteis"], "3 a 5")
        self.assertEqual(a["opcoes"]["expressa"]["prazo_dias_uteis"], "1 a 2")

        b = quote_shipping("69005-000", 6100, 38000)
        self.assertEqual((b["zona"], b["peso_cobrado_g"], b["kg_adicionais"]), ("Z5", 6300, 2))
        self.assertEqual(b["opcoes"]["economica"]["valor_centavos"], 9990)
        self.assertEqual(b["opcoes"]["expressa"]["valor_centavos"], 16190)
        self.assertEqual(b["faltam_frete_gratis_centavos"], 1900)

        c = quote_shipping("40020-000", 800, 42000)
        self.assertEqual((c["zona"], c["faixa"]), ("Z4", "até 1 kg"))
        self.assertEqual(c["opcoes"]["economica"]["valor_centavos"], 0)
        self.assertEqual(c["opcoes"]["expressa"]["valor_centavos"], 5990)
        self.assertEqual(c["opcoes"]["expressa"]["prazo_dias_uteis"], "3 a 6")

        d = quote_shipping("88010-000", 300, 29900)
        self.assertEqual(d["zona"], "Z2")
        self.assertEqual(d["opcoes"]["economica"]["valor_centavos"], 0)
        self.assertEqual(d["opcoes"]["expressa"]["valor_centavos"], 3190)

        e = quote_shipping("76801-000", 4800, 10000)
        self.assertEqual((e["zona"], e["faixa"]), ("Z5", "até 5 kg"))
        self.assertEqual(e["opcoes"]["economica"]["valor_centavos"], 7990)
        self.assertEqual(e["opcoes"]["expressa"]["valor_centavos"], 12990)
        self.assertEqual(e["faltam_frete_gratis_centavos"], 29900)

        self.assertIsNone(zone_for_cep("00000-000"))
        with self.assertRaisesRegex(ValueError, "CEP inválido"):
            quote_shipping("00000-000", 100, 10000)

    def test_total_example_from_section_6_2(self):
        amounts = product_amounts(30000, "PROHALL10")
        self.assertEqual(amounts, {"cupom": "PROHALL10", "desconto_cupom_centavos": 3000, "base_produtos_centavos": 27000, "desconto_pix_centavos": 1350})
        quote = quote_shipping("01310-100", 1200, amounts["base_produtos_centavos"])
        self.assertEqual(quote["faltam_frete_gratis_centavos"], 2900)
        self.assertEqual(27000 - 1350 + quote["opcoes"]["economica"]["valor_centavos"], 27940)


class CartAndOrder(TestCase):
    def test_stock_coupon_removal_and_limits(self):
        session = new_session()
        add_item(session, "PH-010", 2)
        with self.assertRaisesRegex(ValueError, "Estoque"):
            add_item(session, "PH-010", 1)
        add_item(session, "PH-002")
        apply_coupon(session, "PROHALL10")
        self.assertEqual(totals(session)["cupom"], "PROHALL10")
        remove_item(session, "PH-002")
        result = remove_item(session, "PH-010", 1)
        self.assertIsNone(result["cupom"])
        self.assertIn("deixou de valer", result["aviso"])
        with self.assertRaisesRegex(ValueError, "Quantidade"):
            add_item(session, "PH-001", -1)

    def test_checkout_rejects_empty_cep_and_pix_expires(self):
        session = new_session()
        add_item(session, "PH-004")
        data = {"nome": "Ana Teste", "email": "ana@example.com", "cep": "", "endereco": "Rua Exemplo", "numero": "10", "modalidade_frete": "economica"}
        with self.assertRaisesRegex(ValueError, "CEP inválido"):
            finalize_order(session, data)
        self.assertTrue(session["cart"])
        data["cep"] = "01001-000"
        order = finalize_order(session, data)
        self.assertIsInstance(order["resumo"]["total_pix_centavos"], int)
        self.assertFalse(session["cart"])
        pix = generate_pix(session, order["id"])
        self.assertTrue(pix["pix"]["texto"].endswith("|NAO-PAGAVEL"))
        pix["pix"]["expira_em"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        self.assertEqual(get_order(session, order["id"])["status"], "expirado")
        with self.assertRaisesRegex(ValueError, "expirado"):
            simulate_payment(session, order["id"])
        generate_pix(session, order["id"])
        self.assertEqual(simulate_payment(session, order["id"])["status"], "pago")
