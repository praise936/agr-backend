from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

# urlpatterns = [
#     path('market/', ProductListCreateView.as_view(), name='product-list'),
#     path('market/<uuid:pk>/', ProductRetrieveView.as_view(), name='product-detail'),
# ]



urlpatterns = [
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product-create'),
    path('products/<int:pk>/', views.ProductRetrieveView.as_view(), name='product-detail'),
]