# from time import timezone
from decimal import Decimal
from django.utils import timezone as django_timezone
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
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
    def is_valid(self):
        now = django_timezone.now()
        return self.active and self.valid_from <= now <= self.valid_to

    def can_use(self):
        if self.usage_limit:
            return self.times_used < self.usage_limit
        return True
    def apply_discount(self, total_amount):
        discount_factor = Decimal(self.discount) / Decimal(100)
        return Decimal(total_amount) * discount_factor

    def increment_usage(self):
        self.times_used += 1
        self.save()

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


