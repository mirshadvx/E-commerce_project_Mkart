from django.urls import path 
from . import views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('',login_required(views.dashboard), name='dashboard'),
    path('productlist/', views.products_list, name='productlist'),
    path('toggle-variant-availability/', views.toggle_variant_availability, name='toggle_variant_availability'),
    path('edit_product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('addProduct/', views.add_product, name='addProduct'),
    path('addCategory/', views.add_Category, name='addCategory'),
    path('check-category/', views.check_category, name='check_category'),
    path('check-category/', views.check_category, name='check_category'),
    path('categorylist/',views.category_list,name='categorylist'),
    path('delete_category/<int:category_id>/', views.delete_category, name='delete_category'),
    path('edit_category/<int:category_id>/', views.edit_category, name='edit_category'),
    path('toggle_category_status/<int:category_id>/', views.toggle_category_status, name='toggle_category_status'),
    path('brandlist/', views.brand_list, name='brandlist'),
    path('check-brand-exists/', views.check_brand_exists, name='check_brand_exists'),
    path('add-brand/', views.add_brand, name='add_brand'),
    path('edit-brand/', views.edit_brand, name='edit_brand'),
    path('delete-brand/', views.delete_brand, name='delete_brand'),
    path('userlist/',views.user_list,name='userlist'),
    path('toggle-user-status/', views.toggle_user_status, name='toggle_user_status'),
    path('add-variant/<int:id>/', views.add_variant, name='add_variant'),
    path('logout', views.logout_admin, name='logout'),
    path('order_list/', views.show_order_list, name='order_list'),
    path('order_list/order_details/<int:id>/', views.show_order_details, name='order_details'),
    path('update_order_item_status/', views.update_order_item_status, name='update_order_item_status'),
    path('addcoupon/', views.add_coupon, name='add_coupon'),
    path('couponList/',views.show_coupon_list,name='coupon_list'),
    path('coupon_exists/',views.coupon_exists,name='coupon_exists'),
    path('get_coupon_details/', views.get_coupon_details, name='get_coupon_details'),
    path('edit_coupon/', views.edit_coupon, name='edit_coupon'),
    path('delete_coupon/', views.delete_coupon, name='delete_coupon'),
    path('control_coupon_status/', views.control_coupon_status,name='control_c_status'),
    path('offer/',views.offer_list,name='offer'),
    path('add_offer',views.add_offer,name='add_offer'),
    path('edit_offer/<int:offer_id>/',views.edit_offer,name='edit_offer'),
    path('delete_offer/<int:offer_id>/',views.delete_offer,name='delete_offer'),
    path('control_offer_status/<int:offer_id>/',views.control_offer_status,name='offer_status'),
    path('update-product-offer/', views.update_product_offer, name='update_product_offer'),
    path('update-category-offer/', views.update_category_offer, name='update_category_offer'),
    path('sales_report/',views.show_sales_details,name='sales_report'),
    path('sales_report/', views.show_sales_details, name='sales_report'),
    path('sales-report-data/', views.get_filtered_sales_data, name='sales_report_data'),
]