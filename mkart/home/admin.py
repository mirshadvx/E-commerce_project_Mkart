from django.contrib import admin
from .models import *


class show_order(admin.ModelAdmin):
    list_display = ("user","status","payment_method","total_price")
admin.site.register(Profile)
admin.site.register(UserAddress)
admin.site.register(Wishlist)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order,show_order)

admin.site.register(OrderItem)
admin.site.register(OrderAddress)

# @admin.register(Profile)
# class ProfileAdmin(admin.ModelAdmin):
#     list_display = ('user', 'phone', 'referral_code', 'referred_by')
#     search_fields = ('user__username', 'referral_code', 'referred_by__username')



