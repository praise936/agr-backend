from rest_framework import serializers
from .models import Produce, Order, OrderItem, Cart, CartItem
from users.serializers import UserDetailSerializer
from django.db import transaction
from django.utils import timezone
import cloudinary.uploader

class ProductSerializer(serializers.ModelSerializer):
    farmer_details = UserDetailSerializer(source='farmer', read_only=True)
    farmer_name = serializers.CharField(source='farmer.get_full_name', read_only=True)
    
    # Cloudinary-specific fields
    image_url = serializers.SerializerMethodField()
    
    image_public_id = serializers.CharField(source='image.public_id', read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    image_versions = serializers.SerializerMethodField()
    
    class Meta:
        model = Produce
        fields = [
            'id', 'name', 'description', 'price', 'farmer', 'farmer_details',
            'farmer_name', 'location', 'category', 'is_available',
            'image', 'image_url', 'image_public_id', 'thumbnail_url', 'image_versions',
            'unit', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'farmer']

    def get_image_url(self, obj):
        """Get the full Cloudinary URL"""
        if obj.image:
            return obj.image.url
        return None

    def get_image(self, obj):
        """Get the image URL (alias for backward compatibility)"""
        return self.get_image_url(obj)

    def get_thumbnail_url(self, obj):
        """Get a thumbnail version of the image"""
        if obj.image:
            return obj.image.build_url(width=100, height=100, crop='thumb')
        return None

    def get_image_versions(self, obj):
        """Get multiple sized versions of the image"""
        if not obj.image:
            return None
        return {
            'thumbnail': obj.image.build_url(width=100, height=100, crop='thumb'),
            'small': obj.image.build_url(width=300, height=200, crop='limit'),
            'medium': obj.image.build_url(width=600, height=400, crop='limit'),
            'large': obj.image.build_url(width=1200, height=800, crop='limit'),
        }

    def create(self, validated_data):
        """Handle image upload through Cloudinary"""
        # The CloudinaryField handles the upload automatically
        return super().create(validated_data)


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    # Remove 'product_image' from fields and use only these
    product_image_url = serializers.SerializerMethodField()
    product_thumbnail = serializers.SerializerMethodField()
    price_per_unit = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'product_name', 
            'product_image_url', 'product_thumbnail',  # Removed 'product_image'
            'quantity', 'price_per_unit', 'subtotal', 'added_at'
        ]
        read_only_fields = ['id', 'added_at']

    def get_product_image_url(self, obj):
        """Get the full image URL"""
        if obj.product and obj.product.image:
            return obj.product.image.url
        return None

    def get_product_thumbnail(self, obj):
        """Get thumbnail version"""
        if obj.product and obj.product.image:
            return obj.product.image.build_url(width=100, height=100, crop='thumb')
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
    product_thumbnail_url = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'product_image_url', 'product_thumbnail_url',
            'quantity', 'unit', 'price_per_unit', 'subtotal', 'is_delivered',
        ]
        read_only_fields = ['id', 'subtotal']

    def get_product_image_url(self, obj):
        """Get the full Cloudinary URL"""
        # First check if order item has its own image URL
        if obj.product_image_url:
            return obj.product_image_url
        
        # If not, try to get from the related product
        if obj.product and obj.product.image:
            return obj.product.image.url
        
        return None

    def get_product_thumbnail_url(self, obj):
        """Get thumbnail version"""
        if obj.product and obj.product.image:
            return obj.product.image.build_url(width=100, height=100, crop='thumb')
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


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status', 'payment_status', 'estimated_delivery_time', 'tracking_number']


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