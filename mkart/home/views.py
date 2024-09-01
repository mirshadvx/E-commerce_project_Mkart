from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
# from django.utils import timezone
import random
import time
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login , logout
from django.contrib import messages
from requests import request
from products.models import *
from . models import *
import re
from django.views.decorators.cache import never_cache
from django.db.models import Q
from django.urls import reverse
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.http import require_POST
from allauth.socialaccount.models import SocialAccount
import razorpay
from django.conf import settings
from decimal import Decimal
from Admin.models import *
from django.utils import timezone as django_timezone
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
    # if request.user.is_authenticated:
    #     # Check if the user is authenticated via Google
    #     if SocialAccount.objects.filter(user=request.user, provider='google').exists():
    #         return redirect('home')
        
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

from django.db.models import Min

def show_products(request):
    products = Product.objects.filter(category__status=True)
    
    # Filter by category, gender, brand, color, and price range as before
    category = request.GET.get('category')
    if category:
        products = products.filter(category__name=category)
    
    gender = request.GET.get('gender')
    if gender:
        products = products.filter(gender__name=gender)
    
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
    
    # Sort products based on the selected criteria
    sort_by = request.GET.get('sortby')
    if sort_by:
        if sort_by == 'low to high':
            products = products.annotate(min_price=Min('variants__price')).order_by('min_price')
        elif sort_by == 'high to low':
            products = products.annotate(min_price=Min('variants__price')).order_by('-min_price')
        elif sort_by == 'new arrivals':
            products = products.order_by('-created_at')
        elif sort_by == 'aA-zZ':
            products = products.order_by('name')
        elif sort_by == 'zZ-aA':
            products = products.order_by('-name')
    
    # Calculate discounted prices and pass to the template
    for product in products:
        variant = product.variants.first()  # Assuming you want to use the first variant
        if variant:
            product.display_price = variant.price
            product.discounted_price = product.get_discounted_price()
            if product.discounted_price < variant.price:
                product.discount_percentage = 100 * (1 - product.discounted_price / variant.price)
            else:
                product.discount_percentage = None
    
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
        'sort_by': sort_by,
    }
    
    return render(request, 'store/products_home.html', context)


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

    # Get the original and discounted prices
    original_price = selected_variant.price
    discounted_price = product.get_discounted_price()

    # Determine which offer is active (if any)
    active_offer = None
    if product.offer and product.offer.is_active and product.offer.valid_from <= timezone.now() <= product.offer.valid_to:
        active_offer = product.offer
    elif product.category.offer and product.category.offer.is_active and product.category.offer.valid_from <= timezone.now() <= product.category.offer.valid_to:
        active_offer = product.category.offer

    context = {
        'product': product,
        'variants': variants,
        'selected_variant': selected_variant,
        'cart_count': cart_count,
        'active_offer': active_offer,
        'original_price': original_price,
        'discounted_price': discounted_price,
    }

    return render(request, 'store/product_info.html', context)

@login_required
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('variant__product', 'variant__color')
    
    context = {
        'wishlist_items': wishlist_items
    }
    return render(request, 'store/wishlist.html', context)


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
            messages.warning(request, f"{product_variant.product.name} - {product_variant.color} is out of stock and has been removed from your cart.")
            continue
        if item.quantity > 10:
            item.quantity = 10
            item.save()
            messages.warning(request, f"Sorry, you can only buy 10 units of {product_variant.product.name}. Quantity has been adjusted to 10.")
        
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
    
    context = {
        'cart_items': cart_items,
        'cart_total': cart_total,
    }
    return render(request, 'store/cart.html', context)
    

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
            cart_item = CartItem.objects.get(id=cart_item_id, cart__user=request.user)
            quantity = int(request.POST.get('quantity', 1))
            
            cart_item.quantity = quantity
            cart_item.save()
            
            item_total = cart_item.get_total_price()  # This will now include the discount
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
    user = request.user
    orders = Order.objects.filter(user=user).order_by('-created_at')
    profile = Profile.objects.get(user=user)

    context = {
        'user': user,
        'orders': orders,
        'profile': profile,
    }
    return render(request, 'store/Account.html', context)


def submit_address(request):
    if request.method == 'POST':
        
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
        return redirect('account')
    
    return render(request,'store/edit_address.html',{'address': address})


def delete_address(request, address_id):
    try:
        address = UserAddress.objects.get(id=address_id, user=request.user)
        address.delete()
        return JsonResponse({'status': 'success', 'message': 'Address deleted successfully.'})
    except UserAddress.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Address not found.'}, status=404)

