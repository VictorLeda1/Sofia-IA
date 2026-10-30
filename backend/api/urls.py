from django.urls import path

from api.views import (
    CartItemsView, CartItemView, ChatView, CouponView, DebugToolsView, OrderView, OrdersView,
    PixView, ProductView, ProductsView, ShippingView, SimulatePaymentView, StateView,
)

urlpatterns = [
    path("products/", ProductsView.as_view()),
    path("products/<str:product_id>/", ProductView.as_view()),
    path("session/", StateView.as_view()),
    path("debug/tools/", DebugToolsView.as_view()),
    path("chat/", ChatView.as_view()),
    path("cart/items/", CartItemsView.as_view()),
    path("cart/items/<str:product_id>/", CartItemView.as_view()),
    path("coupon/", CouponView.as_view()),
    path("shipping/", ShippingView.as_view()),
    path("orders/", OrdersView.as_view()),
    path("orders/<str:order_id>/", OrderView.as_view()),
    path("orders/<str:order_id>/pix/", PixView.as_view()),
    path("orders/<str:order_id>/simulate-payment/", SimulatePaymentView.as_view()),
]
