from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import random
import time
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login , logout
from django.contrib import messages
from products.models import *
from . models import *
import re
from django.views.decorators.cache import never_cache
from django.db.models import Q
from django.urls import reverse
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.http import require_POST
# Create your views here.

import os

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from google.oauth2 import id_token
from google.auth.transport import requests

@csrf_exempt
def auth_receiver(request):
    """
    Google calls this URL after the user has signed in with their Google account.
    """
    print('Inside')
    token = request.POST['credential']

    try:
        user_data = id_token.verify_oauth2_token(
            token, requests.Request(), os.environ['GOOGLE_OAUTH_CLIENT_ID']
        )
    except ValueError:
        return HttpResponse(status=403)

    # In a real app, I'd also save any new user here to the database.
    # You could also authenticate the user here using the details from Google (https://docs.djangoproject.com/en/4.2/topics/auth/default/#how-to-log-a-user-in)
    request.session['user_data'] = user_data

    return redirect('sign_in')


def store(request):
    if request.user.is_authenticated:
        return redirect(home)
    
    all_products = Product.objects.all()
    categories = Category.objects.all()
    genders = Gender.objects.all()
    brands = Brand.objects.all()

    context = {
        'products': all_products,
        'categories': categories,
        'genders': genders,
        'brands': brands,
    }
    
    return render(request,'store/store.html',context)


def check_username(request):
    username = request.GET.get('username', None)
    data = {
        'exists': User.objects.filter(username__iexact=username).exists()
    }
    return JsonResponse(data)



def check_email(request):
    email = request.GET.get('email', None)
    data = {
        'exists': User.objects.filter(email__iexact=email).exists()
    }
    return JsonResponse(data)


def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        phone_number = request.POST.get('phone_number')
        
        context = {
            'username': username,
            'email': email,
            'phone_number': phone_number,
            'errors': {},
        }
        
        errors = {}
        
        if not username:
            errors['username'] = 'Username is required'
        elif len(username) < 3:
            errors['username'] = 'Username must be at least 3 characters long'
        elif len(username) > 12:
            errors['username'] = 'Username must be 12 characters below'
        elif not re.match(r'^[a-zA-Z0-9_]*$', username):
            errors['username'] = 'Username can only contain alphanumeric characters and underscores'
        elif User.objects.filter(username=username).exists():
            errors['username'] = 'Username already exists'
        
    
        if not email:
            errors['email'] = 'Email is required'
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            errors['email'] = 'Invalid email format'
        
        if not phone_number:
            errors['phone_number'] = 'Phone number is required'
        elif not re.match(r'^\+?1?\d{9,15}$', phone_number):
            errors['phone_number'] = 'Invalid phone number format'

        if not password:
            errors['password'] = 'Password is required'
        elif len(password) < 8:
            errors['password'] = 'Password must be at least 8 characters long'
        elif len(password) > 128:
            errors['password'] = 'Password must be 128 characters or fewer'
        elif not re.search(r'[A-Z]', password):
            errors['password'] = 'Password must contain at least one uppercase letter'
        elif not re.search(r'[a-z]', password):
            errors['password'] = 'Password must contain at least one lowercase letter'
        elif not re.search(r'\d', password):
            errors['password'] = 'Password must contain at least one digit'
        elif not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors['password'] = 'Password must contain at least one special character'
        
        if errors:
            context['errors'] = errors
            return render(request, 'store/register.html', context)

    
        otp = str(random.randint(100000, 999999))
   
        request.session['registration_data'] = {
            'username': username,
            'email': email,
            'password': password,
            'phone_number': phone_number,
            'otp': otp,
            'otp_created_at': timezone.now().isoformat()
        }
        
        try:
            subject = 'Your OTP for registration'
            message = f'Your OTP is: {otp}. This OTP is valid for 5 minutes.'
            from_email = settings.EMAIL_HOST_USER
            recipient_list = [email]
            send_mail(subject, message, from_email, recipient_list)
            print('worked')
        except:
            print('find error')
       
     
        stored_data = request.session.get('registration_data')
        print(stored_data)
       
        return redirect('validate_otp')
   
    return render(request, 'store/register.html')

