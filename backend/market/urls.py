from django.urls import path
from . import views

urlpatterns = [
    # Product URLs
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product-create'),
    path('products/my/', views.MyProductListView.as_view(), name='my-products'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('products/<int:pk>/update/', views.ProductUpdateView.as_view(), name='product-update'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product-delete'),

    # Cart URLs
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/', views.CartView.as_view(), name='cart-add'),
    path('cart/update/', views.CartView.as_view(), name='cart-update'),
    path('cart/remove/', views.CartView.as_view(), name='cart-remove'),

    # Checkout and Order URLs
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('orders/', views.OrderListCreateView.as_view(), name='order-list'),
    path('orders/recent/', views.RecentOrdersView.as_view(), name='recent-orders'),
    path('orders/stats/', views.OrderStatsView.as_view(), name='order-stats'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/update-status/', views.OrderStatusUpdateView.as_view(), name='order-status-update'),
]