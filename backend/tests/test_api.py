from django.test import SimpleTestCase, override_settings
from unittest.mock import patch


class ApiSmoke(SimpleTestCase):
    def test_checkout_quote_updates_for_cart_coupon_cep_and_shipping_mode(self):
        self.client.post("/api/cart/items/", {"id": "PH-004", "quantidade": 1}, content_type="application/json")
        first = self.client.post("/api/shipping/", {"cep": "01001-000", "modalidade_frete": "economica"}, content_type="application/json").json()

        self.client.post("/api/cart/items/", {"id": "PH-005", "quantidade": 2}, content_type="application/json")
        with_more_items = self.client.get("/api/session/").json()["cart"]
        self.assertGreater(with_more_items["subtotal_centavos"], first["subtotal_centavos"])
        self.assertEqual(len(with_more_items["items"]), 2)

        with_coupon = self.client.post("/api/coupon/", {"codigo": "PROHALL10"}, content_type="application/json").json()
        self.assertEqual(with_coupon["cupom"], "PROHALL10")
        self.assertGreater(with_coupon["desconto_cupom_centavos"], 0)
        self.assertLess(with_coupon["base_produtos_centavos"], with_more_items["base_produtos_centavos"])

        new_cep = self.client.post("/api/shipping/", {"cep": "69005-000", "modalidade_frete": "economica"}, content_type="application/json").json()
        self.assertEqual(new_cep["frete"]["zona"], "Z5")
        self.assertNotEqual(new_cep["valor_frete_centavos"], with_coupon["valor_frete_centavos"])

        express = self.client.post("/api/shipping/", {"cep": "69005-000", "modalidade_frete": "expressa"}, content_type="application/json").json()
        self.assertEqual(express["modalidade_frete"], "expressa")
        self.assertGreater(express["valor_frete_centavos"], new_cep["valor_frete_centavos"])
        self.assertEqual(express["total_pix_centavos"], express["base_produtos_centavos"] - express["desconto_pix_centavos"] + express["valor_frete_centavos"])

    def test_debug_tools_lists_all_calls_and_arguments_without_results(self):
        from commerce.service import get_session

        response = self.client.get("/api/session/")
        session = get_session(response.cookies["sofia_session"].value)
        session["debug"] = [{"name": "buscar_produtos", "args": {"termo": str(index)}, "result": {"internal": True}} for index in range(31)]
        debug = self.client.get("/api/debug/tools/")
        self.assertEqual(debug.status_code, 200)
        self.assertEqual(len(debug.json()["calls"]), 31)
        self.assertEqual(debug.json()["calls"][-1], {"name": "buscar_produtos", "args": {"termo": "30"}})

    def test_catalog_cart_checkout_pix_and_swagger_without_database(self):
        products = self.client.get("/api/products/")
        self.assertEqual(products.status_code, 200)
        self.assertEqual(len(products.json()), 15)
        self.assertEqual(self.client.get("/api/docs/").status_code, 200)
        self.assertEqual(self.client.get("/api/schema/").status_code, 200)
        cart = self.client.post("/api/cart/items/", {"id": "PH-004", "quantidade": 1}, content_type="application/json")
        self.assertEqual(cart.status_code, 200)
        self.assertEqual(cart.json()["items"][0]["id"], "PH-004")
        self.assertEqual(self.client.post("/api/shipping/", {"cep": "01001-000"}, content_type="application/json").status_code, 200)
        express = self.client.post("/api/shipping/", {"cep": "01001-000", "modalidade_frete": "expressa"}, content_type="application/json")
        self.assertEqual(express.status_code, 200)
        self.assertEqual(express.json()["modalidade_frete"], "expressa")
        self.assertEqual(express.json()["valor_frete_centavos"], express.json()["frete"]["opcoes"]["expressa"]["valor_centavos"])
        data = {"nome": "Ana Teste", "email": "ana@example.com", "cep": "01001-000", "endereco": "Rua Exemplo", "numero": "10", "modalidade_frete": "economica"}
        order = self.client.post("/api/orders/", data, content_type="application/json")
        self.assertEqual(order.status_code, 201)
        order_id = order.json()["id"]
        pix = self.client.post(f"/api/orders/{order_id}/pix/")
        self.assertEqual(pix.status_code, 200)
        self.assertTrue(pix.json()["qr_data_url"].startswith("data:image/png;base64,"))
        self.assertEqual(self.client.post(f"/api/orders/{order_id}/simulate-payment/").json()["status"], "pago")

    @override_settings(GEMINI_API_KEY="")
    def test_chat_requires_backend_key(self):
        response = self.client.post("/api/chat/", {"message": "Oi"}, content_type="application/json")
        self.assertEqual(response.status_code, 503)
        self.assertIn("GEMINI_API_KEY", response.json()["detail"])

    def test_chat_exposes_order_created_by_tool_call(self):
        self.client.post("/api/cart/items/", {"id": "PH-004"}, content_type="application/json")

        def simulated_tool_chat(session, message):
            from commerce.service import finalize_order, generate_pix
            order = finalize_order(session, {"nome": "Ana Teste", "email": "ana@example.com", "cep": "01001-000", "endereco": "Rua Exemplo", "numero": "10", "modalidade_frete": "economica"})
            generate_pix(session, order["id"])
            return {"text": "Seu PIX de teste está pronto.", "cards": [], "debug": []}

        with patch("api.views.chat", side_effect=simulated_tool_chat):
            response = self.client.post("/api/chat/", {"message": "Pode fechar"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["active_order"]["qr_data_url"].startswith("data:image/png;base64,"))
        self.assertTrue(response.json()["active_order"]["pix"]["texto"].endswith("|NAO-PAGAVEL"))
        self.assertIn("aguardando pagamento", response.json()["text"])
        self.assertIn("Gostaria de simular o pagamento?", response.json()["text"])
        self.assertNotIn("sucesso", response.json()["text"].lower())

    def test_chat_exposes_checkout_preview_before_order(self):
        self.client.post("/api/cart/items/", {"id": "PH-004", "quantidade": 2}, content_type="application/json")

        def simulated_preview(session, message):
            from commerce.service import prepare_checkout
            preview = prepare_checkout(session, {"nome": "Ana Teste", "email": "ana@example.com", "cep": "01001-000", "endereco": "Rua Exemplo", "numero": "10"})
            return {"text": "Você prefere Econômico ou Expresso?", "cards": [], "debug": [{"name": "preparar_checkout", "args": {}, "result": preview}]}

        with patch("api.views.chat", side_effect=simulated_preview):
            response = self.client.post("/api/chat/", {"message": "Pode fechar"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["active_order"])
        self.assertEqual(response.json()["checkout_preview"]["cliente"]["nome"], "Ana Teste")
        self.assertEqual(response.json()["checkout_preview"]["resumo"]["items"][0]["quantidade"], 2)
        self.assertIn("Frete Econômico:", response.json()["text"])
        self.assertIn("Total do pedido no PIX:", response.json()["text"])
        self.assertEqual(self.client.get("/api/session/").json()["messages"][-1]["checkout_preview"]["cliente"]["cep"], "01001000")

    def test_checkout_message_shows_free_shipping_as_zero(self):
        from api.views import checkout_message
        from commerce.service import add_item, new_session, prepare_checkout

        session = new_session()
        add_item(session, "PH-001", 4)
        preview = prepare_checkout(session, {"nome": "Victor Teste", "email": "victor@example.com", "cep": "18000-000", "endereco": "Rua X", "numero": "123"})
        message = checkout_message(preview)
        self.assertIn("Frete Econômico: R$ 0,00 (grátis)", message)
        self.assertIn("Total do pedido no PIX: R$ 1.025,62", message)
        self.assertIn("Frete Expresso: R$ 47,90", message)
        self.assertNotIn("Grátis se refere", message)
