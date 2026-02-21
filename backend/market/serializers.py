from rest_framework import serializers
from .models import Produce
from users.serializers import UserDetailSerializer

class ProductSerializer(serializers.ModelSerializer):
    farmer = UserDetailSerializer(read_only=True)  # Read-only for GET requests
    image = serializers.ImageField(use_url=True)
    
    class Meta:
        model = Produce
        fields = [
            'id', 'name', 'price', 'farmer',
            'location', 'category', 'available',
            'image', 'unit',
        ]
        read_only_fields = ['id']  # id should be read-only
