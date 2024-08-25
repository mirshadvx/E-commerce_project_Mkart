from django.dispatch import receiver
from allauth.account.signals import user_signed_up

# @receiver(user_signed_up)
# def social_login_user_signed_up(request, user, **kwargs):
#     user.is_active = True
#     user.save()