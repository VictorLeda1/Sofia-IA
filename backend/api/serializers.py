from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(min_length=1, max_length=2000)


class CartItemRequestSerializer(serializers.Serializer):
    id = serializers.CharField()
    quantidade = serializers.IntegerField(min_value=1, required=False, default=1)


class RemoveItemRequestSerializer(serializers.Serializer):
    quantidade = serializers.IntegerField(min_value=1, required=False)


class CouponRequestSerializer(serializers.Serializer):
    codigo = serializers.CharField()


class ShippingRequestSerializer(serializers.Serializer):
    cep = serializers.CharField()
    modalidade_frete = serializers.ChoiceField(choices=("economica", "expressa"), required=False)


class OrderRequestSerializer(serializers.Serializer):
    nome = serializers.CharField(min_length=2, max_length=100)
    email = serializers.EmailField(max_length=150)
    cep = serializers.CharField()
    endereco = serializers.CharField(min_length=3, max_length=180)
    numero = serializers.CharField(max_length=20)
    complemento = serializers.CharField(max_length=120, required=False, allow_blank=True)
    modalidade_frete = serializers.ChoiceField(choices=("economica", "expressa"))
