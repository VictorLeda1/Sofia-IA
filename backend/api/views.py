"""Endpoints HTTP do teste. Estado isolado por cookie e mantido em memória."""

import base64
import copy
import io
import logging

import qrcode
from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, extend_schema
from drf_spectacular.types import OpenApiTypes
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import (
    CartItemRequestSerializer, ChatRequestSerializer, CouponRequestSerializer,
    OrderRequestSerializer, RemoveItemRequestSerializer, ShippingRequestSerializer,
)
from catalog.service import PRODUCTS, current_price_cents, detail_product
from commerce.service import (
    add_item, apply_coupon, finalize_order, generate_pix, get_order, get_session,
    money, remove_item, simulate_payment, totals, quote_shipping,
)
from sofia_ai.agent import chat
from commerce.transcript import save_conversation

logger = logging.getLogger(__name__)


class SessionView(APIView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.state = get_session(request.COOKIES.get("sofia_session"))

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if hasattr(self, "state"):
            response.set_cookie(
                "sofia_session", self.state["id"], httponly=True, samesite="Lax",
                secure=request.is_secure(), max_age=24 * 3600,
            )
        return response

    def handle_exception(self, exc):
        if isinstance(exc, ValueError):
            exc = ValidationError({"detail": str(exc)})
        return super().handle_exception(exc)


def order_view(order):
    response = {**order}
    if order["pix"]:
        qr = qrcode.make(order["pix"]["texto"])
        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")
        response["qr_data_url"] = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    else:
        response["qr_data_url"] = None
    return response


def checkout_message(preview):
    summary = preview["resumo"]
    shipping = preview["totais_por_frete"]
    lines = [
        "Confira o resumo calculado do pedido abaixo:",
        f"Subtotal: {money(summary['subtotal_centavos'])}.",
    ]
    if summary["desconto_cupom_centavos"]:
        lines.append(f"Desconto do cupom {summary['cupom']}: {money(summary['desconto_cupom_centavos'])}.")
    lines.append(f"Desconto no PIX: {money(summary['desconto_pix_centavos'])}.")
    lines.append(f"Produtos no PIX, após descontos: {money(summary['base_produtos_centavos'] - summary['desconto_pix_centavos'])}.")
    for mode, label in (("economica", "Econômico"), ("expressa", "Expresso")):
        option = shipping[mode]
        free = " (grátis)" if option["frete_centavos"] == 0 else ""
        lines.append(f"Frete {label}: {money(option['frete_centavos'])}{free}, {option['prazo_dias_uteis']} dias úteis. Total do pedido no PIX: {money(option['total_pix_centavos'])}.")
    lines.append("Você prefere frete Econômico ou Expresso?")
    return "\n".join(lines)


class ProductsView(SessionView):
    @extend_schema(operation_id="list_products", responses=OpenApiTypes.OBJECT, tags=["Catálogo"], summary="Listar os 15 produtos")
    def get(self, request):
        return Response([{**p, "preco_vigente_centavos": current_price_cents(p)} for p in PRODUCTS])


class ProductView(SessionView):
    @extend_schema(operation_id="get_product", parameters=[OpenApiParameter("product_id", str, OpenApiParameter.PATH)], responses=OpenApiTypes.OBJECT, tags=["Catálogo"], summary="Ficha completa do produto")
    def get(self, request, product_id):
        return Response(detail_product(product_id))


class StateView(SessionView):
    @extend_schema(responses=OpenApiTypes.OBJECT, tags=["Sessão"], summary="Estado atual da conversa")
    def get(self, request):
        return Response({"cart": totals(self.state), "messages": self.state["messages"], "checkout_preparado": bool(self.state.get("checkout_draft")), "debug": self.state["debug"][-30:], "orders": [{"id": o["id"], "status": get_order(self.state, o["id"])["status"]} for o in self.state["orders"].values()]})


class DebugToolsView(SessionView):
    @extend_schema(responses=OpenApiTypes.OBJECT, tags=["Debug"], summary="Ferramentas chamadas nesta conversa")
    def get(self, request):
        return Response({"calls": [{"name": event["name"], "args": event["args"]} for event in self.state["debug"]]})


class ChatView(SessionView):
    @extend_schema(request=ChatRequestSerializer, responses=OpenApiTypes.OBJECT, tags=["Sofia IA"], summary="Conversar com a Sofia (Gemini + ferramentas)")
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.validated_data["message"].strip()
        if not message:
            raise ValidationError({"message": "Mensagem vazia."})
        before = {key: copy.deepcopy(self.state[key]) for key in ("cart", "coupon", "cep", "shipping_mode", "checkout_draft", "orders")}
        try:
            result = chat(self.state, message)
        except RuntimeError as exc:
            self.state.update(before)
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception:
            self.state.update(before)
            logger.exception("Falha ao consultar Gemini")
            return Response({"detail": "Falha ao consultar o Gemini. Tente novamente."}, status=status.HTTP_502_BAD_GATEWAY)
        preview = next((event["result"] for event in reversed(result["debug"]) if event["name"] == "preparar_checkout" and isinstance(event["result"], dict) and "resumo" in event["result"]), None)
        preview = preview if self.state.get("checkout_draft") else None
        if preview:
            result["text"] = checkout_message(preview)
        latest = list(self.state["orders"].values())[-1] if self.state["orders"] else None
        changed_order = latest and (latest["id"] not in before["orders"] or latest["pix"] != before["orders"][latest["id"]]["pix"])
        if latest and changed_order and latest["pix"] and latest["status"] == "aguardando_pagamento":
            if latest["id"] not in before["orders"]:
                result["text"] = f"Pedido {latest['id']} criado e aguardando pagamento. O PIX de teste no valor de {money(latest['resumo']['total_pix_centavos'])} está disponível por 15 minutos. Gostaria de simular o pagamento? Use o botão no PIX exibido na tela."
            else:
                result["text"] = f"O PIX de teste do pedido {latest['id']} foi renovado por 15 minutos. Gostaria de simular o pagamento? Use o botão no PIX exibido na tela."
        self.state["messages"].extend([{"role": "user", "text": message}, {"role": "assistant", "text": result["text"], "cards": [p["id"] for p in result["cards"]], "checkout_preview": preview}])
        save_conversation(self.state)
        return Response({**result, "cart": totals(self.state), "checkout_preview": preview, "active_order": order_view(get_order(self.state, latest["id"])) if latest and changed_order else None})


class CartItemsView(SessionView):
    @extend_schema(request=CartItemRequestSerializer, responses=OpenApiTypes.OBJECT, tags=["Carrinho"], summary="Adicionar ao carrinho")
    def post(self, request):
        serializer = CartItemRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return Response(add_item(self.state, data["id"], data["quantidade"]))


class CartItemView(SessionView):
    @extend_schema(request=RemoveItemRequestSerializer, responses=OpenApiTypes.OBJECT, tags=["Carrinho"], summary="Remover unidades do carrinho")
    def delete(self, request, product_id):
        serializer = RemoveItemRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        return Response(remove_item(self.state, product_id, serializer.validated_data.get("quantidade")))


class CouponView(SessionView):
    @extend_schema(request=CouponRequestSerializer, responses=OpenApiTypes.OBJECT, tags=["Carrinho"], summary="Aplicar PROHALL10")
    def post(self, request):
        serializer = CouponRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(apply_coupon(self.state, serializer.validated_data["codigo"]))


class ShippingView(SessionView):
    @extend_schema(request=ShippingRequestSerializer, responses=OpenApiTypes.OBJECT, tags=["Frete"], summary="Calcular frete do carrinho atual")
    def post(self, request):
        serializer = ShippingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = totals(self.state)
        if not cart["items"]:
            raise ValidationError({"detail": "Adicione um produto para calcular o frete."})
        quote = quote_shipping(serializer.validated_data["cep"], cart["peso_itens_g"], cart["base_produtos_centavos"])
        self.state["cep"] = quote["cep"]
        if "modalidade_frete" in serializer.validated_data:
            self.state["shipping_mode"] = serializer.validated_data["modalidade_frete"]
        return Response(totals(self.state))


class OrdersView(SessionView):
    @extend_schema(request=OrderRequestSerializer, responses=OpenApiTypes.OBJECT, tags=["Checkout de teste"], summary="Criar pedido fictício")
    def post(self, request):
        serializer = OrderRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = finalize_order(self.state, serializer.validated_data)
        self.state["messages"].append({"role": "assistant", "text": f"Pedido de teste {order['id']} criado. Vamos gerar seu PIX fictício."})
        save_conversation(self.state)
        return Response(order_view(order), status=status.HTTP_201_CREATED)


class OrderView(SessionView):
    @extend_schema(responses=OpenApiTypes.OBJECT, tags=["Checkout de teste"], summary="Consultar pedido e validade do PIX")
    def get(self, request, order_id):
        return Response(order_view(get_order(self.state, order_id)))


class PixView(SessionView):
    @extend_schema(request=None, responses=OpenApiTypes.OBJECT, tags=["PIX falso"], summary="Gerar ou renovar PIX não pagável")
    def post(self, request, order_id):
        return Response(order_view(generate_pix(self.state, order_id)))


class SimulatePaymentView(SessionView):
    @extend_schema(request=None, responses=OpenApiTypes.OBJECT, tags=["PIX falso"], summary="Simular pagamento do PIX")
    def post(self, request, order_id):
        order = simulate_payment(self.state, order_id)
        self.state["messages"].append({"role": "assistant", "text": f"Pagamento simulado confirmado para {order_id}. Obrigada pela compra de teste! 💕"})
        save_conversation(self.state)
        return Response(order_view(order))
