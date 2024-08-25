from django.urls import path 
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('', views.store, name='store'),
    path('home/',views.home,name='home'),
    path('register/', views.register, name='register'),
    path('check_username/', views.check_username, name='check_username'),
    path('check_email/', views.check_email, name='check_email'),
    path('validate-otp/', views.validate_otp, name='validate_otp'),
    path('checkout/', views.checkout, name='checkout'),
    path('logout/', views.logoutPage, name='logout'),  
    path('login/', views.loginpage, name='login'), 
    path('resend-otp',views.resend_otp,name='resend_otp'),
    path('account',views.account,name='account'),
    path('social-login-success/', views.social_login_success, name='social_login_success'),
    path('productslist/',views.show_products,name='productslist'),
    path('product_info/<int:id>/',views.product_info,name='product_info'),
    # path('product_variant/<int:id>/',views.product_variant_info, name='product_variant_info'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/add/<int:id>/', views.add_wishlist, name='add_wishlist'),
    path('wishlist/remove/<int:id>/', views.remove_wishlist, name='remove_wishlist'),
    path('cart/', views.cart, name='cart'),
    path('cart/add/<int:id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:cart_item_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:id>/',views.remove_cart,name='remove_cart'),
    path('submit_address/', views.submit_address, name='submit_address'),
    path('edit_address/<int:id>/', views.edit_address, name='edit_address'),
    path('delete_address/<int:address_id>/', views.delete_address, name='delete_address'),
    path('checkout/',views.checkout,name='checkout'),
    path('order_confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('order_info/<int:order_id> ',views.show_order_details,name='order_info'),
    path('edit_details',views.edit_details,name='edit_details'),
    #for reset password 
    path('password_reset/',auth_views.PasswordResetView.as_view(template_name='store/password_reset.html'),name='password_reset'),
    path('password_reset_done/',auth_views.PasswordResetDoneView.as_view(template_name='store/password_reset_done.html'),name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',auth_views.PasswordResetConfirmView.as_view(template_name='store/password_reset_confirm.html'),name='password_reset_confirm'),
    path('password-reset-complete/',auth_views.PasswordResetCompleteView.as_view(template_name='store/password_reset_complete.html'),name='password_reset_complete'),
    path('auth-receiver', views.auth_receiver, name='auth_receiver'),
    
    path('cancel-item/', views.cancel_item, name='cancel_item'),
    path('return-item/', views.return_item, name='return_item'),
    
    
]
