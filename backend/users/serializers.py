from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User
import re

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
        """Validate username format and check if it already exists"""
        # Check format
        if not re.match(r'^[\w.@+-]+$', value):
            raise serializers.ValidationError(
                "Name may contain only letters, numbers, and @/./+/-/_ characters"
            )
        
        # Check if username already exists
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "This username is already taken. Please choose another one."
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
        return data
    
    def create(self, validated_data):
        """Create and return a new user"""
        # Remove password2 as it's not needed for user creation
        validated_data.pop('password2')
        password = validated_data.pop('password')
        
        # Use name as username
        validated_data['username'] = validated_data.get('name')
        
        try:
            # Create user
            user = User.objects.create_user(
                username=validated_data['username'],
                password=password,
                **validated_data
            )
            return user
        except Exception as e:
            # Catch any database errors (like duplicate username)
            if 'unique constraint' in str(e).lower() or 'duplicate' in str(e).lower():
                raise serializers.ValidationError({
                    'name': ['This username is already taken. Please choose another one.']
                })
            raise e

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