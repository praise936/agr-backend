from rest_framework import serializers
from .models import Produce, Order, OrderItem, Cart, CartItem
from users.serializers import UserDetailSerializer
from django.db import transaction
from django.utils import timezone

class ProductSerializer(serializers.ModelSerializer):
    farmer_details = UserDetailSerializer(source='farmer', read_only=True)
    farmer_name = serializers.CharField(source='farmer.get_full_name', read_only=True)
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Produce
        fields = [
            'id', 'name', 'description', 'price', 'farmer', 'farmer_details',
            'farmer_name', 'location', 'category', 'is_available',
            'image', 'image_url', 'unit',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'farmer']

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
        return None

    


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.ImageField(source='product.image', read_only=True)
    product_image_url = serializers.SerializerMethodField()
    price_per_unit = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'product_name', 'product_image', 'product_image_url',
            'quantity', 'price_per_unit', 'subtotal', 'added_at'
        ]
        read_only_fields = ['id', 'added_at']

    def get_product_image_url(self, obj):
        if obj.product and obj.product.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.product.image.url)
        return None

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    items_count = serializers.IntegerField(source='total_items', read_only=True)
    
    class Meta:
        model = Cart
        fields = ['cart_id', 'items', 'subtotal', 'items_count', 'created_at', 'updated_at']
        read_only_fields = ['cart_id', 'created_at', 'updated_at']


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(read_only=True)
    product_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_image', 'product_name', 'product_image_url',
            'quantity', 'unit', 'price_per_unit', 'subtotal', 'is_delivered',
        ]
        read_only_fields = ['id', 'subtotal']

    def get_product_image_url(self, obj):
        # First check if order item has its own image URL
        if obj.product_image_url:
            return obj.product_image_url
        
        # If not, try to get from the related product
        if obj.product and obj.product.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.product.image.url)
        
        return None


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    farmer_name = serializers.CharField(source='farmer.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'tracking_number',
            'customer_name', 'customer_phone', 'customer_email',
            'delivery_address', 'delivery_instructions',
            'farmer', 'farmer_name',
            'status', 'status_display', 'payment_status', 'payment_status_display',
            'subtotal', 'delivery_fee', 'total_amount',
            'created_at', 'updated_at', 'confirmed_at', 'processing_at',
            'out_for_delivery_at', 'delivered_at', 'cancelled_at',
            'estimated_delivery_time', 'items'
        ]
        read_only_fields = [
            'order_number', 'created_at', 'updated_at',
            'confirmed_at', 'processing_at', 'out_for_delivery_at',
            'delivered_at', 'cancelled_at'
        ]


class CheckoutSerializer(serializers.Serializer):
    """Serializer for checkout process"""
    cart_id = serializers.CharField(required=False, allow_null=True)
    customer_name = serializers.CharField(max_length=255)
    customer_phone = serializers.CharField(max_length=20)
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    delivery_address = serializers.CharField()
    delivery_instructions = serializers.CharField(required=False, allow_blank=True)
    delivery_fee = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)

    def validate_customer_phone(self, value):
        """Basic phone validation"""
        if not value.replace('+', '').replace('-', '').isdigit():
            raise serializers.ValidationError("Invalid phone number format")
        return value

    def validate(self, data):
        # You could add more validation here (e.g., check if cart exists)
        return data


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status', 'payment_status', 'estimated_delivery_time', 'tracking_number']

    def validate_status(self, value):
        valid_statuses = ['confirmed', 'processing', 'out_for_delivery', 'delivered', 'cancelled']
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Invalid status. Choose from: {', '.join(valid_statuses)}"
            )
        return value


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders from cart"""
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer_name', 'customer_phone',
            'customer_email', 'delivery_address', 'delivery_instructions',
            'farmer', 'subtotal', 'delivery_fee', 'total_amount',
            'created_at', 'items'
        ]
        read_only_fields = ['id', 'order_number', 'created_at', 'subtotal', 'total_amount']

    @transaction.atomic
    def create(self, validated_data):
        # This will be implemented in the view
        pass