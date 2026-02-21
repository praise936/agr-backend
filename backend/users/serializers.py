from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User
import re  # Missing import for re module

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = [
            'name', 'password', 'password2',
            'user_type', 'phone_number',
            'location', 'profile_picture', 
        ]

    def validate_name(self, value):
        """Validate username format"""
        if not re.match(r'^[\w.@+-]+$', value):
            raise serializers.ValidationError(
                "name may contain only letters, numbers, and @/./+/-/_ characters"
            )
        return value
    
    def validate_password(self, value):
        """Validate password strength"""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, data):
        """Check that passwords match"""
        if data.get('password') != data.get('password2'):
            raise serializers.ValidationError({"password": "Passwords must match."})
        return data  # Missing return statement
    
    def create(self, validated_data):
        """Create and return a new user"""
        # Remove password2 as it's not needed for user creation
        validated_data.pop('password2')
        password = validated_data.pop('password')
        validated_data['username'] = validated_data.get('name')
        
        # Create user
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        return user

class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer for user details (read-only)"""
    
    product_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'name', 'user_type',
            'phone_number', 'profile_picture', 'location', 'date_joined',
            'product_count'  
        ]

