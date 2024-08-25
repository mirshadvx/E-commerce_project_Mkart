from django.db import IntegrityError
from django.shortcuts import render, redirect , get_object_or_404
from django.urls import reverse
from django.utils.text import slugify
from products.models import Category , Brand, Color, Gender, Product , ProductVariant
from django.contrib import messages
from django.http import JsonResponse
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

# Create your views here.

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
    return render(request, 'categoryList.html', {'categories': categories})

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
def products_list(request):
    products = Product.objects.prefetch_related('variants', 'variants__color').all() 
    return render(request, 'productsList.html', {'products': products})


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


def logout_admin(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect(reverse('login'))


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



def update_order_item_status(request):
    
    if request.method == 'POST':
        print('workeddddd')
        item_id = request.POST.get('item_id')
        new_status = request.POST.get('new_status')

        try:
            order_item = OrderItem.objects.get(id=item_id)
            if order_item.update_status(new_status):
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Invalid status transition.'})
        except OrderItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Order item not found.'})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})
