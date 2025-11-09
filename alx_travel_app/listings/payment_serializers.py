"""
Serializers for payment-related views.
"""
from rest_framework import serializers
from .models import Payment

class PaymentResponseSerializer(serializers.ModelSerializer):
    """
    Serializer for payment response data
    """
    class Meta:
        model = Payment
        fields = [
            'payment_id', 'amount', 'payment_status', 'transaction_id',
            'chapa_reference', 'payment_date', 'currency', 'customer_email'
        ]
        read_only_fields = fields

class PaymentInitiateSerializer(serializers.Serializer):
    """
    Serializer for initiating a payment
    """
    booking_id = serializers.UUIDField(required=True)

class PaymentVerifyResponseSerializer(serializers.Serializer):
    """
    Serializer for payment verification response
    """
    status = serializers.CharField()
    payment = PaymentResponseSerializer()
    chapa_status = serializers.CharField()
    verification_data = serializers.DictField()

class PaymentListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing payments
    """
    class Meta:
        model = Payment
        fields = [
            'payment_id', 'amount', 'payment_status', 'payment_date',
            'currency', 'chapa_reference', 'booking_id'
        ]
        read_only_fields = fields
