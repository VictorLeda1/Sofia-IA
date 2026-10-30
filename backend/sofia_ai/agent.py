"""Integração Gemini e function calling. Nenhum cálculo comercial ocorre aqui."""

from pathlib import Path

from django.conf import settings
from google import genai
from google.genai import types

from catalog.service import PRODUCTS, detail_product, search_products
from commerce.service import (
    add_item, apply_coupon, cart_summary, confirm_shipping_and_generate_pix,
    finalize_order, generate_pix, get_order, prepare_checkout,
    quote_shipping, remove_item, totals,
)

PROMPT = (Path(__file__).parent / "prompt.md").read_text(encoding="utf-8")


def declaration(name, description, properties=None, required=None):
    return {"name": name, "description": description, "parameters": {"type": "OBJECT", "properties": properties or {}, "required": required or []}}


def string(description):
    return {"type": "STRING", "description": description}


def integer(description):
    return {"type": "INTEGER", "description": description}


TOOLS = [
    declaration("buscar_produtos", "Busca resumos dos produtos do catálogo.", {"termo": string("Problema ou nome"), "categoria": string("Categoria exata se conhecida"), "uso": string("profissional ou home_care")}),
    declaration("detalhar_produto", "Retorna a ficha completa e verificável do produto.", {"id": string("ID PH-001 a PH-015")}, ["id"]),
    declaration("adicionar_ao_carrinho", "Adiciona unidades com validação de estoque e limite.", {"id": string("ID do produto"), "quantidade": integer("Número inteiro de unidades")}, ["id", "quantidade"]),
    declaration("remover_do_carrinho", "Remove todas ou algumas unidades.", {"id": string("ID do produto"), "quantidade": integer("Quantidade opcional")}, ["id"]),
    declaration("ver_carrinho", "Consulta itens, subtotal, cupom, base e peso do carrinho."),
    declaration("aplicar_cupom", "Valida e aplica o cupom informado.", {"codigo": string("Código da cliente")}, ["codigo"]),
    declaration("calcular_frete", "Calcula opções e prazos de frete usando o carrinho atual.", {"cep": string("CEP com 8 dígitos")}, ["cep"]),
    declaration("preparar_checkout", "Valida os dados de entrega, guarda um rascunho e devolve subtotal, descontos, total e os dois fretes; ainda não cria pedido. Use antes de perguntar a modalidade.", {"nome": string("Nome"), "email": string("E-mail"), "cep": string("CEP"), "endereco": string("Endereço"), "numero": string("Número"), "complemento": string("Complemento opcional")}, ["nome", "email", "cep", "endereco", "numero"]),
    declaration("confirmar_frete", "Depois que a cliente escolhe Econômico ou Expresso, fecha o rascunho e gera automaticamente o PIX falso. Não chame antes da escolha explícita.", {"modalidade_frete": string("economica ou expressa")}, ["modalidade_frete"]),
    declaration("finalizar_pedido", "Cria pedido de teste após receber os dados de entrega da cliente.", {"nome": string("Nome"), "email": string("E-mail"), "cep": string("CEP"), "endereco": string("Endereço"), "numero": string("Número"), "complemento": string("Complemento opcional"), "modalidade_frete": string("economica ou expressa")}, ["nome", "email", "cep", "endereco", "numero", "modalidade_frete"]),
    declaration("gerar_pix", "Gera PIX obviamente falso para um pedido da sessão.", {"pedido_id": string("ID do pedido")}, ["pedido_id"]),
    declaration("consultar_pedido", "Consulta status do pedido e expiração do PIX.", {"pedido_id": string("ID do pedido")}, ["pedido_id"]),
]