@login_required
def checkout(request):
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)
    except Cart.DoesNotExist:
        cart = None
        cart_items = []

    if not cart_items:
        messages.warning(request, "Your cart is empty. Add some items before checking out.")
        return redirect('cart')

    subtotal = sum(item.get_total_price() for item in cart_items)
    coupon = request.session.get('coupon')
    coupon_discount = Decimal('0.00')

    if coupon:
        try:
            coupon_obj = Coupon.objects.get(code=coupon)
            if coupon_obj.is_valid() and coupon_obj.can_use():
                coupon_discount = coupon_obj.apply_discount(subtotal)
        except Coupon.DoesNotExist:
            del request.session['coupon']

    total = subtotal - coupon_discount

    # Initialize Razorpay client
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    # Create Razorpay order
    razorpay_order = client.order.create({
        'amount': int(total * 100),  # Amount in paise
        'currency': 'INR',
        'payment_capture': '1'
    })

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'coupon_discount': coupon_discount,
        'total': total,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'razorpay_order_id': razorpay_order['id'],
        'coupon': coupon,
    }

    if request.method == 'POST':
        if 'coupon_code' in request.POST:
            return apply_coupon(request)
        elif 'remove_coupon' in request.POST:
            if 'coupon' in request.session:
                del request.session['coupon']
            messages.success(request, "Coupon removed successfully.")
            return redirect('checkout')
        else:
            # Process the order
            order = create_order(request, cart_items, total, coupon)
            
            if order:
                # Clear the cart and coupon
                cart.items.all().delete()
                if 'coupon' in request.session:
                    del request.session['coupon']
                
                messages.success(request, "Your order has been placed successfully!")
                return redirect('order_confirmation', order_id=order.id)
            else:
                messages.error(request, "There was an error processing your order. Please try again.")

    return render(request, 'store/checkout.html', context)

def validate_cart_items(request, cart_items):
    for item in cart_items:
        product_variant = item.product_variant
        
        if not product_variant.is_available:
            messages.error(request, f"{product_variant.product.name} - {product_variant.color} is not available. Sorry!")
            return False
        
        if item.quantity > product_variant.stock:
            messages.error(request, f"Sorry, we only have {product_variant.stock} of {product_variant.product.name} - {product_variant.color} in stock.")
            return False
    
    return True