def validate_otp(request):
    if request.method == "POST":
        user_otp = request.POST.get('otp')
        stored_data = request.session.get('registration_data', {})
        print(user_otp,stored_data)

        if not stored_data:
            return redirect('register')

        otp_created_at = timezone.datetime.fromisoformat(stored_data.get('otp_created_at'))
        time_elapsed = (timezone.now() - otp_created_at).total_seconds()

        if time_elapsed > 300:  
            del request.session['registration_data']
            return render(request, 'store/validateOTP.html', {'error': 'OTP has expired. Please try again.'})
        
        if user_otp == stored_data.get('otp'):
            try:
                existing_user = User.objects.filter(email=stored_data['email']).first()
                if existing_user:
                    return render(request, 'store/validateOTP.html', {'error': 'An account with this email already exists.'})
                
             
                new_user = User.objects.create_user(
                    username=stored_data['username'],
                    email=stored_data['email'],
                    password=stored_data['password']
                )
                new_user.save()
                
                Profile.objects.create(user=new_user, phone=stored_data['phone_number'])

                return redirect('login')
            except IntegrityError:
                return render(request, 'store/validateOTP.html', {'error': 'An error occurred while creating your account. Please try again.'})
        else:
            return render(request, 'store/validateOTP.html', {'error': 'Invalid OTP'})
        
    
    return render(request, 'store/validateOTP.html')

def resend_otp(request):
    stored_data = request.session.get('registration_data', {})
    if not stored_data:
        return redirect('register')

    
    new_otp = str(random.randint(100000, 999999))

  
    send_mail(
        'Your new OTP for registration',
        f'Your new OTP is: {new_otp}. This OTP will expire in 5 minutes.',
        settings.EMAIL_HOST_USER,
        [stored_data['email']],
        fail_silently=False,
    )

  
    stored_data['otp'] = new_otp
    stored_data['otp_created_at'] = timezone.now().isoformat()
    request.session['registration_data'] = stored_data

    return redirect('validate_otp')

# @login_required
def home(request):
    if request.user.is_authenticated:  
        all_products = Product.objects.filter(category__status=True)
        categories = Category.objects.filter(status=True)
        genders = Gender.objects.all()
        brands = Brand.objects.all()

        context = {
            'products': all_products,
            'categories': categories,
            'genders': genders,
            'brands': brands,
        }
        return render(request, 'store/home.html', context)
        
    all_products = Product.objects.filter(category__status=True)
    categories = Category.objects.filter(status=True)
    genders = Gender.objects.all()
    brands = Brand.objects.all()
         
    context = {
        'products': all_products,
        'categories': categories,
        'genders': genders,
        'brands': brands,
    }
        
    return render(request,'store/store.html',context)
    
@never_cache
def loginpage(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            messages.error(request, 'username and password are required.')
            return render(request, 'store/login.html')


        user = authenticate(request, username=username, password=password)
        print(user)

        if user is not None:
            if not user.is_active:
                messages.error(request, 'Your account is blocked. Please contact us.')
                return render(request, 'store/login.html')
            
            login(request, user)
            if user.is_staff:  
                return render(request, 'store/login.html', {'show_admin_modal': True})
            else:
                return redirect('home') 
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'store/login.html')






def check_username(request):
    username = request.GET.get('username', None)
    data = {
        'exists': User.objects.filter(username=username).exists()
    }
    return JsonResponse(data)
