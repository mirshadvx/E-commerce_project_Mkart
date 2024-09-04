from django.db import IntegrityError
from django.shortcuts import render, redirect , get_object_or_404
from django.urls import reverse
from django.utils.text import slugify
from products.models import Category , Brand, Color, Gender, Product , ProductVariant
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
import base64
from base64 import b64decode
from PIL import Image
import os
from django.core.files.base import ContentFile
from django.views.decorators.http import require_POST
import base64
from io import BytesIO
from PIL import Image
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test , login_required
from django.core.exceptions import PermissionDenied
from django.contrib.auth import logout
from django.urls import reverse
from home.models import *
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
from django.core.exceptions import ValidationError
from .models import *
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum
from django.utils.dateparse import parse_datetime
from django.views.decorators.cache import never_cache

# Create your views here.

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def dashboard(request):
    return render(request,'dashboard.html') 


@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_Category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        logo = request.FILES.get('logo')
        
        slug = slugify(name)

        if Category.objects.filter(slug=slug).exists():
            messages.error(request, 'A category with this name already exists.')
            return render(request, 'addCategory.html')

        category = Category(
            name=name,
            description=description,
            slug=slug
        )
        if logo:
            category.logo.save(f"{slug}_logo.png", logo, save=False)
        
        category.save()

        messages.success(request, 'Category added successfully.')
    return render(request,'addCategory.html')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def check_category(request):
    category_name = request.GET.get('name', None)
    data = {
        'exists': Category.objects.filter(name__iexact=category_name).exists()
    }
    return JsonResponse(data)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def category_list(request):
    categories = Category.objects.all()
    offers = Offer.objects.filter(is_active=True)
    return render(request, 'categoryList.html', {'categories': categories, 'offers': offers})

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def toggle_category_status(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.status = not category.status
    category.save()
    return JsonResponse({'status': category.status})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_category(request, category_id):
    category = Category.objects.get(id=category_id)
    category.status = False
    category.save()

    return redirect('categorylist')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.description = request.POST.get('description')

        if not category.slug:
            category.slug = slugify(category.name)
            
        category.save()
        messages.success(request, 'Category updated successfully.')
        return redirect('categorylist')

    return render(request, 'editCategory.html', {'category': category})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def brand_list(request):
    brands = Brand.objects.all()
    return render(request, 'brandList.html', {'brands': brands})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variants_data = []
    for variant in product.variants.all():
        variant_data = {
            'id': variant.id,
            'color': variant.color,
            'price': variant.price,
            'stock': variant.stock,
            'is_available': variant.is_available,
            'images': [
                getattr(variant, f'image_{i}') for i in range(1, 4)
            ]
        }
        variants_data.append(variant_data)

    
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.gender = get_object_or_404(Gender, id=request.POST.get('gender'))
        product.category = get_object_or_404(Category, id=request.POST.get('category'))
        product.brand = get_object_or_404(Brand, id=request.POST.get('brand'))
        product.description = request.POST.get('description')
        product.save()

        for variant in product.variants.all():
            variant.color = get_object_or_404(Color, id=request.POST.get(f'variant_color_{variant.id}'))
            variant.price = request.POST.get(f'variant_price_{variant.id}')
            variant.stock = request.POST.get(f'variant_stock_{variant.id}')
            variant.is_available = request.POST.get(f'variant_is_available_{variant.id}') == 'True'

            for i in range(1, 4):
                cropped_image = request.POST.get(f'cropped_image_{variant.id}_{i}')
                if cropped_image:
                
                    format, imgstr = cropped_image.split(';base64,')
                    ext = format.split('/')[-1]
                    
            
                    filename = f'product_{product.id}_variant_{variant.id}_image_{i}.{ext}'
      
      
                    image_field = getattr(variant, f'image_{i}')
                    image_field.save(filename, ContentFile(base64.b64decode(imgstr)), save=False)

            variant.save()
        return redirect('productlist') 

    context = {
        'product': product,
        'variants_data': variants_data, 
        'genders': Gender.objects.all(),
        'categories': Category.objects.all(),
        'brands': Brand.objects.all(),
        'colors': Color.objects.all(),
    }
    
    return render(request, 'editProduct.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_product(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        gender_id = request.POST.get('gender')
        category_id = request.POST.get('category')
        brand_id = request.POST.get('brand')
        description = request.POST.get('description')

        gender = Gender.objects.get(id=gender_id)
        category = Category.objects.get(id=category_id)
        brand = Brand.objects.get(id=brand_id)
        
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        while Product.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        try:
            product = Product.objects.create(
                name=name,
                slug=slug,
                gender=gender,
                category=category,
                brand=brand,
                description=description,
            )
        except IntegrityError:
            messages.error(request, "Error creating product. Please try again.")
            return redirect('add_product')


        color_id = request.POST.get('color')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        
        is_available = request.POST.get('is_available') == 'True'

        color = Color.objects.get(id=color_id)
        variant = ProductVariant.objects.create(
            product=product,
            color=color,
            price=price,
            stock=stock,
            is_available=is_available  
        )


        for i in range(1, 4):
            cropped_image_field = f'cropped_image_{i}'
            image_data_url = request.POST.get(cropped_image_field)
            if image_data_url:
                format, imgstr = image_data_url.split(';base64,')
                ext = format.split('/')[-1]
                img_data = ContentFile(base64.b64decode(imgstr), name=f"{slug}_image_{i}.{ext}")

                if i == 1:
                    variant.image_1.save(f"{slug}_image_{i}.{ext}", img_data, save=False)
                elif i == 2:
                    variant.image_2.save(f"{slug}_image_{i}.{ext}", img_data, save=False)
                elif i == 3:
                    variant.image_3.save(f"{slug}_image_{i}.{ext}", img_data, save=False)

        variant.save()

        return redirect(reverse('productlist'))
    else:
        context = {
            'genders': Gender.objects.all(),
            'categories': Category.objects.all(),
            'brands': Brand.objects.all(),
            'colors': Color.objects.all(),
        }
        return render(request, 'addProduct.html', context)

def superuser_required(view_func):
    def check_superuser(user):
        return user.is_superuser
    decorated_view_func = user_passes_test(check_superuser, login_url='login')(view_func)
    return decorated_view_func

@login_required
@user_passes_test(lambda u: u.is_superuser)
# def products_list(request):
#     products = Product.objects.prefetch_related('variants', 'variants__color').all() 
#     return render(request, 'productsList.html', {'products': products})
def products_list(request):
    products = Product.objects.prefetch_related(
        'variants', 
        'variants__color'
    ).select_related(
        'offer', 
        'category', 
        'brand', 
        'gender'
    ).all()
    
    offers = Offer.objects.filter(is_active=True)
    
    return render(request, 'productsList.html', {'products': products, 'offers': offers})


@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def toggle_variant_availability(request):
    variant_id = request.POST.get('variant_id')
    try:
        variant = ProductVariant.objects.get(id=variant_id)
        variant.is_available = not variant.is_available
        variant.save()
        return JsonResponse({
            'success': True,
            'is_available': variant.is_available,
            'status_text': 'Available' if variant.is_available else 'Not Available'
        })
    except ProductVariant.DoesNotExist:
        return JsonResponse({'success': False}, status=404)
   

@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_list(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'userList.html', {'users': users})
    
    
@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def toggle_user_status(request):
    user_id = request.POST.get('user_id')
    is_active = request.POST.get('is_active') == 'true'
    
    try:
        user = User.objects.get(id=user_id)
        user.is_active = is_active
        user.save()
        return JsonResponse({'success': True})
    except User.DoesNotExist:
        return JsonResponse({'success': False}, status=404)
    
    
@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_variant(request, id):
    product = get_object_or_404(Product, id=id)
    
    if request.method == 'POST':
        color_id = request.POST.get('color')
        stock = request.POST.get('stock')
        price = request.POST.get('price')
        is_available = request.POST.get('is_available') == 'True'

        variant = ProductVariant(
            product=product,
            color_id=color_id,
            stock=stock,
            price=price,
        )

        
        for i in range(1, 4):
            cropped_image = request.POST.get(f'cropped_image_{i}')
            if cropped_image:
                format, imgstr = cropped_image.split(';base64,')
                ext = format.split('/')[-1]
                data = ContentFile(base64.b64decode(imgstr), name=f'product_{product.id}_variant_{i}.{ext}')
                setattr(variant, f'image_{i}', data)

        variant.save()
        # return redirect('product_list')  
        return render(request,'addVariant.html')

    context = {
        'product': product,
        'genders': Gender.objects.all(),
        'categories': Category.objects.all(),
        'brands': Brand.objects.all(),
        'colors': Color.objects.all(),
    }
    return render(request, 'addVariant.html', context)


@never_cache
def logout_admin(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect(reverse('login'))

@login_required
@user_passes_test(lambda u: u.is_superuser)
def show_order_list(request):
    orders = Order.objects.all().select_related('user').prefetch_related('ordered_items')
    
    context = {
        'orders': orders
    }
    return render(request,'orderlist.html',context)

# def show_order_details(request, id):
#     order = get_object_or_404(Order.objects.select_related('user', 'order_address').prefetch_related('ordered_items__product_variant'), id=id)
    
#     context = {
#         'order': order,
#     }
#     return render(request, 'order_Details.html', context)

# def show_order_details(request, id):
#     order = get_object_or_404(Order.objects.select_related('user', 'order_address').prefetch_related(
#         'ordered_items__product_variant__product__brand',
#         'ordered_items__product_variant__product__category',
#         'ordered_items__product_variant__color'
#     ), id=id)
    
#     for item in order.ordered_items.all():
#         item.payment_status = item.get_payment_status()
    
#     context = {
#         'order': order,
#     }
#     return render(request, 'order_Details.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def show_order_details(request, id):
    order = get_object_or_404(Order.objects.select_related('user', 'order_address').prefetch_related(
        'ordered_items__product_variant__product__brand',
        'ordered_items__product_variant__product__category',
        'ordered_items__product_variant__color'
    ), id=id)

    context = {
        'order': order,
    }
    return render(request, 'order_Details.html', context)

# @require_POST
# def update_order_item_status(request):
#     item_id = request.POST.get('item_id')
#     new_status = request.POST.get('new_status')
    
#     try:
#         order_item = OrderItem.objects.get(id=item_id)
#         order_item.item_status = new_status
#         order_item.save()
#         return JsonResponse({'success': True})
#     except OrderItem.DoesNotExist:
#         return JsonResponse({'success': False, 'error': 'Order item not found'})
#     except Exception as e:
#         return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def update_order_item_status(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        new_status = request.POST.get('new_status')

        try:
            order_item = OrderItem.objects.get(id=item_id)
            
            if order_item.update_status(new_status):
                if order_item.item_status == 'delivered':
                    order_item.payment_status_item = 'paid'
                    order_item.save()
                
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Invalid status transition.'})
        
        except OrderItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Order item not found.'})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})


# def update_order_item_status(request):
    
#     if request.method == 'POST':
#         item_id = request.POST.get('item_id')
#         new_status = request.POST.get('new_status')

#         try:
#             order_item = OrderItem.objects.get(id=item_id)
#             if order_item.update_status(new_status):
#                 if order_item.item_status == 'delivered':
#                     order_item.payment_status_item = 'paid'
#                     order_item.save()
#                 return JsonResponse({'success': True})
#             else:
#                 return JsonResponse({'success': False, 'error': 'Invalid status transition.'})
#         except OrderItem.DoesNotExist:
#             return JsonResponse({'success': False, 'error': 'Order item not found.'})

#     return JsonResponse({'success': False, 'error': 'Invalid request method.'})



@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_coupon(request):
    if request.method == 'POST':
        try:
            # Extract data from POST request
            code = request.POST.get('code')
            discount = request.POST.get('discount')
            valid_from = request.POST.get('valid_from')
            valid_to = request.POST.get('valid_to')
            active = request.POST.get('active') == 'True'
            usage_limit = request.POST.get('usage_limit')
            min_purchase_amount = request.POST.get('min_purchase_amount')
            description = request.POST.get('description')

            # Create new Coupon instance
            coupon = Coupon(
                code=code,
                discount=Decimal(discount),
                valid_from=valid_from,
                valid_to=valid_to,
                active=active,
                description=description
            )

            # Handle optional fields
            if usage_limit:
                coupon.usage_limit = int(usage_limit)
            if min_purchase_amount:
                coupon.min_purchase_amount = Decimal(min_purchase_amount)

            # Validate the model
            coupon.full_clean()

            # Save the coupon
            coupon.save()

            messages.success(request, f'Coupon "{code}" has been successfully added.')
            return redirect('coupon_list')  # Assuming you have a URL named 'coupon_list'

        except ValidationError as e:
            # Handle validation errors
            error_messages = []
            for field, errors in e.message_dict.items():
                error_messages.extend(errors)
            for message in error_messages:
                messages.error(request, message)

        except Exception as e:
            # Handle any other unexpected errors
            messages.error(request, f'An error occurred: {str(e)}')

    # If it's a GET request or if there were errors, render the form again
    return render(request, 'addCoupon.html')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def coupon_exists(request):
    coupon_code = request.GET.get('code', None)
    exists = Coupon.objects.filter(code=coupon_code).exists()
    return JsonResponse({'exists': exists})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def show_coupon_list(request):
    coupons = Coupon.objects.all()
    return render(request, 'couponList.html', {'coupons': coupons})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def get_coupon_details(request):
    coupon_id = request.GET.get('id')
    try:
        coupon = Coupon.objects.get(id=coupon_id)
        data = {
            'id': coupon.id,
            'code': coupon.code,
            'discount': coupon.discount,
            'valid_from': coupon.valid_from.isoformat(),
            'valid_to': coupon.valid_to.isoformat(),
            'active': coupon.active,
            'usage_limit': coupon.usage_limit,
            'description': coupon.description,
        }
        return JsonResponse(data)
    except Coupon.DoesNotExist:
        return JsonResponse({'error': 'Coupon not found'}, status=404)

@csrf_exempt
@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_coupon(request):
    if request.method == 'POST':
        coupon_id = request.POST.get('id')
        try:
            coupon = Coupon.objects.get(id=coupon_id)
            coupon.code = request.POST.get('code')
            coupon.discount = request.POST.get('discount')
            coupon.valid_from = parse_datetime(request.POST.get('valid_from'))
            coupon.valid_to = parse_datetime(request.POST.get('valid_to'))
            coupon.active = request.POST.get('active') == 'true'
            coupon.usage_limit = request.POST.get('usage_limit') or None
            coupon.description = request.POST.get('description')
            coupon.save()
            return JsonResponse({'success': True})
        except Coupon.DoesNotExist:
            return JsonResponse({'success': False})

@csrf_exempt
@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_coupon(request):
    if request.method == 'POST':
        coupon_id = request.POST.get('id')
        try:
            coupon = Coupon.objects.get(id=coupon_id)
            coupon.delete()
            return JsonResponse({'success': True})
        except Coupon.DoesNotExist:
            return JsonResponse({'success': False})
        
@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def control_coupon_status(request):
    coupon_id = request.POST.get('id')
    is_active = request.POST.get('active') == 'true'
    
    try:
        coupon = Coupon.objects.get(id=coupon_id)
        coupon.active = is_active
        coupon.save()
        return JsonResponse({'success': True})
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@login_required
@user_passes_test(lambda u: u.is_superuser)
@user_passes_test(lambda u: u.is_superuser)
def offer_list(request):
    offers = Offer.objects.all().order_by('-valid_from')  # Fetch all offers, sorted by valid_from date
    context = {
        'offers': offers,
    }
    return render(request, 'Offer.html', context)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_offer(request):
    try:
        name = request.POST.get('name')
        discount = request.POST.get('discount')
        valid_from = request.POST.get('valid_from')
        valid_to = request.POST.get('valid_to')
        description = request.POST.get('description')
        is_active = request.POST.get('is_active') == 'on'

        # Validate input
        if not name or not discount or not valid_from or not valid_to:
            return JsonResponse({'success': False, 'message': 'All fields are required.'}, status=400)

        # Create the offer
        Offer.objects.create(
            name=name,
            discount=discount,
            valid_from=valid_from,
            valid_to=valid_to,
            description=description,
            is_active=is_active
        )
        return JsonResponse({'success': True, 'message': 'Offer added successfully!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
    

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def update_product_offer(request):
    product_id = request.POST.get('product_id')
    offer_id = request.POST.get('offer_id')
    
    product = get_object_or_404(Product, id=product_id)
    
    if offer_id:
        offer = get_object_or_404(Offer, id=offer_id)
        product.offer = offer
    else:
        product.offer = None
    
    product.save()
    
    return JsonResponse({
        'success': True,
        'message': f"Offer updated successfully for product: {product.name}"
    })

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def update_category_offer(request):
    category_id = request.POST.get('category_id')
    offer_id = request.POST.get('offer_id')
    action = request.POST.get('action')

    try:
        category = get_object_or_404(Category, id=category_id)

        if action == 'update':
            offer = get_object_or_404(Offer, id=offer_id)
            category.offer = offer
            category.save()
            message = f'Offer "{offer.name}" has been successfully applied to category "{category.name}".'
        elif action == 'remove':
            old_offer_name = category.offer.name if category.offer else "No offer"
            category.offer = None
            category.save()
            message = f'Offer has been successfully removed from category "{category.name}". Previous offer was "{old_offer_name}".'
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid action specified.'
            }, status=400)

        return JsonResponse({
            'success': True,
            'message': message
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=400)
        

from django.db.models import F

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def show_sales_details(request):
    return render(request, 'sales_report.html')

def get_filtered_sales_data(request):
    report_type = request.GET.get('report_type', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    now = timezone.now()
    if report_type == 'daily':
        start_date = now.date()
        end_date = start_date + timedelta(days=1)
    elif report_type == 'weekly':
        start_date = now.date() - timedelta(days=now.weekday())
        end_date = start_date + timedelta(weeks=1)
    elif report_type == 'monthly':
        start_date = now.replace(day=1).date()
        end_date = (start_date + timedelta(days=32)).replace(day=1)
    elif report_type == 'yearly':
        start_date = now.replace(day=1, month=1).date()
        end_date = start_date.replace(year=start_date.year + 1)
    elif report_type == 'custom' and start_date and end_date:
        start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date() + timedelta(days=1)
    else:
        start_date = Order.objects.earliest('created_at').created_at.date()
        end_date = now.date() + timedelta(days=1)

    orders = Order.objects.filter(created_at__range=[start_date, end_date])

    sales = orders.annotate(
        total_items=Sum('ordered_items__quantity'),
        total_discount=Sum('ordered_items__quantity') * F('discount_amount_coupon')
    ).values(
        'id', 'created_at', 'payment_method', 'user__username', 
        'total_price', 'coupon', 'discount_amount_coupon', 'status',
        'total_items', 'total_discount'
    )

    for sale in sales:
        sale['created_at'] = sale['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        sale['total_price'] = float(sale['total_price'])
        sale['discount_amount_coupon'] = float(sale['discount_amount_coupon'])
        sale['total_discount'] = float(sale['total_discount'])

    summary = orders.aggregate(
        sales_count=Count('id'),
        order_amount=Sum('total_price'),
        total_discount=Sum('discount_amount_coupon'),
    )

    summary['order_amount'] = float(summary['order_amount'] or 0)
    summary['total_discount'] = float(summary['total_discount'] or 0)

    data = {
        'sales': list(sales),
        'summary': summary,
    }
    return JsonResponse(data)
        
        
# def show_sales_details(request):
#     return render(request,'sales_report.html')


# def show_sales_details(request):
#     return render(request, 'sales_report.html')

# def get_filtered_sales_data(request):
#     report_type = request.GET.get('report_type', 'all')  # Default to 'all' if not provided
#     start_date = request.GET.get('start_date')
#     end_date = request.GET.get('end_date')

#     if report_type == 'daily':
#         start_date = timezone.now().date()
#         end_date = start_date + timedelta(days=1)
#     elif report_type == 'weekly':
#         start_date = timezone.now() - timedelta(days=timezone.now().weekday())
#         end_date = start_date + timedelta(weeks=1)
#     elif report_type == 'monthly':
#         start_date = timezone.now().replace(day=1)
#         end_date = (start_date + timedelta(days=32)).replace(day=1)
#     elif report_type == 'yearly':
#         start_date = timezone.now().replace(day=1, month=1)
#         end_date = (start_date + timedelta(days=366)).replace(day=1, month=1)
#     elif report_type == 'custom' and start_date and end_date:
#         start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
#         end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
#     else:
#         # If 'all' is selected, fetch all sales data without filtering by date
#         orders = Order.objects.all()
#         print('hi mirshad')

#     # If start_date and end_date are set, filter by date range
#     if start_date and end_date:
#         orders = Order.objects.filter(created_at__date__range=[start_date, end_date])

#     sales = orders.values(
#         'id', 'created_at', 'payment_method', 'user__username', 'original_price', 'coupon', 
#         'discount_amount_coupon', 'total_price'
#     )

#     summary = orders.aggregate(
#         sales_count=Count('id'),
#         order_amount=Sum('total_price'),
#         total_discount=Sum('discount_amount_coupon'),
#     )

#     data = {
#         'sales': list(sales),
#         'summary': summary,
#     }
#     return JsonResponse(data)

# def get_filtered_sales_data(request):
#     report_type = request.GET.get('report_type', 'daily')
#     start_date = request.GET.get('start_date')
#     end_date = request.GET.get('end_date')

#     if report_type == 'daily':
#         start_date = timezone.now().date()
#         end_date = start_date + timedelta(days=1)
#     elif report_type == 'weekly':
#         start_date = timezone.now() - timedelta(days=timezone.now().weekday())
#         end_date = start_date + timedelta(weeks=1)
#     elif report_type == 'monthly':
#         start_date = timezone.now().replace(day=1)
#         end_date = (start_date + timedelta(days=32)).replace(day=1)
#     elif report_type == 'yearly':
#         start_date = timezone.now().replace(day=1, month=1)
#         end_date = (start_date + timedelta(days=366)).replace(day=1, month=1)
#     elif report_type == 'custom' and start_date and end_date:
#         start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
#         end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()

#     orders = Order.objects.filter(created_at__date__range=[start_date, end_date])
#     sales = orders.values(
#         'id', 'created_at', 'payment_method', 'user__username', 'original_price', 'coupon', 
#         'discount_amount_coupon', 'total_price'
#     )

#     summary = orders.aggregate(
#         sales_count=Count('id'),
#         order_amount=Sum('total_price'),
#         total_discount=Sum('discount_amount_coupon'),
#     )

#     data = {
#         'sales': list(sales),
#         'summary': summary,
#     }
#     return JsonResponse(data)
