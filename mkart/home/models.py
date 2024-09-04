from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from products.models import Product, ProductVariant
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from django.db import models
import string
import random
from Admin.models import *

# class Profile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     phone = models.CharField(max_length=15, blank=True, null=True)

#     def __str__(self):
#         return self.user.username


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True, null=True)
    referral_code = models.CharField(max_length=10, unique=True, blank=True,null=True)
    referred_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')

    def __str__(self):
        return self.user.username

    def generate_referral_code(self):
        # Use the user's ID (which is unique) and a random 4-character string to create the referral code
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        self.referral_code = f'{self.user.id}{random_suffix}'

        # Ensure the generated code is unique
        while Profile.objects.filter(referral_code=self.referral_code).exists():
            random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            self.referral_code = f'{self.user.id}{random_suffix}'

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.generate_referral_code()
        super().save(*args, **kwargs)
        
    @classmethod
    def apply_referral(cls, user, referral_code):
        try:
            referred_by_profile = cls.objects.get(referral_code=referral_code)
            user.profile.referred_by = referred_by_profile.user
            user.profile.save()
            return True
        except cls.DoesNotExist:
            return False    
            
    @classmethod
    def apply_referral(cls, user, referral_code):
        try:
            referred_by_profile = cls.objects.get(referral_code=referral_code)
            user.profile.referred_by = referred_by_profile.user
            user.profile.save()

            # Add 50 rupees to the new user's wallet
            user.wallet.balance += 50
            user.wallet.save()

            # Add 100 rupees to the referrer's wallet
            referred_by_profile.user.wallet.balance += 100
            referred_by_profile.user.wallet.save()

            # Log the wallet transactions
            WalletTransaction.objects.create(wallet=user.wallet, amount=50, transaction_type='credit')
            WalletTransaction.objects.create(wallet=referred_by_profile.user.wallet, amount=100, transaction_type='credit')

            return True
        except cls.DoesNotExist:
            return False        
    
class UserAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField()
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.full_name}, {self.address_line_1}, {self.city}, {self.country}"    

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.CASCADE)
    added_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'variant')

    def __str__(self):
        return f"{self.user.username}'s wishlist item: {self.variant.product.name} - {self.variant.color.name}"

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s cart"
    
    def get_total_price(self):
        total = sum(item.get_total_price() for item in self.items.all())
        return total

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    
    def get_total_price(self):
        # Use the discounted price instead of the original price
        discounted_price = self.product_variant.product.get_discounted_price()
        return self.quantity * discounted_price

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped' ),
        ('delivered', 'Delivered'),
        ('completed', 'Completed'),
    ]

    PAYMENT_METHODS = [
        ('cod', 'Cash on Delivery'),
        ('razorpay', 'Razorpay'),
        ('wallet', 'Wallet'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('paid','Paid'),
        ('unpaid','Unpaid'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cod')
    payment_status = models.CharField(max_length=10,choices=PAYMENT_STATUS_CHOICES,default='unpaid')
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    coupon = models.CharField(max_length=50,null=True)
    discount_amount_coupon = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Order {self.id} - {self.user.username}"

    def calculate_total_price(self):
        total = sum(item.get_total_price() for item in self.ordered_items.all())
        self.total_price = total
        self.save()
        return total

class OrderItem(models.Model):
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped' ),
        ('delivered', 'Delivered'),
        ('returned','Returned'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('paid','Paid'),
        ('unpaid','Unpaid'),
    ]
    Action_status_choice = [
        ('cancel','Cancel'),
        ('return','Return'),
    ]
    order = models.ForeignKey(Order,related_name='ordered_items', on_delete=models.SET_NULL, blank=True, null=True)
    product_variant = models.ForeignKey('products.ProductVariant', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    item_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status_item = models.CharField(max_length=10,choices=PAYMENT_STATUS_CHOICES,default='unpaid')
    action_status = models.CharField(max_length=10,choices=Action_status_choice,default='cancel')
    return_request = models.BooleanField(default=False)
    # discount_amount_coupon = models.DecimalField(max_digits=10, decimal_places=2, default=0)
       
    
    def get_total_price(self):
        return self.quantity * self.price
    
    def update_status(self, new_status):
        # Rules for status changes
        valid_transitions = {
            'pending': ['processing', 'shipped', 'delivered'],
            'processing': ['shipped', 'delivered'],
            'shipped': ['delivered'],
            'delivered': ['returned'],
            'returned': [],
            'cancelled': [],
        }

        if new_status in valid_transitions.get(self.item_status, []):
            self.item_status = new_status
            self.save()
            return True
        return False
    
class OrderAddress(models.Model):
    order = models.OneToOneField('Order', on_delete=models.CASCADE, related_name='order_address')
    full_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField()
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    def __str__(self):
        return f"Address for Order {self.order.id} - {self.full_name} {self.last_name}"
    