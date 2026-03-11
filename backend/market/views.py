from rest_framework import generics, filters, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from .models import Produce, Order, OrderItem, Cart, CartItem
from .serializers import (
    ProductSerializer, OrderSerializer, OrderCreateSerializer,
    OrderStatusUpdateSerializer, CartSerializer, CartItemSerializer,
    CheckoutSerializer
)
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.shortcuts import get_object_or_404
from django.db import transaction
import uuid

# ==================== PRODUCT VIEWS ====================

class ProductListView(generics.ListAPIView):
    """List all available products with filtering"""
    permission_classes = [AllowAny]
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'location']
    search_fields = ['name', 'farmer__first_name', 'farmer__last_name', 'farmer__email', 'location']
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        return Produce.objects.filter(is_available=True)


class ProductDetailView(generics.RetrieveAPIView):
    """Get single product details"""
    permission_classes = [AllowAny]
    queryset = Produce.objects.filter(is_available=True)
    serializer_class = ProductSerializer
    lookup_field = 'pk'


class ProductCreateView(generics.CreateAPIView):
    """Create a new product (farmers only)"""
    permission_classes = [IsAuthenticated]
    serializer_class = ProductSerializer

    def perform_create(self, serializer):
        if self.request.user.user_type != 'farmer':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only farmers can create products")
        serializer.save(farmer=self.request.user)


class ProductUpdateView(generics.UpdateAPIView):
    """Update product (owner only)"""
    permission_classes = [IsAuthenticated]
    serializer_class = ProductSerializer

    def get_queryset(self):
        return Produce.objects.filter(farmer=self.request.user)


