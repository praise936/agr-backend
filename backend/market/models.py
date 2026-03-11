from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid
from cloudinary.models import CloudinaryField

User = get_user_model()

class Produce(models.Model):
    CATEGORY_CHOICES = [
        ('Sukuma', 'Sukuma Wiki'),
        ('Spinach', 'Spinach'),
        ('Cabbage', 'Cabbage'),
        ('Kale', 'Kale'),
        ('Lettuce', 'Lettuce'),
        ('Other', 'Other'),
    ]

    UNIT_CHOICES = [
        ('bundle', 'Bundle'),
        ('piece', 'Piece'),
        ('kg', 'Kilogram'),
        ('gram', 'Gram'),
        ('sack', 'Sack'),
        ('crate', 'Crate'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Cloudinary field for image storage
    image = CloudinaryField(
        'image',  # Public ID prefix
        folder='products/',  # Organize in folders
        resource_type='image',
        transformation=[
            {'width': 600, 'height': 400, 'crop': 'limit'}  # Optional default transformation
        ],
        blank=True,
        null=True
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Sukuma')
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='bundle')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=100)
    farmer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['farmer', 'is_available']),
            models.Index(fields=['category']),
            models.Index(fields=['location']),
        ]
    
    @property
    def image_public_id(self):
        """Get the Cloudinary public ID for frontend use"""
        return self.image.public_id if self.image else None
    @property
    def image_versions(self):
        """Get different sized versions of the image"""
        if not self.image:
            return None
        return {
            'thumbnail': self.image.build_url(width=100, height=100, crop='thumb'),
            'small': self.image.build_url(width=300, height=200, crop='limit'),
            'medium': self.image.build_url(width=600, height=400, crop='limit'),
            'large': self.image.build_url(width=1200, height=800, crop='limit'),
        }


    def __str__(self):
        return f"{self.name} - {self.farmer.get_full_name() or self.farmer.email}"



class Order(models.Model):
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    # Order identification quantity_available
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    tracking_number = models.CharField(max_length=50, unique=True, blank=True, null=True)

    # Customer details (captured at checkout)
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField(blank=True, null=True)
    delivery_address = models.TextField()
    delivery_instructions = models.TextField(blank=True, null=True)
    
    # Relationships
    farmer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders_as_farmer')
    # Optional: If you want to track which customer placed the order (if they're registered)
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders_as_customer')
    
    # Status
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Financial
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    processing_at = models.DateTimeField(null=True, blank=True)
    out_for_delivery_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['farmer', 'status']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['order_number']),
        ]

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate unique order number
            date_str = timezone.now().strftime('%Y%m%d')
            random_uuid = str(uuid.uuid4())[:6].upper()
            self.order_number = f"ORD-{date_str}-{random_uuid}"
        
        # Auto-update status timestamps
        if self.status == 'confirmed' and not self.confirmed_at:
            self.confirmed_at = timezone.now()
        elif self.status == 'processing' and not self.processing_at:
            self.processing_at = timezone.now()
        elif self.status == 'out_for_delivery' and not self.out_for_delivery_at:
            self.out_for_delivery_at = timezone.now()
        elif self.status == 'delivered' and not self.delivered_at:
            self.delivered_at = timezone.now()
        elif self.status == 'cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order_number} - {self.customer_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Produce, on_delete=models.SET_NULL, null=True, related_name='order_items')
    
    # Snapshot of product details at time of order
    product_name = models.CharField(max_length=255)
    product_image = models.ImageField(upload_to='order_items/', blank=True, null=True)
    product_image_url = models.URLField(blank=True, null=True)
    
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    
    # Track if this item was delivered/cancelled separately
    is_delivered = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.price_per_unit
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_name} x {self.quantity} {self.unit}"


class Cart(models.Model):
    """Temporary cart for anonymous users or logged-in customers"""
    cart_id = models.CharField(max_length=100, unique=True, editable=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='carts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.cart_id:
            self.cart_id = str(uuid.uuid4())
        super().save(*args, **kwargs)

    @property
    def total_items(self):
        return self.items.count()

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())

    def __str__(self):
        return f"Cart {self.cart_id}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Produce, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['cart', 'product']

    @property
    def subtotal(self):
        return self.quantity * self.product.price

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"