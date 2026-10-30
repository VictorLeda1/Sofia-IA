from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from google.genai import types

from commerce.service import new_session
from sofia_ai.agent import chat, trim_history


class GeminiToolLoop(SimpleTestCase):
    def test_history_keeps_function_calls_with_their_responses(self):
        history = []
        for index in range(12):
            history.extend([
                types.Content(role="user", parts=[types.Part.from_text(text=f"Mensagem {index}")]),
                types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(name="ver_carrinho", args={}, id=str(index)))]),
                types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(name="ver_carrinho", response={"result": {}}, id=str(index)))]),
                types.Content(role="model", parts=[types.Part.from_text(text="Resposta")]),
            ])

        kept = trim_history(history)
        self.assertEqual(len(kept), 40)
        self.assertEqual(kept[0].parts[0].text, "Mensagem 2")
        self.assertEqual(trim_history(history[:-1])[0].parts[0].text, "Mensagem 2")
        self.assertEqual(trim_history(history[2:10])[0].parts[0].text, "Mensagem 1")

    @override_settings(GEMINI_API_KEY="chave-ficticia", GEMINI_MODEL="gemini-3.8-flash")
    def test_function_call_uses_catalog_and_preserves_response_id(self):
        calls = []

        def generate_content(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                content = types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(name="detalhar_produto", args={"id": "PH-003"}, id="chamada-1"))])
            else:
                content = types.Content(role="model", parts=[types.Part.from_text(text="Para controlar o frizz sem secador, conheça o Secar sem Frizz.")])
            return SimpleNamespace(candidates=[SimpleNamespace(content=content)])

        fake_client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        with patch("sofia_ai.agent.genai.Client", return_value=fake_client):
            session = new_session()
            result = chat(session, "Quero controlar o frizz em casa")

        self.assertEqual(len(calls), 2)
        self.assertEqual(result["cards"][0]["id"], "PH-003")
        response_part = calls[1]["contents"][-2].parts[0].function_response
        self.assertEqual(response_part.id, "chamada-1")
        self.assertEqual(response_part.response["result"]["id"], "PH-003")
        self.assertEqual(result["debug"][0]["name"], "detalhar_produto")
