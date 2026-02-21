from django.db import models
from users.models import User

class Produce(models.Model):
    name = models.CharField(max_length=200,null=True)
    image = models.ImageField(upload_to='products/')
    CATEGORY_CHOICES = [
        ('Sukuma', 'sukuma'),
        ('Spinach', 'spinach'),
        ('Cabbage', 'cabbage'),
    ]
    category = models.CharField(
        max_length=20, 
        choices=CATEGORY_CHOICES,
        default='Sukuma'  # or default='Spinach'
    )

    available = models.BooleanField(default=True)
    location = models.CharField(max_length=100)
    unit = models.CharField(max_length=50, help_text="e.g., bundle, piece")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    farmer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')

    def __str__(self):
        return self.name
    
# models.py (add this to your existing models)


    