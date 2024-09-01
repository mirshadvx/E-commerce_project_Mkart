from django.urls import path 
from . import views


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('productlist/', views.products_list, name='productlist'),
    path('toggle-variant-availability/', views.toggle_variant_availability, name='toggle_variant_availability'),
    path('edit_product/<int:product_id>/', views.edit_product, name='edit_product'),
    # path('t/', views.toggle_product_status, name='toggle_product_status'),
    path('addProduct/', views.add_product, name='addProduct'),
    path('addCategory/', views.add_Category, name='addCategory'),
    path('check-category/', views.check_category, name='check_category'),
    path('check-category/', views.check_category, name='check_category'),
    path('categorylist/',views.category_list,name='categorylist'),
    path('delete_category/<int:category_id>/', views.delete_category, name='delete_category'),
    path('edit_category/<int:category_id>/', views.edit_category, name='edit_category'),
    path('toggle_category_status/<int:category_id>/', views.toggle_category_status, name='toggle_category_status'),
    path('brandlist/',views.brand_list,name='brandlist'),
    path('userlist/',views.user_list,name='userlist'),
    path('toggle-user-status/', views.toggle_user_status, name='toggle_user_status'),
    path('add-variant/<int:id>/', views.add_variant, name='add_variant'),
    path('logout', views.logout_admin, name='logout'),
    
    ## order realated
    path('order_list/', views.show_order_list, name='order_list'),
    path('order_list/order_details/<int:id>/', views.show_order_details, name='order_details'),
    path('update_order_item_status/', views.update_order_item_status, name='update_order_item_status'),
    #coupon
    path('addcoupon/', views.add_coupon, name='add_coupon'),
    path('couponList/',views.show_coupon_list,name='coupon_list'),
    path('coupon_exists/',views.coupon_exists,name='coupon_exists'),
    #offer
    path('offer/',views.offer_list,name='offer'),
    path('add_offer/',views.add_offer,name='add_offer'),
    
    path('update-product-offer/', views.update_product_offer, name='update_product_offer'),
    # path('add_offer_to_category/', views.add_offer_to_category, name='add_offer_to_category'),
    path('update-category-offer/', views.update_category_offer, name='update_category_offer'),
    path('sales_report/',views.show_sales_details,name='sales_report'),
    
    
    

]