def logoutPage(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect('login') 








def social_login_success(request):
    if request.user.is_authenticated:
        messages.success(request, 'Successfully logged in with Google!')
        return redirect('store')
    else:
        messages.error(request, 'Social login failed. Please try again.')
        return redirect('login') 
    
def social_login_success(request):
    if request.user.is_authenticated:
        messages.success(request, 'Successfully logged in with Google!')
        return redirect('store')
    else:
        messages.error(request, 'Social login failed. Please try again.')
        return redirect('login') 
    
def show_products(request):
    # products = Product.objects.all()
    products = Product.objects.filter(category__status=True)
    
    category = request.GET.get('category')
    if category:
        products = Product.objects.filter(category__name=category)
    
    gender = request.GET.get('gender')
    if gender:
        products = Product.objects.filter(gender__name=gender)
        
    brand = request.GET.get('brand')
    if brand:
        products = products.filter(brand__name=brand)

    color = request.GET.get('color')
    if color:
        products = products.filter(variants__color__name=color).distinct()
        
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price and max_price:
        products = products.filter(variants__price__gte=min_price, variants__price__lte=max_price).distinct()
    
    categories = Category.objects.filter(status=True)
    genders = Gender.objects.all()
    brands = Brand.objects.all()
    colors = Color.objects.all()

    context = {
        'products': products,
        'categories': categories,
        'genders': genders,
        'brands': brands,
        'colors': colors,
    }
    
    return render(request, 'store/products_home.html', context)

# def product_info(request, id):
#     product = get_object_or_404(Product, id=id)
#     return render(request, 'store/product_info.html', {'product': product})

def product_info(request, id):
    product = get_object_or_404(Product, id=id)
    variants = product.variants.all()

    cart_count = 0

    # Check if the user is authenticated
    if request.user.is_authenticated:
        user = request.user
        cart_count = CartItem.objects.filter(cart__user=user).count()

    # Check if the user has selected a specific variant
    variant_id = request.GET.get('variant_id')
    if variant_id:
        selected_variant = get_object_or_404(ProductVariant, id=variant_id)
    else:
        selected_variant = product.variants.first()

    return render(request, 'store/product_info.html', {
        'product': product,
        'variants': variants,
        'selected_variant': selected_variant,
        'cart_count': cart_count
    })

# def product_info(request, id):
#     product = get_object_or_404(Product, id=id)
#     variants = product.variants.all()
#     user = request.user
#     cart_count = CartItem.objects.filter(cart__user=user).count()
#     print(cart_count)
    

#     # Check if the user has selected a specific variant
#     variant_id = request.GET.get('variant_id')
#     if variant_id:
#         selected_variant = get_object_or_404(ProductVariant, id=variant_id)
#     else:
#         selected_variant = product.variants.first()

#     return render(request, 'store/product_info.html', {
#         'product': product,
#         'variants': variants,
#         'selected_variant': selected_variant,
#         'cart_count':cart_count
#     })

@login_required
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('variant__product', 'variant__color')
    
    context = {
        'wishlist_items': wishlist_items
    }
    return render(request, 'store/wishlist.html', context)

# def add_wishlist(request,id):
#     product = get_object_or_404(Product, id=id)
    
#     # Check if the product is already in the user's wishlist
#     wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
#     # Get the URL of the previous page from the request headers
#     previous_page = request.META.get('HTTP_REFERER', 'store')  # Default to 'home' if HTTP_REFERER is not set

#     # Redirect back to the previous page
#     return redirect(previous_page)

@login_required
def add_wishlist(request, id):
    if request.method == 'POST':
        variant_id = request.POST.get('variant_id')
        variant = get_object_or_404(ProductVariant, id=variant_id, product_id=id)
        
        try:
            Wishlist.objects.create(user=request.user, variant=variant)
            # messages.success(request, f"{variant.product.name} ({variant.color.name}) added to your wishlist.")
        except IntegrityError:
            messages.info()
        # request, f"{variant.product.name} ({variant.color.name}) is already in your wishlist."
        return redirect('product_info',   id=id)
    
    return redirect('home')

# def remove_wishlist(request,id):
#     product = get_object_or_404(Product,id=id)
    
#     try:
#         item = Wishlist.objects.get(user=request.user,product=product)
#         item.delete()
#     except wishlist.DoesNotExist:
#         print('error in remove product')

#     previous_page = request.META.get('HTTP_REFERER', 'store')  # Default to 'home' if HTTP_REFERER is not set
#     # Redirect back to the previous page
#     return redirect(previous_page)

def remove_wishlist(request, id):
    if request.method == 'POST':
        try:
            wishlist_item = Wishlist.objects.get(user=request.user, variant_id=id)
            wishlist_item.delete()
            return JsonResponse({'success': True})
        except Wishlist.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Item not found in wishlist'}, status=404)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)
    
@login_required
def cart(request):

    cart = Cart.objects.get(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart)
    
    delete_cartitem = []
    
    for item in cart_items:
        product_variant = item.product_variant
        
        if not product_variant.is_available:
            delete_cartitem.append(item)
            messages.warning(request, f"{product_variant.product.name} - {product_variant.color} is out of stock and {product_variant.product.name} removed from your cart.")
            continue
        if item.quantity > 10:
            item.quantity = 10
            item.save()
            messages.warning(request,f"Sorry, you can only buy 10 products for each products!!! {product_variant.product.name}")
        
        if item.quantity > product_variant.stock:
            if product_variant.stock > 0:
                item.quantity = product_variant.stock
                item.save()
                messages.warning(request, f"Quantity for {product_variant.product.name} - {product_variant.color} has been adjusted to the available stock of {product_variant.stock}.")
            else:
                delete_cartitem.append(item)
                messages.warning(request, f"{product_variant.product.name} - {product_variant.color} is out of stock and has been removed from your cart.")
        
    
    for item in delete_cartitem:
        item.delete()
        

    cart_items = CartItem.objects.filter(cart=cart)
    cart_total = sum(item.get_total_price() for item in cart_items)
    print(cart_total)
    context = {
        'cart_items': cart_items,
        'cart_total': cart_total,
    }
    return render(request, 'store/cart.html', context)
    
# def add_to_cart(request, id):
#     if request.method == 'POST':
#         variant_id = request.POST.get('variant_id')
#         quantity = int(request.POST.get('quantity', 1))
        
#         variant = get_object_or_404(ProductVariant, id=variant_id)
        
#         if not variant.is_available or variant.stock < quantity:
#             messages.error(request, "Sorry, this product is out of stock or the requested quantity exceeds available stock.")
#             return redirect(request.META.get('HTTP_REFERER', 'home'))
        
#         # Get or create the user's cart
#         cart, created = Cart.objects.get_or_create(user=request.user)
        
#         # Check if the item is already in the cart
#         cart_item, item_created = CartItem.objects.get_or_create(
#             cart=cart,
#             product_variant=variant,
#             defaults={'quantity': quantity}
#         )
        
#         if not item_created:
#             # If the item was already in the cart, update the quantity
#             cart_item.quantity += quantity
#             cart_item.save()
        
#         messages.success(request, f"{variant.product.name} has been added to your cart.")
#         return redirect(request.META.get('HTTP_REFERER', 'home'))
#         # return redirect('home')  # Or wherever you want to redirect after adding to cart
    
#     return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def add_to_cart(request, id):
    if request.method == 'POST':
        variant_id = request.POST.get('variant_id')
        quantity = int(request.POST.get('quantity', 1))
        
        variant = get_object_or_404(ProductVariant, id=variant_id)
        
        if not variant.is_available or variant.stock < quantity:
            return JsonResponse({
                'success': False,
                'error': "Sorry, this product is out of stock or the requested quantity exceeds available stock."
            })
        
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product_variant=variant,
            defaults={'quantity': quantity}
        )
        
        if not item_created:
            cart_item.quantity += quantity
            cart_item.save()
        return redirect(request.META.get('HTTP_REFERER', 'home'))
        return JsonResponse({
            'success': True,
            'message': f"{variant.product.name} has been added to your cart."
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})




