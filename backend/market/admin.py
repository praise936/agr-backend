from django.contrib import admin
from .models import Produce, Order, OrderItem, Cart, CartItem

# Very simple registration
admin.site.register(Produce)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Cart)
admin.site.register(CartItem)