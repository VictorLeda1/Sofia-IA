import json
from pathlib import Path

from django.conf import settings

PRODUCTS = json.loads((settings.REPO_DIR / "data" / "produtos.json").read_text(encoding="utf-8"))
BY_ID = {product["id"]: product for product in PRODUCTS}


def current_price_cents(product):
    from decimal import Decimal, ROUND_HALF_UP

    value = product["preco_promocional"] if product["preco_promocional"] is not None else product["preco"]
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def search_products(term=None, category=None, usage=None):
    query = str(term or "").casefold().strip()
    found = []
    for product in PRODUCTS:
        searchable = " ".join((product["nome"], product["descricao_curta"], *product["indicado_para"])).casefold()
        if query and query not in searchable:
            continue
        if category and product["categoria"] != category:
            continue
        if usage and product["uso"] not in (usage, "ambos"):
            continue
        found.append({
            "id": product["id"],
            "nome": product["nome"],
            "preco_centavos": current_price_cents(product),
            "descricao_curta": product["descricao_curta"],
            "uso": product["uso"],
            "estoque_teste": product["estoque_teste"],
        })
    return found


def detail_product(product_id):
    product = BY_ID.get(product_id)
    if not product:
        raise ValueError("Produto não encontrado no catálogo.")
    return product
