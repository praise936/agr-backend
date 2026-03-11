# management/commands/migrate_to_cloudinary.py
from django.core.management.base import BaseCommand
from market.models import Produce
import cloudinary.uploader
from django.core.files.base import ContentFile
import os

class Command(BaseCommand):
    help = 'Migrate existing local images to Cloudinary'

    def handle(self, *args, **options):
        products = Produce.objects.all()
        for product in products:
            if product.image and hasattr(product.image, 'file'):
                # If there's a local file, upload to Cloudinary
                try:
                    # This will automatically upload to Cloudinary on save
                    product.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully migrated image for {product.name}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to migrate {product.name}: {str(e)}')
                    )