class ProductDeleteView(generics.DestroyAPIView):
    """Delete product (owner only)"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Produce.objects.filter(farmer=self.request.user)


class MyProductListView(generics.ListAPIView):
    """List products created by current user"""
    permission_classes = [IsAuthenticated]
    serializer_class = ProductSerializer

    def get_queryset(self):
        return Produce.objects.filter(farmer=self.request.user).select_related('farmer')


# ==================== CART VIEWS ====================

class CartView(APIView):
    """Handle cart operations"""
    permission_classes = [AllowAny]

    def get_cart(self, request):
        """Get or create cart based on session or user"""
        cart_id = request.query_params.get('cart_id')
        
        if request.user.is_authenticated:
            # Try to get user's active cart
            cart = Cart.objects.filter(customer=request.user, is_active=True).first()
            if cart:
                return cart
        
        if cart_id:
            # Try to get cart by ID
            cart = Cart.objects.filter(cart_id=cart_id, is_active=True).first()
            if cart:
                return cart
        
        # Create new cart
        cart = Cart.objects.create(
            customer=request.user if request.user.is_authenticated else None
        )
        return cart

    def get(self, request):
        """Get current cart"""
        cart = self.get_cart(request)
        serializer = CartSerializer(cart, context={'request': request})
        return Response({
            'cart_id': cart.cart_id,
            'cart': serializer.data
        })

    def post(self, request):
        """Add item to cart"""
        cart = self.get_cart(request)
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)

        try:
            # Convert to Decimal instead of float
            from decimal import Decimal
            quantity = Decimal(str(quantity))
        except (TypeError, ValueError):
            return Response({'error': 'Invalid quantity'}, status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(Produce, id=product_id, is_available=True)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            # Add using Decimal
            cart_item.quantity += quantity
            cart_item.save()

        serializer = CartSerializer(cart, context={'request': request})
        return Response({
            'message': 'Item added to cart',
            'cart_id': cart.cart_id,
            'cart': serializer.data
        })

    def put(self, request):
        """Update cart item quantity"""
        cart = self.get_cart(request)
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity')

        try:
            from decimal import Decimal
            quantity = Decimal(str(quantity))
        except (TypeError, ValueError):
            return Response({'error': 'Invalid quantity'}, status=status.HTTP_400_BAD_REQUEST)

        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

        if quantity <= 0:
            cart_item.delete()
            message = 'Item removed from cart'
        else:
            cart_item.quantity = quantity
            cart_item.save()
            message = 'Cart updated'

        serializer = CartSerializer(cart, context={'request': request})
        return Response({
            'message': message,
            'cart': serializer.data
        })

    def delete(self, request):
        """Remove item from cart"""
        cart = self.get_cart(request)
        item_id = request.query_params.get('item_id')

        if item_id:
            cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
            cart_item.delete()

        serializer = CartSerializer(cart, context={'request': request})
        return Response({
            'message': 'Item removed from cart',
            'cart': serializer.data
        })


# ==================== ORDER VIEWS ====================

# In views.py, update the CheckoutView's post method

class CheckoutView(APIView):
    """Process checkout and create order"""
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        cart_id = data.get('cart_id')

        # Get cart
        cart = None
        if cart_id:
            cart = Cart.objects.filter(cart_id=cart_id, is_active=True).first()
        
        if request.user.is_authenticated and not cart:
            cart = Cart.objects.filter(customer=request.user, is_active=True).first()

        if not cart or not cart.items.exists():
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        # Group items by farmer
        farmer_items = {}
        for cart_item in cart.items.select_related('product__farmer'):
            farmer = cart_item.product.farmer
            if farmer not in farmer_items:
                farmer_items[farmer] = []
            farmer_items[farmer].append(cart_item)

        orders = []
        
        # Create order for each farmer
        for farmer, items in farmer_items.items():
            # Calculate totals
            subtotal = sum(item.subtotal for item in items)
            delivery_fee = data.get('delivery_fee', 0)
            total = subtotal + delivery_fee

            # Create order
            order = Order.objects.create(
                customer_name=data['customer_name'],
                customer_phone=data['customer_phone'],
                customer_email=data.get('customer_email', ''),
                delivery_address=data['delivery_address'],
                delivery_instructions=data.get('delivery_instructions', ''),
                farmer=farmer,
                customer=request.user if request.user.is_authenticated else None,
                subtotal=subtotal,
                delivery_fee=delivery_fee,
                total_amount=total,
                status='pending'
            )

            # Create order items and set image URL
            for cart_item in items:
                product = cart_item.product
                
                # Get the Cloudinary URL - no need to build absolute URL!
                # Cloudinary URLs are already absolute
                image_url = None
                if product.image:
                    image_url = product.image.url  # This is already a full URL
                
                # Get thumbnail URL for potential use
                thumbnail_url = None
                if product.image:
                    thumbnail_url = product.image.build_url(width=100, height=100, crop='thumb')
                
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    product_image=None,  # We don't need to store the file anymore
                    product_image_url=image_url,  # Store the Cloudinary URL
                    quantity=cart_item.quantity,
                    unit=product.unit,
                    price_per_unit=product.price,
                    subtotal=cart_item.subtotal
                )

            orders.append(order)

        # Mark cart as inactive
        cart.is_active = False
        cart.save()

        # Serialize orders with request context
        order_serializer = OrderSerializer(orders, many=True, context={'request': request})
        
        return Response({
            'message': 'Order placed successfully',
            'orders': order_serializer.data,
            'order_numbers': [order.order_number for order in orders]
        }, status=status.HTTP_201_CREATED)

class OrderListCreateView(generics.ListCreateAPIView):
    """List orders for farmer or create new order"""
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['order_number', 'customer_name', 'customer_phone', 'delivery_address']
    ordering_fields = ['created_at', 'total_amount', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user
        
        if user.user_type == 'farmer':
            queryset = Order.objects.filter(farmer=user)
        else:
            # For customers, show their orders
            queryset = Order.objects.filter(customer=user)
        
        # Apply filters
        status_filter = self.request.query_params.get('status')
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)

        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.select_related('farmer').prefetch_related('items')


class OrderDetailView(generics.RetrieveAPIView):
    """Get order details"""
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'farmer':
            return Order.objects.filter(farmer=user)
        return Order.objects.filter(customer=user)


class OrderStatusUpdateView(APIView):
    """Update order status (farmers only)"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        order = get_object_or_404(Order, pk=pk, farmer=request.user)
        serializer = OrderStatusUpdateSerializer(order, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(OrderSerializer(order).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrderStatsView(APIView):
    """Get order statistics for farmer"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.user_type != 'farmer':
            return Response({'error': 'Only farmers can access stats'}, status=status.HTTP_403_FORBIDDEN)

        queryset = Order.objects.filter(farmer=request.user)
        today = timezone.now().date()
        
        # Orders by status
        orders_by_status = {}
        for status_code, _ in Order.ORDER_STATUS:
            orders_by_status[status_code] = queryset.filter(status=status_code).count()

        # Today's revenue
        today_orders = queryset.filter(created_at__date=today)
        today_revenue = today_orders.aggregate(total=Sum('total_amount'))['total'] or 0

        # Total revenue
        total_revenue = queryset.aggregate(total=Sum('total_amount'))['total'] or 0

        stats = {
            'totalOrders': queryset.count(),
            'pendingOrders': queryset.filter(status='pending').count(),
            'processingOrders': queryset.filter(status='processing').count(),
            'outForDelivery': queryset.filter(status='out_for_delivery').count(),
            'deliveredToday': queryset.filter(status='delivered', delivered_at__date=today).count(),
            'totalRevenue': float(total_revenue),
            'revenueToday': float(today_revenue),
            'ordersByStatus': orders_by_status
        }

        return Response(stats)


class RecentOrdersView(generics.ListAPIView):
    """Get recent orders (last 7 days)"""
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        user = self.request.user
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        
        if user.user_type == 'farmer':
            return Order.objects.filter(
                farmer=user,
                created_at__gte=seven_days_ago
            ).select_related('farmer').prefetch_related('items')[:10]
        else:
            return Order.objects.filter(
                customer=user,
                created_at__gte=seven_days_ago
            ).select_related('farmer').prefetch_related('items')[:10]