def update_cart(request, cart_item_id):
    if request.method == 'POST':
        try:
            # Get the cart item, ensuring it belongs to the current user
            cart_item = CartItem.objects.get(id=cart_item_id, cart__user=request.user)
            quantity = int(request.POST.get('quantity', 1))
            
            # Update the quantity
            cart_item.quantity = quantity
            cart_item.save()
            
            # Calculate the new totals
            item_total = cart_item.get_total_price()
            cart_total = sum(item.get_total_price() for item in cart_item.cart.items.all())
            
            return JsonResponse({
                'success': True,
                'item_total': item_total,
                'cart_total': cart_total,
            })
        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cart item not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})


def remove_cart(request, id):
    if request.method == 'POST':
        try:
            cart_item = CartItem.objects.get(id=id, cart__user=request.user)
            cart_item.delete()
            
            # Recalculate cart total
            cart = Cart.objects.get(user=request.user)
            cart_total = sum(item.get_total_price() for item in cart.items.all())
            
            return JsonResponse({
                'success': True,
                'cart_total': float(cart_total)
            })
        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Item not found in cart'}, status=404)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)


def account(request):
    user  = request.user
    orders = Order.objects.filter(user=user).order_by('-created_at')
    
    order_items = OrderItem.objects.filter(order__in=orders)
    
    profile = Profile.objects.get(user=user)
    
    
    context = {
        'user': request.user,
        'orders': orders,
        'order_items': order_items,
        'profile': profile,

    }
    return render(request,'store/Account.html',context)


