from django.test import SimpleTestCase
from unittest.mock import patch


class ApiSmoke(SimpleTestCase):
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
