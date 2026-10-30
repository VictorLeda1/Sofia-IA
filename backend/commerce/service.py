"""Regras determinísticas do teste. Todos os valores monetários são centavos."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from threading import RLock
from uuid import uuid4
import re

from catalog.service import BY_ID, current_price_cents

_lock = RLock()
_sessions = {}


def new_session():
    return {"id": str(uuid4()), "cart": {}, "coupon": None, "cep": None, "shipping_mode": "economica", "checkout_draft": None, "orders": {}, "history": [], "messages": [], "debug": []}


def get_session(session_id=None):
    with _lock:
        if session_id and session_id in _sessions:
            return _sessions[session_id]
        session = new_session()
        _sessions[session["id"]] = session
        return session


def round_percent(cents, percent):
    return int((Decimal(cents) * Decimal(str(percent)) / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def money(cents):
    return f"R$ {cents // 100:,}".replace(",", ".") + f",{cents % 100:02d}"


def zone_for_cep(raw):
    if not isinstance(raw, str) or not re.fullmatch(r"\d{5}-?\d{3}", raw):
        return None
    n = int(raw.replace("-", ""))
    if 1_000_000 <= n <= 19_999_999 or 30_000_000 <= n <= 39_999_999:
        return "Z1"
    if 20_000_000 <= n <= 29_999_999 or 80_000_000 <= n <= 89_999_999:
        return "Z2"
    if 70_000_000 <= n <= 76_799_999 or 78_000_000 <= n <= 79_999_999 or 90_000_000 <= n <= 99_999_999:
        return "Z3"
    if 40_000_000 <= n <= 65_999_999:
        return "Z4"
    if 66_000_000 <= n <= 69_999_999 or 76_800_000 <= n <= 77_999_999:
        return "Z5"
    return None


# F1, F2, F3, F4, adicional por kg, prazo em dias úteis.
FREIGHT = {
    "Z1": {"economica": (1590, 1890, 2290, 2990, 350, "3 a 5"), "expressa": (2490, 2990, 3590, 4790, 550, "1 a 2")},
    "Z2": {"economica": (1990, 2390, 2890, 3890, 450, "4 a 7"), "expressa": (3190, 3890, 4690, 6290, 700, "2 a 3")},
    "Z3": {"economica": (2490, 2990, 3690, 4990, 600, "5 a 9"), "expressa": (3990, 4890, 5990, 8290, 950, "2 a 4")},
    "Z4": {"economica": (2990, 3690, 4590, 6490, 800, "7 a 12"), "expressa": (4990, 5990, 7490, 10490, 1300, "3 a 6")},
    "Z5": {"economica": (3490, 4290, 5490, 7990, 1000, "9 a 15"), "expressa": (5990, 7290, 8990, 12990, 1600, "4 a 8")},
}


def quote_shipping(cep, items_weight_g, base_cents):
    zone = zone_for_cep(cep)
    if not zone:
        raise ValueError("CEP inválido. Informe 8 dígitos de uma faixa atendida, com ou sem hífen.")
    if not isinstance(items_weight_g, int) or items_weight_g < 0 or not isinstance(base_cents, int) or base_cents < 0:
        raise ValueError("Peso ou valor inválido.")
    charged = items_weight_g + 200
    band = 0 if charged <= 500 else 1 if charged <= 1000 else 2 if charged <= 2000 else 3 if charged <= 5000 else 4
    extra_kg = (charged - 5000 + 999) // 1000 if band == 4 else 0
    threshold = 29900 if zone in ("Z1", "Z2") else 39900
    options = {}
    for mode in ("economica", "expressa"):
        row = FREIGHT[zone][mode]
        standard = row[band] if band < 4 else row[3] + extra_kg * row[4]
        free = mode == "economica" and base_cents >= threshold
        options[mode] = {"valor_centavos": 0 if free else standard, "prazo_dias_uteis": row[5], "gratis": free}
    return {"cep": cep.replace("-", ""), "zona": zone, "peso_cobrado_g": charged, "faixa": ("até 0,5 kg", "até 1 kg", "até 2 kg", "até 5 kg", "acima de 5 kg")[band], "kg_adicionais": extra_kg, "limite_frete_gratis_centavos": threshold, "faltam_frete_gratis_centavos": max(0, threshold - base_cents), "opcoes": options}


def product_amounts(subtotal, coupon=None):
    if not isinstance(subtotal, int) or subtotal < 0:
        raise ValueError("Subtotal inválido.")
    valid_coupon = coupon == "PROHALL10" and subtotal >= 15000
    discount = round_percent(subtotal, 10) if valid_coupon else 0
    base = subtotal - discount
    return {"cupom": "PROHALL10" if valid_coupon else None, "desconto_cupom_centavos": discount, "base_produtos_centavos": base, "desconto_pix_centavos": round_percent(base, 5)}


def cart_summary(session):
    items = []
    for product_id, quantity in session["cart"].items():
        product = BY_ID[product_id]
        price = current_price_cents(product)
        items.append({"id": product_id, "nome": product["nome"], "imagem_url": product["imagem_url"], "quantidade": quantity, "preco_unitario_centavos": price, "total_centavos": price * quantity, "peso_bruto_g": product["peso_bruto_g"]})
    subtotal = sum(item["total_centavos"] for item in items)
    amounts = product_amounts(subtotal, session["coupon"])
    if session["coupon"] and not amounts["cupom"]:
        session["coupon"] = None
    weight = sum(item["peso_bruto_g"] * item["quantidade"] for item in items)
    return {"items": items, "subtotal_centavos": subtotal, **amounts, "peso_itens_g": weight, "peso_cobrado_g": weight + 200 if items else 0}


def totals(session, cep=None, mode=None):
    cart = cart_summary(session)
    cep = cep if cep is not None else session["cep"]
    mode = mode if mode is not None else session["shipping_mode"]
    quote = quote_shipping(cep, cart["peso_itens_g"], cart["base_produtos_centavos"]) if cep and cart["items"] else None
    if quote and mode not in ("economica", "expressa"):
        raise ValueError("Modalidade de frete inválida.")
    shipping = quote["opcoes"][mode]["valor_centavos"] if quote else None
    return {**cart, "frete": quote, "modalidade_frete": mode if quote else None, "valor_frete_centavos": shipping, "total_pix_centavos": cart["base_produtos_centavos"] - cart["desconto_pix_centavos"] + shipping if quote else None}


def add_item(session, product_id, quantity=1):
    product = BY_ID.get(product_id)
    if not product:
        raise ValueError("Produto não encontrado no catálogo.")
    if type(quantity) is not int or quantity < 1:
        raise ValueError("Quantidade deve ser um inteiro positivo.")
    new_quantity = session["cart"].get(product_id, 0) + quantity
    if new_quantity > 10:
        raise ValueError("Limite de 10 unidades por item.")
    if new_quantity > product["estoque_teste"]:
        raise ValueError(f"Estoque de teste insuficiente: {product['estoque_teste']} unidade(s).")
    session["cart"][product_id] = new_quantity
    session["checkout_draft"] = None
    return totals(session)


def remove_item(session, product_id, quantity=None):
    if product_id not in BY_ID:
        raise ValueError("Produto não encontrado no catálogo.")
    if product_id not in session["cart"]:
        raise ValueError("Esse produto não está no carrinho.")
    if quantity is not None and (type(quantity) is not int or quantity < 1):
        raise ValueError("Quantidade deve ser um inteiro positivo.")
    if quantity is None or quantity >= session["cart"][product_id]:
        del session["cart"][product_id]
    else:
        session["cart"][product_id] -= quantity
    session["checkout_draft"] = None
    had_coupon = bool(session["coupon"])
    result = totals(session)
    if had_coupon and not session["coupon"]:
        result["aviso"] = "O cupom deixou de valer porque o subtotal ficou abaixo de R$ 150,00."
    return result


def apply_coupon(session, code):
    if not isinstance(code, str) or code.strip().upper() != "PROHALL10":
        raise ValueError("Cupom inválido.")
    if cart_summary(session)["subtotal_centavos"] < 15000:
        raise ValueError("PROHALL10 exige subtotal mínimo de R$ 150,00.")
    session["coupon"] = "PROHALL10"
    session["checkout_draft"] = None
    return totals(session)


def validate_checkout_data(data):
    if not isinstance(data, dict):
        raise ValueError("Dados do pedido inválidos.")
    name, email, cep, address, number, complement, mode = (data.get(key) for key in ("nome", "email", "cep", "endereco", "numero", "complemento", "modalidade_frete"))
    if not isinstance(name, str) or not 2 <= len(name.strip()) <= 100:
        raise ValueError("Informe um nome válido.")
    if not isinstance(email, str) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 150:
        raise ValueError("Informe um e-mail válido.")
    if not isinstance(address, str) or not 3 <= len(address.strip()) <= 180:
        raise ValueError("Informe um endereço válido.")
    if not isinstance(number, (str, int)) or not str(number).strip() or len(str(number)) > 20:
        raise ValueError("Informe o número do endereço.")
    if complement is not None and (not isinstance(complement, str) or len(complement) > 120):
        raise ValueError("Complemento inválido.")
    if mode not in ("economica", "expressa"):
        raise ValueError("Escolha frete Econômico ou Expresso.")
    if not zone_for_cep(cep):
        raise ValueError("CEP inválido. Informe 8 dígitos de uma faixa atendida, com ou sem hífen.")
    return {"nome": name.strip(), "email": email.strip(), "cep": cep.replace("-", ""), "endereco": address.strip(), "numero": str(number).strip(), "complemento": (complement or "").strip(), "modalidade_frete": mode}


def prepare_checkout(session, data):
    if not session["cart"]:
        raise ValueError("O carrinho está vazio.")
    if not isinstance(data, dict):
        raise ValueError("Dados do pedido inválidos.")
    customer = validate_checkout_data({**data, "modalidade_frete": "economica"})
    summary = totals(session, customer["cep"], "economica")
    session["checkout_draft"] = {key: value for key, value in customer.items() if key != "modalidade_frete"}
    session["cep"] = customer["cep"]
    totals_by_shipping = {
        mode: {
            "frete_centavos": option["valor_centavos"],
            "total_pix_centavos": summary["base_produtos_centavos"] - summary["desconto_pix_centavos"] + option["valor_centavos"],
            "prazo_dias_uteis": option["prazo_dias_uteis"],
        }
        for mode, option in summary["frete"]["opcoes"].items()
    }
    return {"cliente": session["checkout_draft"], "resumo": summary, "totais_por_frete": totals_by_shipping, "aviso": "Pedido ainda não criado. Apresente os valores e pergunte qual frete a cliente prefere."}


def confirm_shipping_and_generate_pix(session, mode):
    if mode not in ("economica", "expressa"):
        raise ValueError("Escolha frete Econômico ou Expresso.")
    if not session.get("checkout_draft"):
        raise ValueError("Peça os dados de entrega e prepare o pedido antes de escolher o frete.")
    order = finalize_order(session, {**session["checkout_draft"], "modalidade_frete": mode})
    return generate_pix(session, order["id"])


def finalize_order(session, data):
    if not session["cart"]:
        raise ValueError("O carrinho está vazio.")
    customer = validate_checkout_data(data)
    cep, mode = customer["cep"], customer["modalidade_frete"]
    summary = totals(session, cep, mode)
    session["cep"] = cep
    session["shipping_mode"] = mode
    order_id = f"PH-TESTE-{uuid4().hex[:8].upper()}"
    order = {"id": order_id, "status": "aguardando_pagamento", "criado_em": datetime.now(timezone.utc).isoformat(), "cliente": {key: value for key, value in customer.items() if key != "modalidade_frete"}, "resumo": summary, "pix": None}
    session["orders"][order_id] = order
    session["cart"] = {}
    session["coupon"] = None
    session["checkout_draft"] = None
    return order


def get_order(session, order_id):
    order = session["orders"].get(order_id)
    if not order:
        raise ValueError("Pedido não encontrado nesta conversa.")
    if order["status"] == "aguardando_pagamento" and order["pix"] and datetime.now(timezone.utc) >= datetime.fromisoformat(order["pix"]["expira_em"]):
        order["status"] = "expirado"
    return order


def generate_pix(session, order_id):
    order = get_order(session, order_id)
    if order["status"] == "pago":
        raise ValueError("Este pedido já foi pago na simulação.")
    if order["status"] == "aguardando_pagamento" and order["pix"]:
        return order
    order["status"] = "aguardando_pagamento"
    order["pix"] = {"texto": f"PIX-TESTE|PROHALL|{order_id}|{order['resumo']['total_pix_centavos'] / 100:.2f}|{uuid4().hex[:8].upper()}|NAO-PAGAVEL", "expira_em": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()}
    return order


def simulate_payment(session, order_id):
    order = get_order(session, order_id)
    if order["status"] == "expirado":
        raise ValueError("PIX expirado. Gere outro antes de simular o pagamento.")
    if not order["pix"]:
        raise ValueError("Gere o PIX falso antes de simular o pagamento.")
    if order["status"] == "pago":
        return order
    order["status"] = "pago"
    order["pago_em"] = datetime.now(timezone.utc).isoformat()
    return order
