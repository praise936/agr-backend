from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class User(AbstractUser):
    
    """Custom User Model for Farmers Market Platform"""
    
    # User Types
    FARMER = 'farmer'
    BUYER = 'buyer'
    
    USER_TYPE_CHOICES = [
        (FARMER, 'Farmer'),
        (BUYER, 'Buyer'),
    ]
    name = models.CharField(max_length=100)
#  users_user
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default=BUYER)
    phone_number = models.CharField(max_length=10, blank=True)
   
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)

    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
  
    
    class Meta:
        ordering = ['-date_joined']
    
    def __str__(self):
        return self.name
    
    @property
    def is_farmer(self):
        return self.user_type == self.FARMER
    @property
    def is_authenticated(self):
        return True
   