def submit_address(request):
    if request.method == 'POST':
        # Create a new UserAddress instance
        
        street_1 = request.POST.get('address_line_1')
        street_2 = request.POST.get('address_line_2','')
        
        check = UserAddress.objects.filter(
            user = request.user,
            address_line_1 = street_1,
            address_line_2 = street_2,
        ).exists()
        

        if check:
            print('exists')
            messages.error(request,"Sorry, the address already exists !!!")
            return redirect('account')

        
        
        address = UserAddress(
            user=request.user,
            full_name=request.POST.get('full_name'),
            last_name=request.POST.get('last_name'),
            phone_number=request.POST.get('phone_number'),
            email=request.POST.get('email'),
            address_line_1=request.POST.get('address_line_1'),
            address_line_2=request.POST.get('address_line_2'),
            city=request.POST.get('city'),
            state=request.POST.get('state'),
            postal_code=request.POST.get('postal_code'),
            country=request.POST.get('country'),
            is_default=request.POST.get('is_default') == 'on'
        )
        
        print(address)
        address.save()
        messages.success(request,"Address created successfully!!!")
        
        if address.is_default:
            UserAddress.objects.filter(user=request.user).exclude(id=address.id).update(is_default=False)

        return redirect('account') 
    return redirect('account',)

def edit_address(request,id):
    address = get_object_or_404(UserAddress, id=id, user=request.user)
    
    if request.method == 'POST':
        # Update the address
        address.full_name = request.POST.get('full_name')
        address.last_name = request.POST.get('last_name')
        address.phone_number = request.POST.get('phone_number')
        address.email = request.POST.get('email')
        address.country = request.POST.get('country')
        address.address_line_1 = request.POST.get('address_line_1')
        address.address_line_2 = request.POST.get('address_line_2')
        address.city = request.POST.get('city')
        address.state = request.POST.get('state')
        address.postal_code = request.POST.get('postal_code')
        
        address.save()
        messages.success(request, "Address updated successfully.")
        return redirect('account')  # Redirect to the account page
    
    return render(request,'store/edit_address.html',{'address': address})


def delete_address(request, address_id):
    try:
        address = UserAddress.objects.get(id=address_id, user=request.user)
        address.delete()
        return JsonResponse({'status': 'success', 'message': 'Address deleted successfully.'})
    except UserAddress.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Address not found.'}, status=404)
    
# def checkout(request):
#     user = request.user
#     cart = Cart.objects.get(user=user)
#     cart_items = cart.items.all()
#     cart_total = cart.get_total_price()
    
#     if request.method == 'POST':
#         checker = True
#         for item in cart_items:
#             product = item.product_variant
            
#             print(product)
#             if not product.is_available:
#                 messages.error(request, f"{product.product.name} - {product.color} is no longer available.")
#                 checker = False
#                 continue
            
#             if item.quantity > product.stock:
#                 print('hi')
#                 messages.error(request, f"Sorry, we only have {product.stock} of {product.product.name} - {product.color} in stock.")
#                 checker = False
#                 continue
            
#             if checker:
#                 return redirect('order_confirmation', order_id=15)
#             else:
#                 return redirect('home')
            
        
#         payment_method = request.POST.get('payment_method', 'cod')
        
#         order = Order.objects.create(
#             user=user,
#             status='pending',
#             total_price=cart_total,
#             payment_method=payment_method
#         )

#         use_new_address = request.POST.get('use_new_address')

#         if use_new_address:
#             full_name = request.POST.get('full_name')
#             last_name = request.POST.get('last_name')
#             phone_number = request.POST.get('phone_number')
#             email = request.POST.get('email')
#             address_line_1 = request.POST.get('address_line_1')
#             address_line_2 = request.POST.get('address_line_2')
#             city = request.POST.get('city')
#             state = request.POST.get('state')
#             postal_code = request.POST.get('postal_code')
#             country = request.POST.get('country')

#             order_address = OrderAddress.objects.create(
#                 order=order,
#                 full_name=full_name,
#                 last_name=last_name,
#                 phone_number=phone_number,
#                 email=email,
#                 address_line_1=address_line_1,
#                 address_line_2=address_line_2,
#                 city=city,
#                 state=state,
#                 postal_code=postal_code,
#                 country=country
#             )
#         else:
#             selected_address_id = request.POST.get('selected_address')
#             selected_address = user.addresses.get(id=selected_address_id)