def create_order(request, cart_items, total, coupon):
    order = Order.objects.create(
        user=request.user,
        total_price=total,
        payment_method=request.POST.get('payment_method'),
        coupon=coupon
    )

    # Create OrderItems
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product_variant=item.product_variant,
            quantity=item.quantity,
            price=item.product_variant.price
        )

    # Create OrderAddress
    if request.POST.get('use_new_address'):
        OrderAddress.objects.create(
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
        # Use existing address
        address_id = request.POST.get('selected_address')
        address = request.user.addresses.get(id=address_id)
        OrderAddress.objects.create(
            order=order,
            full_name=address.full_name,
            last_name=address.last_name,
            phone_number=address.phone_number,
            email=address.email,
            address_line_1=address.address_line_1,
            address_line_2=address.address_line_2,
            city=address.city,
            state=address.state,
            postal_code=address.postal_code,
            country=address.country
        )

    return order

def handle_order_address(request, order, user):
    use_new_address = request.POST.get('use_new_address')
    if use_new_address:
        # Validate new address fields
        required_fields = ['full_name', 'last_name', 'phone_number', 'email', 'address_line_1', 'city', 'state', 'postal_code', 'country']
        for field in required_fields:
            if not request.POST.get(field):
                messages.error(request, f"Please fill in the {field.replace('_', ' ')} field.")
                return False
        
        OrderAddress.objects.create(
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
        if not selected_address_id:
            messages.error(request, "Please select an address or enter a new one")
            return False
        
        try:
            selected_address = user.addresses.get(id=selected_address_id)
            OrderAddress.objects.create(
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
        except selected_address.DoesNotExist:
            messages.error(request, "The selected address is no longer available. Please choose another or enter a new one.")
            return False
    
    return True

def process_razorpay_payment(request, client, order):
    params_dict = {
        'razorpay_order_id': request.POST.get('razorpay_order_id'),
        'razorpay_payment_id': request.POST.get('razorpay_payment_id'),
        'razorpay_signature': request.POST.get('razorpay_signature')
    }
    
    try:
        client.utility.verify_payment_signature(params_dict)
        order.status = 'processing'
        order.payment_status = 'paid'
        order.razorpay_order_id = params_dict['razorpay_order_id']
        order.razorpay_payment_id = params_dict['razorpay_payment_id']
        order.save()
        return True
    except:
        messages.error(request, "Razorpay payment verification failed")
        return False

def process_cod_order(order):
    order.status = 'pending'
    order.payment_status = 'unpaid'
    order.save()

def create_order_items_and_update_stock(order, cart_items, payment_method):
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product_variant=item.product_variant,
            quantity=item.quantity,
            price=item.product_variant.price,
            item_status='processing' if payment_method == 'razorpay' else 'pending',
            payment_status_item='paid' if payment_method == 'razorpay' else 'unpaid'
        )
        
        item.product_variant.stock -= item.quantity
        item.product_variant.save()       
        
# @require_POST
# def apply_coupon(request):
#     code = request.POST.get('coupon_code')
    
#     try:
#         coupon = Coupon.objects.get(code=code)
#         cart = Cart.objects.get(user=request.user)
#         cart_total = cart.get_total_price()

#         if coupon.is_valid() and coupon.can_use():
#             if cart_total >= coupon.min_purchase_amount:
#                 discount = coupon.apply_discount(cart_total)
#                 new_total = cart_total - discount
#                 request.session['coupon'] = code
#                 coupon.increment_usage()
#                 return JsonResponse({
#                     'success': True,
#                     'message': 'Coupon applied successfully!',
#                     'new_total': str(new_total),
#                     'discount': str(discount)
#                 })
#             else:
#                 return JsonResponse({
#                     'success': False,
#                     'message': f'This coupon requires a minimum purchase of ${coupon.min_purchase_amount}.'
#                 })
#         else:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'This coupon is invalid or has expired.'
#             })
#     except Coupon.DoesNotExist:
#         return JsonResponse({
#             'success': False,
#             'message': 'Invalid coupon code.'
#         })

@require_POST
def apply_coupon(request):
    code = request.POST.get('coupon_code')
    try:
        coupon = Coupon.objects.get(code=code)
        cart = Cart.objects.get(user=request.user)
        cart_total = cart.get_total_price()

        if coupon.is_valid() and coupon.can_use():
            if cart_total >= coupon.min_purchase_amount:
                request.session['coupon'] = code
                coupon.increment_usage()
                messages.success(request, "Coupon applied successfully!")
            else:
                messages.error(request, f"This coupon requires a minimum purchase of ${coupon.min_purchase_amount}.")
        else:
            messages.error(request, "This coupon is invalid or has expired.")
    except Coupon.DoesNotExist:
        messages.error(request, "Invalid coupon code.")
    except Cart.DoesNotExist:
        messages.error(request, "No active cart found.")
    
    return redirect('checkout')

@login_required
def order_confirmation(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('home')

    context = {
        'order': order
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
                update_session_auth_hash(request, user) 
                messages.success(request, 'Your password was successfully updated!')
            else:
                messages.error(request, 'New passwords do not match.')
        else:
            messages.error(request, 'Current password is incorrect.')

    messages.success(request, 'Your profile was successfully updated!')
    
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@require_POST
def cancel_item(request):
    item_id = request.POST.get('item_id')
    variant_id = request.POST.get('variant_id')
    inc_quantity = request.POST.get('inc_quantity')
    variant = ProductVariant.objects.get(id=variant_id)
    print(item_id,'item id ddddddd')
    print(variant_id)
    
    
    try:
        item = OrderItem.objects.get(id=item_id, order__user=request.user)
        
        if item.item_status in ['pending', 'processing', 'shipped']:
            item.item_status = 'cancelled'
            
            variant.stock = variant.stock + int(inc_quantity)
            variant.save()
            item.save()

            order = item.order
            if all(oi.item_status == 'cancelled' for oi in order.ordered_items.all()):
                order.status = 'cancelled'
                order.save()

            return JsonResponse({'success': True, 'message': 'Item cancelled successfully'})
        else:
            return JsonResponse({'success': False, 'message': 'Item cannot be cancelled in its current status'})

    except OrderItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Item not found'})


@require_POST
def return_item(request):
    item_id = request.POST.get('item_id')
    reason = request.POST.get('reason')
    try:
        item = OrderItem.objects.get(id=item_id, order__user=request.user)
        if item.item_status == 'delivered' and not item.return_request:
            item.return_request = True
            # item.item_status = 'returned'   
            item.save()

            return JsonResponse({'success': True, 'message': 'Return request submitted successfully'})
        else:
            return JsonResponse({'success': False, 'message': 'Unable to process return request'})
    except OrderItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Item not found'})


        







# def checkout(request):
#     user = request.user
#     cart = Cart.objects.get(user=user)
#     cart_items = cart.items.all()
    
#     # Calculate cart total with product/category offers applied
#     cart_total = sum(item.get_total_price() for item in cart_items)
    
#     count_of_cart = cart.items.count()
    
#     if count_of_cart == 0:
#         messages.error(request, "There are no items in your cart")
#         return redirect(request.META.get('HTTP_REFERER', 'home'))
    
#     # Initialize Razorpay client
#     client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
#     coupon_id = request.session.get('coupon_id')
#     coupon = None
#     coupon_discount = Decimal('0.00')
#     # if coupon_id:
#     #     try:
#     #         coupon = Coupon.objects.get(id=coupon_id)
#     #         if coupon.is_valid() and coupon.can_use():
#     #             if coupon.min_purchase_amount and cart_total < coupon.min_purchase_amount:
#     #                 messages.error(request, f"Minimum purchase amount of {coupon.min_purchase_amount} required for this coupon.")
#     #                 del request.session['coupon_id']
#     #                 discounted_total = cart_total
#     #             else:
#     #                 discount_amount = coupon.apply_discount(cart_total)
#     #                 discounted_total = cart_total - discount_amount
#     #         else:
#     #             messages.error(request, "The applied coupon is no longer valid.")
#     #             del request.session['coupon_id']
#     #             discounted_total = cart_total
#     #     except Coupon.DoesNotExist:
#     #         discounted_total = cart_total
#     #         del request.session['coupon_id']
#     # else:
#     #     discounted_total = cart_total
#     if coupon_id:
#         try:
#             coupon = Coupon.objects.get(id=coupon_id)
#             if coupon.is_valid() and coupon.can_use():
#                 if coupon.min_purchase_amount and cart_total < coupon.min_purchase_amount:
#                     messages.error(request, f"Minimum purchase amount of {coupon.min_purchase_amount} required for this coupon.")
#                     del request.session['coupon_id']
#                 else:
#                     coupon_discount = coupon.apply_discount(cart_total)
#             else:
#                 messages.error(request, "The applied coupon is no longer valid.")
#                 del request.session['coupon_id']
#         except Coupon.DoesNotExist:
#             del request.session['coupon_id']

#     # Calculate final total
#     final_total = cart_total - coupon_discount
    
#     if request.method == 'POST':
        
#         if 'remove_coupon' in request.POST:
#             if 'coupon_id' in request.session:
#                 del request.session['coupon_id']
#             return redirect('checkout')
#         # Determine payment method
#         payment_method = request.POST.get('payment_method', 'cod')
        
#         # Validate cart items
#         if not validate_cart_items(request, cart_items):
#             return redirect('checkout')
        
#         # Create order with discounted total if a coupon was applied
#         order = create_order(user, final_total, payment_method, coupon)
        
#         # If a coupon was used, associate it with the order and increment usage
#         if coupon:
#             order.coupon = coupon.code
#             order.save()
#             coupon.increment_usage()
        
#         # Handle address
#         if not handle_order_address(request, order, user):
#             return redirect('checkout')
        
#         # Process payment
#         if payment_method == 'razorpay':
#             if not process_razorpay_payment(request, client, order):
#                 return redirect('checkout')
#         elif payment_method == 'cod':
#             process_cod_order(order)
#         # Add other payment methods here if needed
        
#         # Create order items and update stock
#         create_order_items_and_update_stock(order, cart_items, payment_method)
        
#         # Clear the cart and coupon data
#         cart.items.all().delete()
#         if 'coupon_id' in request.session:
#             del request.session['coupon_id']
#             del request.session['discounted_total']
        
#         messages.success(request, "Your order has been placed successfully!")
#         return redirect('order_confirmation', order_id=order.id)
    
#     # Handle GET request
#     try:
#         # Create Razorpay Order
#         amount_in_paise = int(final_total * 100)
#         max_amount = 500000 * 100  # 5 lakh rupees in paise (adjust as needed)
        
#         if amount_in_paise > max_amount:
#             # Split the order into multiple Razorpay orders
#             num_orders = (amount_in_paise + max_amount - 1) // max_amount
#             razorpay_orders = []
#             for i in range(num_orders):
#                 order_amount = min(max_amount, amount_in_paise - i * max_amount)
#                 razorpay_order = client.order.create(dict(
#                     amount=order_amount,
#                     currency='INR',
#                     payment_capture='0'
#                 ))
#                 razorpay_orders.append(razorpay_order)
            
#             # Use the first order for the initial payment
#             primary_razorpay_order = razorpay_orders[0]
#         else:
#             # Create a single Razorpay order
#             primary_razorpay_order = client.order.create(dict(
#                 amount=amount_in_paise,
#                 currency='INR',
#                 payment_capture='0'
#             ))
#             razorpay_orders = [primary_razorpay_order]
        
#         # context = {
#         #     'cart_items': cart_items,
#         #     'cart_total': cart_total,
#         #     'discounted_total': discounted_total,
#         #     'user': user,
#         #     'razorpay_key_id': settings.RAZORPAY_KEY_ID,
#         #     'razorpay_order_id': primary_razorpay_order['id'],
#         #     'cart_total_paise': amount_in_paise,
#         #     'razorpay_orders': razorpay_orders,
#         #     'coupon': coupon,
#         # }
#         context = {
#             'cart_items': cart_items,
#             'cart_total': cart_total,
#             'coupon_discount': coupon_discount,
#             'final_total': final_total,
#             'user': user,
#             'razorpay_key_id': settings.RAZORPAY_KEY_ID,
#             'razorpay_order_id': primary_razorpay_order['id'],
#             'cart_total_paise': amount_in_paise,
#             'razorpay_orders': razorpay_orders,
#             'coupon': coupon,
#         }
        
#         return render(request, 'store/checkout.html', context)
    
#     except razorpay.errors.BadRequestError as e:
#         messages.error(request, f"An error occurred while processing your order: {str(e)}")
#         return redirect('cart')   
# def checkout(request):
#     user = request.user
#     cart = Cart.objects.get(user=user)
#     cart_items = cart.items.all()
#     cart_total = cart.get_total_price()
#     count_of_cart = cart.items.count()
    
#     if count_of_cart == 0:
#         messages.error(request, "There are no items in your cart")
#         return redirect(request.META.get('HTTP_REFERER', 'home'))
    
#     # Initialize Razorpay client
#     client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
#     # Check if a coupon has been applied
#     coupon_id = request.session.get('coupon_id')
#     if coupon_id:
#         try:
#             coupon = Coupon.objects.get(id=coupon_id)
#             discounted_total = request.session.get('discounted_total', cart_total)
#         except Coupon.DoesNotExist:
#             discounted_total = cart_total
#             del request.session['coupon_id']
#             del request.session['discounted_total']
#     else:
#         discounted_total = cart_total
#         coupon = None
    
#     if request.method == 'POST':
#         # Determine payment method
#         payment_method = request.POST.get('payment_method', 'cod')
        
#         # Validate cart items
#         if not validate_cart_items(request, cart_items):
#             return redirect('checkout')
        
#         # Create order with discounted total if a coupon was applied
#         order = create_order(user, discounted_total, payment_method)
        
#         # If a coupon was used, associate it with the order
#         if coupon:
#             order.coupon = coupon.code
#             order.save()
#             coupon.increment_usage()
        
#         # Handle address
#         if not handle_order_address(request, order, user):
#             return redirect('checkout')
        
#         # Process payment
#         if payment_method == 'razorpay':
#             if not process_razorpay_payment(request, client, order):
#                 return redirect('checkout')
#         elif payment_method == 'cod':
#             process_cod_order(order)
#         # Add other payment methods here if needed
        
#         # Create order items and update stock
#         create_order_items_and_update_stock(order, cart_items, payment_method)
        
#         # Clear the cart and coupon data
#         cart.items.all().delete()
#         if 'coupon_id' in request.session:
#             del request.session['coupon_id']
#             del request.session['discounted_total']
        
#         messages.success(request, "Your order has been placed successfully!")
#         return redirect('order_confirmation', order_id=order.id)
    
#     # Handle GET request
#     try:
#         # Create Razorpay Order
#         amount_in_paise = int(discounted_total * 100)
#         max_amount = 500000 * 100  # 5 lakh rupees in paise (adjust as needed)
        
#         if amount_in_paise > max_amount:
#             # Split the order into multiple Razorpay orders
#             num_orders = (amount_in_paise + max_amount - 1) // max_amount
#             razorpay_orders = []
#             for i in range(num_orders):
#                 order_amount = min(max_amount, amount_in_paise - i * max_amount)
#                 razorpay_order = client.order.create(dict(
#                     amount=order_amount,
#                     currency='INR',
#                     payment_capture='0'
#                 ))
#                 razorpay_orders.append(razorpay_order)
            
#             # Use the first order for the initial payment
#             primary_razorpay_order = razorpay_orders[0]
#         else:
#             # Create a single Razorpay order
#             primary_razorpay_order = client.order.create(dict(
#                 amount=amount_in_paise,
#                 currency='INR',
#                 payment_capture='0'
#             ))
#             razorpay_orders = [primary_razorpay_order]
        
#         context = {
#             'cart_items': cart_items,
#             'cart_total': cart_total,
#             'discounted_total': discounted_total,
#             'user': user,
#             'razorpay_key_id': settings.RAZORPAY_KEY_ID,
#             'razorpay_order_id': primary_razorpay_order['id'],
#             'cart_total_paise': amount_in_paise,
#             'razorpay_orders': razorpay_orders,
#         }
        
#         return render(request, 'store/checkout.html', context)
    
#     except razorpay.errors.BadRequestError as e:
#         messages.error(request, f"An error occurred while processing your order: {str(e)}")
#         return redirect('cart')










# @require_POST
# def apply_coupon(request):
#     coupon_code = request.POST.get('coupon_code')
#     try:
#         coupon = Coupon.objects.get(code=coupon_code)
#         cart = Cart.objects.get(user=request.user)
#         cart_total = cart.get_total_price()
        
#         current_time = django_timezone.now()
#         if (coupon.is_valid() and coupon.can_use() and
#             coupon.valid_from <= current_time <= coupon.valid_to):
            
#             if coupon.min_purchase_amount and cart_total < coupon.min_purchase_amount:
#                 return JsonResponse({
#                     'valid': False,
#                     'message': f'Minimum purchase amount of {coupon.min_purchase_amount} required for this coupon.'
#                 })
            
#             discount_amount = coupon.apply_discount(cart_total)
#             new_total = cart_total - discount_amount

#             # Store the coupon and discounted total in the session
#             request.session['coupon_id'] = coupon.id
#             request.session['discounted_total'] = float(new_total)

#             return JsonResponse({
#                 'valid': True,
#                 'discount': float(discount_amount),
#                 'new_total': float(new_total),
#                 'message': 'Coupon applied successfully!'
#             })
            
#         else:
#             return JsonResponse({
#                 'valid': False,
#                 'message': 'This coupon is not valid for your order.'
#             })
#     except Coupon.DoesNotExist:
#         return JsonResponse({
#             'valid': False,
#             'message': 'Invalid coupon code.'
#         })       






# def checkout(request):
#     user = request.user
#     cart = Cart.objects.get(user=user)
#     cart_items = cart.items.all()
#     cart_total = cart.get_total_price()
    
#     count_of_cart = cart.items.count()
    
#     if count_of_cart == 0:
#         messages.error(request, "There are no items in your cart")
#         return redirect(request.META.get('HTTP_REFERER', 'home'))
    
#     # Initialize Razorpay client
#     client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
#     if request.method == 'POST':
#         # Check if it's a Razorpay callback
#         if 'razorpay_payment_id' in request.POST:
#             # Verify the payment signature
#             params_dict = {
#                 'razorpay_order_id': request.POST.get('razorpay_order_id'),
#                 'razorpay_payment_id': request.POST.get('razorpay_payment_id'),
#                 'razorpay_signature': request.POST.get('razorpay_signature')
#             }
            
#             try:
#                 client.utility.verify_payment_signature(params_dict)
#             except:
#                 messages.error(request, "Payment verification failed")
#                 return redirect('checkout')
            
#             payment_method = 'razorpay'
#         else:
#             payment_method = request.POST.get('payment_method', 'cod')
        
#         # Validate cart items
#         checker = True
#         for item in cart_items:
#             product_variant = item.product_variant
            
#             if not product_variant.is_available:
#                 messages.error(request, f"{product_variant.product.name} - {product_variant.color} is not available. Sorry!")
#                 checker = False
#                 continue
            
#             if item.quantity > product_variant.stock:
#                 messages.error(request, f"Sorry, we only have {product_variant.stock} of {product_variant.product.name} - {product_variant.color} in stock.")
#                 checker = False
#                 continue
        
#         if not checker:
#             return redirect('checkout')
        
#         # Create order
#         order = Order.objects.create(
#             user=user,
#             status='pending',
#             total_price=cart_total,
#             payment_method=payment_method
#         )

#         # Handle address
#         use_new_address = request.POST.get('use_new_address')
#         if use_new_address:
#             order_address = OrderAddress.objects.create(
#                 order=order,
#                 full_name=request.POST.get('full_name'),
#                 last_name=request.POST.get('last_name'),
#                 phone_number=request.POST.get('phone_number'),
#                 email=request.POST.get('email'),
#                 address_line_1=request.POST.get('address_line_1'),
#                 address_line_2=request.POST.get('address_line_2'),
#                 city=request.POST.get('city'),
#                 state=request.POST.get('state'),
#                 postal_code=request.POST.get('postal_code'),
#                 country=request.POST.get('country')
#             )
#         else:
#             selected_address_id = request.POST.get('selected_address')
#             if not selected_address_id:
#                 messages.error(request, "Please select an address or enter a new one")
#                 return redirect('checkout')
            
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

#         # Create order items and update stock
#         for item in cart_items:
#             OrderItem.objects.create(
#                 order=order,
#                 product_variant=item.product_variant,
#                 quantity=item.quantity,
#                 price=item.product_variant.price
#             )
            
#             item.product_variant.stock -= item.quantity
#             item.product_variant.save()

#         # Clear the cart
#         cart.items.all().delete()

#         messages.success(request, "Your order has been placed successfully!")
#         return redirect('order_confirmation', order_id=order.id)

#     # Create Razorpay Order
#     razorpay_order = client.order.create(dict(
#         amount=int(cart_total * 100),  # Razorpay expects amount in paise
#         currency='INR',
#         payment_capture='0'
#     ))
    
#     context = {
#         'cart_items': cart_items,
#         'cart_total': cart_total,
#         'user': user,
#         'razorpay_key_id': settings.RAZORPAY_KEY_ID,
#         'razorpay_order_id': razorpay_order['id'],
#         'cart_total_paise': int(cart_total * 100),
#     }
#     return render(request, 'store/checkout.html', context)

# def checkout(request):
#     user = request.user
#     cart = Cart.objects.get(user=user)
#     cart_items = cart.items.all()
#     cart_total = cart.get_total_price()
#     count_of_cart = cart.items.count()
    
#     if count_of_cart == 0:
#         messages.error(request, "There are no items in your cart")
#         return redirect(request.META.get('HTTP_REFERER', 'home'))
    
#     # Initialize Razorpay client
#     client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
#     if request.method == 'POST':
#         # Determine payment method
#         payment_method = 'razorpay' if 'razorpay_payment_id' in request.POST else request.POST.get('payment_method', 'cod')
        
#         # Validate cart items
#         if not validate_cart_items(cart_items):
#             return redirect('checkout')
        
#         # Create order
#         order = create_order(user, cart_total, payment_method)
        
#         # Handle address
#         if not handle_order_address(request, order, user):
#             return redirect('checkout')
        
#         # Process Razorpay payment
#         if payment_method == 'razorpay':
#             if not process_razorpay_payment(request, client, order):
#                 return redirect('checkout')
        
#         # Create order items and update stock
#         create_order_items_and_update_stock(order, cart_items, payment_method)
        
#         # Clear the cart
#         cart.items.all().delete()
        
#         messages.success(request, "Your order has been placed successfully!")
#         return redirect('order_confirmation', order_id=order.id)

#     # Create Razorpay Order for GET request
#     razorpay_order = client.order.create(dict(
#         amount=int(cart_total * 100),  # Razorpay expects amount in paise
#         currency='INR',
#         payment_capture='0'
#     ))
    
#     context = {
#         'cart_items': cart_items,
#         'cart_total': cart_total,
#         'user': user,
#         'razorpay_key_id': settings.RAZORPAY_KEY_ID,
#         'razorpay_order_id': razorpay_order['id'],
#         'cart_total_paise': int(cart_total * 100),
#     }
#     return render(request, 'store/checkout.html', context)

# def validate_cart_items(cart_items):
#     for item in cart_items:
#         product_variant = item.product_variant
        
#         if not product_variant.is_available:
#             messages.error(request, f"{product_variant.product.name} - {product_variant.color} is not available. Sorry!")
#             return False
        
#         if item.quantity > product_variant.stock:
#             messages.error(request, f"Sorry, we only have {product_variant.stock} of {product_variant.product.name} - {product_variant.color} in stock.")
#             return False
    
#     return True

# def create_order(user, cart_total, payment_method):
#     return Order.objects.create(
#         user=user,
#         status='pending',
#         total_price=cart_total,
#         payment_method=payment_method,
#         payment_status='unpaid'
#     )

# def handle_order_address(request, order, user):
#     use_new_address = request.POST.get('use_new_address')
#     if use_new_address:
#         OrderAddress.objects.create(
#             order=order,
#             full_name=request.POST.get('full_name'),
#             last_name=request.POST.get('last_name'),
#             phone_number=request.POST.get('phone_number'),
#             email=request.POST.get('email'),
#             address_line_1=request.POST.get('address_line_1'),
#             address_line_2=request.POST.get('address_line_2'),
#             city=request.POST.get('city'),
#             state=request.POST.get('state'),
#             postal_code=request.POST.get('postal_code'),
#             country=request.POST.get('country')
#         )
#     else:
#         selected_address_id = request.POST.get('selected_address')
#         if not selected_address_id:
#             messages.error(request, "Please select an address or enter a new one")
#             return False
        
#         selected_address = user.addresses.get(id=selected_address_id)
#         OrderAddress.objects.create(
#             order=order,
#             full_name=selected_address.full_name,
#             last_name=selected_address.last_name,
#             phone_number=selected_address.phone_number,
#             email=selected_address.email,
#             address_line_1=selected_address.address_line_1,
#             address_line_2=selected_address.address_line_2,
#             city=selected_address.city,
#             state=selected_address.state,
#             postal_code=selected_address.postal_code,
#             country=selected_address.country
#         )
#     return True

# def process_razorpay_payment(request, client, order):
#     params_dict = {
#         'razorpay_order_id': request.POST.get('razorpay_order_id'),
#         'razorpay_payment_id': request.POST.get('razorpay_payment_id'),
#         'razorpay_signature': request.POST.get('razorpay_signature')
#     }
    
#     try:
#         client.utility.verify_payment_signature(params_dict)
#         order.status = 'processing'
#         order.payment_status = 'paid'
#         order.razorpay_order_id = params_dict['razorpay_order_id']
#         order.razorpay_payment_id = params_dict['razorpay_payment_id']
#         order.save()
#         return True
#     except:
#         messages.error(request, "Payment verification failed")
#         return False

# def create_order_items_and_update_stock(order, cart_items, payment_method):
#     for item in cart_items:
#         OrderItem.objects.create(
#             order=order,
#             product_variant=item.product_variant,
#             quantity=item.quantity,
#             price=item.product_variant.price,
#             item_status='processing' if payment_method == 'razorpay' else 'pending',
#             payment_status_item='paid' if payment_method == 'razorpay' else 'unpaid'
#         )
        
#         item.product_variant.stock -= item.quantity
#         item.product_variant.save()

# def checkout(request):
#     user = request.user
#     cart = Cart.objects.get(user=user)
#     cart_items = cart.items.all()
#     cart_total = cart.get_total_price()
#     count_of_cart = cart.items.count()
    
#     if count_of_cart == 0:
#         messages.error(request, "There are no items in your cart")
#         return redirect(request.META.get('HTTP_REFERER', 'home'))
    
#     # Initialize Razorpay client
#     client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
#     if request.method == 'POST':
#         # Determine payment method
#         payment_method = request.POST.get('payment_method', 'cod')
        
#         # Validate cart items
#         if not validate_cart_items(request, cart_items):
#             return redirect('checkout')
        
#         # Create order
#         order = create_order(user, cart_total, payment_method)
        
#         # Handle address
#         if not handle_order_address(request, order, user):
#             return redirect('checkout')
        
#         # Process payment
#         if payment_method == 'razorpay':
#             if not process_razorpay_payment(request, client, order):
#                 return redirect('checkout')
#         elif payment_method == 'cod':
#             process_cod_order(order)
#         elif payment_method == 'wallet':
#             # Add wallet payment processing logic here
#             pass
        
#         # Create order items and update stock
#         create_order_items_and_update_stock(order, cart_items, payment_method)
        
#         # Clear the cart
#         cart.items.all().delete()
        
#         messages.success(request, "Your order has been placed successfully!")
#         return redirect('order_confirmation', order_id=order.id)

#     # Create Razorpay Order for GET request
#     razorpay_order = client.order.create(dict(
#         amount=int(cart_total * 100),  # Razorpay expects amount in paise
#         currency='INR',
#         payment_capture='0'
#     ))
    
#     context = {
#         'cart_items': cart_items,
#         'cart_total': cart_total,
#         'user': user,
#         'razorpay_key_id': settings.RAZORPAY_KEY_ID,
#         'razorpay_order_id': razorpay_order['id'],
#         'cart_total_paise': int(cart_total * 100),
#     }
#     return render(request, 'store/checkout.html', context)




# def checkout(request):
#     user = request.user
#     cart = Cart.objects.get(user=user)
#     cart_items = cart.items.all()
#     cart_total = cart.get_total_price()
#     count_of_cart = cart.items.count()
    
#     if count_of_cart == 0:
#         messages.error(request, "There are no items in your cart")
#         return redirect(request.META.get('HTTP_REFERER', 'home'))
    
#     # Initialize Razorpay client
#     client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
#     # Check if a coupon has been applied
#     # coupon_id = request.session.get('coupon_id')
#     # if coupon_id:
#     #     try:
#     #         coupon = Coupon.objects.get(id=coupon_id)
#     #         discounted_total = request.session.get('discounted_total', cart_total)
#     #     except Coupon.DoesNotExist:
#     #         discounted_total = cart_total
#     #         del request.session['coupon_id']
#     #         del request.session['discounted_total']
#     # else:
#     #     discounted_total = cart_total
#     #     coupon = None
#     coupon_id = request.session.get('coupon_id')
#     if coupon_id:
#         try:
#             coupon = Coupon.objects.get(id=coupon_id)
#             discounted_total = request.session.get('discounted_total', cart_total)
#         except Coupon.DoesNotExist:
#             discounted_total = cart_total
#             del request.session['coupon_id']
#             del request.session['discounted_total']
#     else:
#         discounted_total = cart_total
#         coupon = None
    
#     if request.method == 'POST':
#         # Determine payment method
#         payment_method = request.POST.get('payment_method', 'cod')
        
#         # Validate cart items
#         if not validate_cart_items(request, cart_items):
#             return redirect('checkout')
        
#         # Create order with discounted total if a coupon was applied
#         order = create_order(user, discounted_total, payment_method)
        
#         # If a coupon was used, associate it with the order
#         if coupon:
#             order.coupon = coupon.code
#             order.save()
#             coupon.increment_usage()
        
#         # Handle address
#         if not handle_order_address(request, order, user):
#             return redirect('checkout')
        
#         # Process payment
#         if payment_method == 'razorpay':
#             if not process_razorpay_payment(request, client, order):
#                 return redirect('checkout')
#         elif payment_method == 'cod':
#             process_cod_order(order)
#         # elif payment_method == 'wallet':
#         #     if not process_wallet_payment(request, order):
#         #         return redirect('checkout')
        
#         # Create order items and update stock
#         create_order_items_and_update_stock(order, cart_items, payment_method)
        
#         # Clear the cart and coupon data
#         cart.items.all().delete()
#         if 'coupon_id' in request.session:
#             del request.session['coupon_id']
#             del request.session['discounted_total']
        
#         messages.success(request, "Your order has been placed successfully!")
#         return redirect('order_confirmation', order_id=order.id)
#     print(f"Discounted Total: {discounted_total}")
#     # Create Razorpay Order for GET request
#     razorpay_order = client.order.create(dict(
#         amount=int(discounted_total * 100),  # Razorpay expects amount in paise
#         currency='INR',
#         payment_capture='0'
#     ))
    
#     context = {
#         'cart_items': cart_items,
#         'cart_total': cart_total,
#         'discounted_total': discounted_total,
#         'user': user,
#         'razorpay_key_id': settings.RAZORPAY_KEY_ID,
#         'razorpay_order_id': razorpay_order['id'],
#         'cart_total_paise': int(discounted_total * 100),
#     }

#     return render(request, 'store/checkout.html', context)