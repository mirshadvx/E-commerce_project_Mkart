from django.db import models
from django.contrib.auth.models import User
from Admin.models import *
from django.utils import timezone as django_timezone

class Gender(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(null=True,blank=True)
    status = models.BooleanField(default=True)
    offer = models.ForeignKey(Offer, on_delete=models.SET_NULL,null=True)
    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Color(models.Model):
    name = models.CharField(max_length=50, unique=True)
    hex_code = models.CharField(max_length=7, unique=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    gender = models.ForeignKey(Gender, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)                                                                                                      
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    offer = models.ForeignKey(Offer, on_delete=models.SET_NULL, null=True, blank=True)

    def get_discounted_price(self):
        best_discount = 0
        if self.offer and self.offer.is_active and self.offer.valid_from <= django_timezone.now() <= self.offer.valid_to:
            best_discount = self.offer.discount

        if self.category.offer and self.category.offer.is_active and self.category.offer.valid_from <= django_timezone.now() <= self.category.offer.valid_to:
            if self.category.offer.discount > best_discount:
                best_discount = self.category.offer.discount

        if best_discount > 0:
            return self.variants.first().price * (1 - best_discount / 100)
        
        return self.variants.first().price

    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    image_1 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    image_2 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    image_3 = models.ImageField(upload_to='product_images/', blank=True, null=True)

    def __str__(self):
        return f"{self.product.name} - {self.color.name}"