#             order_address = OrderAddress.objects.create(
#                 order=order,
#                 full_name=selected_address.full_name,
#                 last_name=selected_address.last_name,
#                 phone_number=selected_address.phone_number,
#                 email=selected_address.email,
#                 address_line_1=selected_address.address_line_1,
#                 address_line_2=selected_address.address_line_2,
#                 city=selected_address.city,
#                 state=selected_address.state,
#                 postal_code=selected_address.postal_code,
#                 country=selected_address.country
#             )
def checkout(request):
    user = request.user
    cart = Cart.objects.get(user=user)
    cart_items = cart.items.all()
    cart_total = cart.get_total_price()
    
    if request.method == 'POST':
        checker = True
        for item in cart_items:
            product_variant = item.product_variant
            
            if not product_variant.is_available:
                messages.error(request, f"{product_variant.product.name} - {product_variant.color} is not available.sorry !!!")
                checker = False
                continue
            
            if item.quantity > product_variant.stock:
                messages.error(request, f"Sorry, we only have {product_variant.stock} of {product_variant.product.name} - {product_variant.color} in stock.")
                checker = False
                continue
            
        
        if not checker:
            return redirect('checkout')
        
        payment_method = request.POST.get('payment_method', 'cod')
        
        order = Order.objects.create(
            user=user,
            status='pending',
            total_price=cart_total,
            payment_method=payment_method
        )

        use_new_address = request.POST.get('use_new_address')

        if use_new_address:
            order_address = OrderAddress.objects.create(
                order=order,
                full_name=request.POST.get('full_name'),
                last_name=request.POST.get('last_name'),
                phone_number=request.POST.get('phone_number'),
                email=request.POST.get('email'),
                address_line_1=request.POST.get('address_line_1'),
                address_line_2=request.POST.get('address_line_2'),
                city=request.POST.get('city'),
                state=request.POST.get('state'),
                postal_code=request.POST.get('postal_code'),
                country=request.POST.get('country')
            )
        else:
            selected_address_id = request.POST.get('selected_address')
            selected_address = user.addresses.get(id=selected_address_id)

            order_address = OrderAddress.objects.create(
                order=order,
                full_name=selected_address.full_name,
                last_name=selected_address.last_name,
                phone_number=selected_address.phone_number,
                email=selected_address.email,
                address_line_1=selected_address.address_line_1,
                address_line_2=selected_address.address_line_2,
                city=selected_address.city,
                state=selected_address.state,
                postal_code=selected_address.postal_code,
                country=selected_address.country
            )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product_variant=item.product_variant,
                quantity=item.quantity,
                price=item.product_variant.price
            )
            
            item.product_variant.stock = item.product_variant.stock - item.quantity
            item.product_variant.save()

    
        cart.items.all().delete()

        return redirect('order_confirmation', order_id=order.id)

    context = {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'user': user,
    }
    return render(request, 'store/checkout.html', context)





def order_confirmation(request, order_id):
    
    order = Order.objects.get(id=order_id)
    context = {
        'order': order,
    }
    return render(request, 'store/order_confirmation.html', context)


def show_order_details(request,order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order)
    order_address = order.order_address

    context = {
        'order': order,
        'order_items': order_items,
        'order_address': order_address,
    }
    return render(request,'store/ordered_product_info.html',context)

@require_POST
def edit_details(request):
    user = request.user
    profile = Profile.objects.get(user=user)


    username = request.POST.get('username')
    last_name = request.POST.get('last_name')
    email = request.POST.get('email')
    phone_number = request.POST.get('phone_number')
    current_password = request.POST.get('current_password')
    new_password = request.POST.get('new_password')
    confirm_new_password = request.POST.get('confirm_new_password')
    
    user.username = username
    user.last_name = last_name
    user.email = email
    user.save()
    
    profile.phone = phone_number
    profile.save()
    
    if current_password and new_password and confirm_new_password:
        if user.check_password(current_password):
            if new_password == confirm_new_password:
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)  # Prevent logout after password change
                messages.success(request, 'Your password was successfully updated!')
            else:
                messages.error(request, 'New passwords do not match.')
        else:
            messages.error(request, 'Current password is incorrect.')

    messages.success(request, 'Your profile was successfully updated!')
    
    return redirect(request.META.get('HTTP_REFERER', 'home'))


        
