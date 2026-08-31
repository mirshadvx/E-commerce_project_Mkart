from decimal import Decimal
from django.utils import timezone as django_timezone
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True
    )
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(default=1)
    min_purchase_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    times_used = models.PositiveIntegerField(default=0)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.code

    def clean(self):
        super().clean()

        if self.code:
            self.code = self.code.strip().upper()
            if not self.code:
                raise ValidationError({'code': 'Coupon code cannot be empty.'})
            if len(self.code) < 3:
                raise ValidationError({'code': 'Coupon code must be at least 3 characters.'})
            qs = Coupon.objects.filter(code=self.code)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({'code': 'This coupon code already exists.'})

        if self.discount is None:
            raise ValidationError({'discount': 'Discount is required.'})
        if self.discount <= 0:
            raise ValidationError({'discount': 'Discount must be greater than 0.'})
        if self.discount > 70:
            raise ValidationError({'discount': 'Discount cannot exceed 70%.'})

        if self.valid_from and self.valid_to:
            if self.valid_from >= self.valid_to:
                raise ValidationError({'valid_to': 'Valid To must be after Valid From.'})

            if not self.pk and self.valid_to <= django_timezone.now():
                raise ValidationError({'valid_to': 'Valid To must be in the future.'})

        if self.usage_limit is None:
            raise ValidationError({'usage_limit': 'Usage limit is required.'})
        if self.usage_limit <= 0:
            raise ValidationError({'usage_limit': 'Usage limit must be at least 1.'})

        if self.min_purchase_amount is not None and self.min_purchase_amount < 0:
            raise ValidationError({'min_purchase_amount': 'Minimum purchase amount cannot be negative.'})

    def is_valid(self):
        now = django_timezone.now()
        return self.active and self.valid_from <= now <= self.valid_to

    def can_use(self, user):
        user_coupon_usage = User_Coupon_limit.objects.filter(coupon=self, user=user).first()
        if user_coupon_usage and user_coupon_usage.count_usage >= 2:
            return False, "You have already used this coupon 2 times."
        if self.times_used >= self.usage_limit:
            return False, "This coupon has reached its usage limit."
        return True, None

    def apply_discount(self, total_amount):
        if self.discount is None:
            return Decimal('0.00')
        discount_factor = Decimal(self.discount) / Decimal('100')
        return Decimal(total_amount) * discount_factor

    def increment_usage(self, user):
        user_coupon_usage, created = User_Coupon_limit.objects.get_or_create(user=user, coupon=self)
        user_coupon_usage.count_usage += 1
        user_coupon_usage.save()
        self.times_used += 1
        self.save()


class User_Coupon_limit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    count_usage = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'coupon']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.coupon.code} - {self.count_usage} uses"


class Offer(models.Model):
    name = models.CharField(max_length=255)
    discount = models.DecimalField(max_digits=5, decimal_places=2)
    valid_from = models.DateTimeField(default=django_timezone.now)
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    class Meta:
        ordering = ['-valid_from']
        
    def is_valid(self):
        now = django_timezone.now()
        return self.is_active and self.valid_from <= now <= self.valid_to

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username} wallet - Balance: {self.balance}"

class WalletTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=(('credit', 'Credit'), ('debit', 'Debit')))
    description = models.CharField(max_length=255, blank=True)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reference_type = models.CharField(max_length=50, blank=True)
    reference_id = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type.title()} of {self.amount} at {self.timestamp}"
    
    class Meta:
        ordering = ["-timestamp"]