def execute_tool(session, name, args, card_ids):
    if not isinstance(args, dict):
        raise ValueError("Argumentos inválidos.")
    if name == "buscar_produtos":
        return search_products(args.get("termo"), args.get("categoria"), args.get("uso"))[:8]
    if name == "detalhar_produto":
        product = detail_product(args.get("id"))
        card_ids[product["id"]] = None
        return product
    if name == "adicionar_ao_carrinho":
        return add_item(session, args.get("id"), args.get("quantidade"))
    if name == "remover_do_carrinho":
        return remove_item(session, args.get("id"), args.get("quantidade"))
    if name == "ver_carrinho":
        return totals(session)
    if name == "aplicar_cupom":
        return apply_coupon(session, args.get("codigo"))
    if name == "calcular_frete":
        cart = cart_summary(session)
        if not cart["items"]:
            raise ValueError("Adicione um produto antes de calcular o frete.")
        quote = quote_shipping(args.get("cep"), cart["peso_itens_g"], cart["base_produtos_centavos"])
        session["cep"] = quote["cep"]
        return quote
    if name == "preparar_checkout":
        return prepare_checkout(session, args)
    if name == "confirmar_frete":
        return confirm_shipping_and_generate_pix(session, args.get("modalidade_frete"))
    if name == "finalizar_pedido":
        return finalize_order(session, args)
    if name == "gerar_pix":
        return generate_pix(session, args.get("pedido_id"))
    if name == "consultar_pedido":
        return get_order(session, args.get("pedido_id"))
    raise ValueError("Ferramenta desconhecida.")


def trim_history(history, limit=40):
    """Mantém turnos completos para não separar uma chamada de sua resposta."""
    if not history:
        return []

    def user_message(content):
        return content.role == "user" and any(part.text is not None for part in content.parts or [])

    start = max(0, len(history) - limit)
    while start < len(history) and not user_message(history[start]):
        start += 1
    if start == len(history):
        start = next((i for i in range(len(history) - 1, -1, -1) if user_message(history[i])), len(history))
    return history[start:]


def chat(session, message):
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY ainda não foi configurada no backend.")
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    summary = "\n".join(f"{p['id']}: {p['nome']}; uso {p['uso']}; {', '.join(p['indicado_para'])}" for p in PRODUCTS)
    current = totals(session)
    session_context = {
        "itens_carrinho": [{"id": p["id"], "quantidade": p["quantidade"]} for p in current["items"]],
        "cupom": current["cupom"], "cep": session["cep"],
        "checkout_preparado": bool(session.get("checkout_draft")),
        "pedidos": [{"id": order["id"], "status": get_order(session, order["id"])["status"]} for order in session["orders"].values()],
    }
    contents = [*trim_history(session["history"]), types.Content(role="user", parts=[types.Part.from_text(text=message)])]
    cards = {}
    debug = []
    for _ in range(10):
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=f"{PROMPT}\n\nCATÁLOGO RESUMIDO (confirme fatos com detalhar_produto):\n{summary}\n\nESTADO ATUAL DA SESSÃO (valores monetários devem ser consultados nas ferramentas):\n{session_context}",
                temperature=0.3,
                tools=[types.Tool(function_declarations=[types.FunctionDeclaration(**item) for item in TOOLS])],
            ),
        )
        if not response.candidates or not response.candidates[0].content:
            raise RuntimeError("O Gemini não retornou resposta utilizável.")
        candidate = response.candidates[0].content
        contents.append(candidate)  # Preserva thought signatures nas chamadas seguintes.
        calls = [part.function_call for part in candidate.parts or [] if part.function_call]
        if not calls:
            answer = "".join(part.text or "" for part in candidate.parts or []).strip()
            if not answer:
                raise RuntimeError("O Gemini retornou uma resposta vazia.")
            session["history"] = trim_history(contents)
            session["debug"].extend(debug)
            return {"text": answer, "cards": [detail_product(product_id) for product_id in list(cards)[:3]], "debug": debug}
        tool_parts = []
        for call in calls:
            args = dict(call.args or {})
            try:
                result = execute_tool(session, call.name, args, cards)
            except (ValueError, TypeError, KeyError) as exc:
                result = {"error": str(exc)}
            debug.append({"name": call.name, "args": args, "result": result})
            tool_parts.append(types.Part(function_response=types.FunctionResponse(name=call.name, response={"result": result}, id=call.id)))
        contents.append(types.Content(role="user", parts=tool_parts))
    raise RuntimeError("A Sofia fez muitas chamadas de ferramenta; tente continuar a conversa.")
