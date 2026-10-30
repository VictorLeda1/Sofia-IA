from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from google.genai import types

from commerce.service import new_session
from sofia_ai.agent import chat, trim_history


class GeminiToolLoop(SimpleTestCase):
    @override_settings(GEMINI_API_KEY="chave-ficticia", GEMINI_MODEL="gemini-3.8-flash")
    def test_blond_with_highlights_asks_application_then_fragility_separately(self):
        calls = []

        def generate_content(**kwargs):
            calls.append(kwargs)
            instruction = kwargs["config"].system_instruction
            self.assertIn("Para \"tenho cabelo loiro com luzes e quero alisar\"", instruction)
            self.assertIn("não faça essas duas perguntas juntas", instruction)
            answer = (
                "Para orientar com segurança: a aplicação será em casa ou com profissional?"
                if len(calls) == 1 else
                "Entendi. Seus fios estão fragilizados ou quebradiços?"
            )
            return SimpleNamespace(candidates=[SimpleNamespace(content=types.Content(role="model", parts=[types.Part.from_text(text=answer)]))])

        fake_client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        with patch("sofia_ai.agent.genai.Client", return_value=fake_client):
            session = new_session()
            first = chat(session, "Tenho cabelo loiro com luzes, muito frizz e quero alisar.")
            second = chat(session, "Com um profissional.")

        self.assertEqual(first["text"].count("?"), 1)
        self.assertIn("casa ou com profissional?", first["text"])
        self.assertNotIn("fragilizados", first["text"])
        self.assertEqual(second["text"].count("?"), 1)
        self.assertIn("fragilizados ou quebradiços?", second["text"])
        self.assertNotIn("casa ou com profissional", second["text"])

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
