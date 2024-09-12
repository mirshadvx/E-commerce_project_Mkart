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
import os
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from google.oauth2 import id_token
from google.auth.transport import requests
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.shortcuts import get_object_or_404

# Create your views here.

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

# def check_username(request):
#     username = request.GET.get('username', None)
#     data = {
#         'exists': User.objects.filter(username=username).exists()
#     }
#     return JsonResponse(data)
def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        phone_number = request.POST.get('phone_number')
        referral_code = request.POST.get('referral_code')
        
        context = {
            'username': username,
            'email': email,
            'phone_number': phone_number,
            'referral_code': referral_code,
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
        
        if referral_code and not Profile.objects.filter(referral_code=referral_code).exists():
            errors['referral_code'] = 'Invalid referral code'
                    
        if errors:
            context['errors'] = errors
            return render(request, 'store/register.html', context)

        otp = str(random.randint(100000, 999999))
   
        request.session['registration_data'] = {
            'username': username,
            'email': email,
            'password': password,
            'phone_number': phone_number,
            'referral_code': referral_code,
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
                
                profile = Profile.objects.create(user=new_user, phone=stored_data['phone_number'])
                
                wallet = Wallet.objects.create(user=new_user)
                
                if stored_data.get('referral_code'):
                    Profile.apply_referral(new_user, stored_data['referral_code'])

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

    print('new otp ',new_otp)
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

def home(request):
    user_wishlist_count = 0
    user_cart_count = 0
    cart_total = 0
    cart_items = []

    if request.user.is_authenticated:
        try:
            user_wishlist_count = Wishlist.objects.filter(user=request.user).count()
        except Wishlist.DoesNotExist:
            user_wishlist_count = 0
        
        try:
            user_cart_count = CartItem.objects.filter(cart__user=request.user).count()  # Count CartItems, not Cart itself
        except Cart.DoesNotExist:
            user_cart_count = 0


        cart, created = Cart.objects.get_or_create(user=request.user)   
        cart_items = CartItem.objects.filter(cart=cart)
        cart_total = cart.get_total_price()

    all_products = Product.objects.filter(category__status=True)
    categories = Category.objects.filter(status=True)
    genders = Gender.objects.all()
    brands = Brand.objects.all()

    context = {
        'products': all_products,
        'categories': categories,
        'genders': genders,
        'brands': brands,
        'wishlist_count': user_wishlist_count,
        'cart_count': user_cart_count,
        'cart_total': cart_total,
        'cart_items': cart_items,
    }
    return render(request, 'store/home.html', context)

   

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
    try:
        user_wishlist_count = Wishlist.objects.filter(user=request.user).count()
    except Wishlist.DoesNotExist:
        user_wishlist_count = None
    
    try:
        user_cart_count = CartItem.objects.filter(cart__user=request.user).count()  
    except Cart.DoesNotExist:
        user_cart_count = None

    cart, created = Cart.objects.get_or_create(user=request.user)   
    
    cart_total = cart.get_total_price()
    
    products = Product.objects.filter(category__status=True)
    

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
    
    
    for product in products:
        variant = product.variants.first()
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
        'wishlist_count':user_wishlist_count,
        'cart_count':user_cart_count,
        'cart_total':cart_total,
    }
    
    return render(request, 'store/products_home.html', context)


def product_info(request, id):
    try:
        user_wishlist_count = Wishlist.objects.filter(user=request.user).count()
    except Wishlist.DoesNotExist:
        user_wishlist_count = None
    
    try:
        user_cart_count = CartItem.objects.filter(cart__user=request.user).count() 
    except Cart.DoesNotExist:
        user_cart_count = None

    cart, created = Cart.objects.get_or_create(user=request.user)   
    
    cart_total = cart.get_total_price()
    
    
    product = get_object_or_404(Product, id=id)
    variants = product.variants.all()

    variant_id = request.GET.get('variant_id')
    if variant_id:
        selected_variant = get_object_or_404(ProductVariant, id=variant_id)
    else:
        selected_variant = product.variants.first()
   
   
    original_price = selected_variant.price
    discounted_price = product.get_discounted_price()

    active_offer = None
    if product.offer and product.offer.is_active and product.offer.valid_from <= timezone.now() <= product.offer.valid_to:
        active_offer = product.offer
    elif product.category.offer and product.category.offer.is_active and product.category.offer.valid_from <= timezone.now() <= product.category.offer.valid_to:
        active_offer = product.category.offer

    context = {
        'product': product,
        'variants': variants,
        'selected_variant': selected_variant,
        'active_offer': active_offer,
        'original_price': original_price,
        'discounted_price': discounted_price,
        'wishlist_count':user_wishlist_count,
        'cart_count':user_cart_count,
        'cart_total':cart_total,
    }

    return render(request, 'store/product_info.html', context)

@login_required
def wishlist(request):
    try:
        user_wishlist_count = Wishlist.objects.filter(user=request.user).count()
        cart = Cart.objects.get(user=request.user)
    except Wishlist.DoesNotExist:
        user_wishlist_count = None 
    try:
        user_cart_count = Cart.objects.filter(user=request.user).count()
    except Cart.DoesNotExist:
        user_cart_count = None     
        
    cart_total = cart.get_total_price()
    
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('variant__product', 'variant__color')
    
    context = {
        'wishlist_items': wishlist_items,
        'wishlist_count':user_wishlist_count,
        'cart_count':user_cart_count,
        'cart_total':cart_total,
    }
    return render(request, 'store/wishlist.html', context)


@login_required
def add_wishlist(request, id):
    if request.method == 'POST':
        variant_id = request.POST.get('variant_id')
        
        variant = get_object_or_404(ProductVariant, id=variant_id, product_id=id)
        
        try:
            Wishlist.objects.create(user=request.user, variant=variant)
            messages.success(request, f"{variant.product.name} ({variant.color.name}) added to your wishlist.")
        except IntegrityError:
            None
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


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
    try:
        user_wishlist_count = Wishlist.objects.filter(user=request.user).count()
    except Wishlist.DoesNotExist:
        user_wishlist_count = None
    
    try:
        user_cart_count = CartItem.objects.filter(cart__user=request.user).count() 
    except Cart.DoesNotExist:
        user_cart_count = None

    cart, created = Cart.objects.get_or_create(user=request.user)   
    
    cart_items = CartItem.objects.filter(cart=cart)
    cart_total = cart.get_total_price()

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
        'wishlist_count': user_wishlist_count,
        'cart_count': user_cart_count,
    }
    
    return render(request, 'store/cart.html', context)


@login_required
def add_to_cart(request, id):
    if request.method == 'POST':
        variant_id = request.POST.get('variant_id')
        quantity = int(request.POST.get('quantity', 1))
        
        variant = get_object_or_404(ProductVariant, id=variant_id)
        
        if not variant.is_available or variant.stock < quantity:
            messages.error(request, "Sorry, this product is out of stock or the requested quantity exceeds available stock.")
            return redirect(request.META.get('HTTP_REFERER', 'home'))
        
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product_variant=variant,
            defaults={'quantity': quantity}
        )
        
        if not item_created:
            cart_item.quantity += quantity
            cart_item.save()
        
        messages.success(request, f"{variant.product.name} has been added to your cart.")
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    
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
 
    try:
        user_wishlist_count = Wishlist.objects.filter(user=request.user).count()
    except Wishlist.DoesNotExist:
        user_wishlist_count = None
    
    try:
        user_cart_count = CartItem.objects.filter(cart__user=request.user).count() 
    except Cart.DoesNotExist:
        user_cart_count = None

    cart, created = Cart.objects.get_or_create(user=request.user)   
    
    cart_items = CartItem.objects.filter(cart=cart)
    cart_total = cart.get_total_price()
    user = request.user
    orders = Order.objects.filter(user=user).order_by('-created_at')
    profile = Profile.objects.get(user=user)
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all()

    context = {
        'user': user,
        'orders': orders,
        'profile': profile,
        'wallet': wallet,
        'transactions': transactions,
        'wishlist_count':user_wishlist_count,
        'cart_count':user_cart_count,
        'cart_total':cart_total,
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
        cart_items = CartItem.objects.filter(cart=cart).select_related('product_variant__product')
    except Cart.DoesNotExist:
        messages.warning(request, "Your cart is empty. Add some items before checking out.")
        return redirect('cart')

    if not cart_items:
        messages.warning(request, "Your cart is empty. Add some items before checking out.")
        return redirect('cart')


    subtotal = sum(item.quantity * item.product_variant.product.get_discounted_price() for item in cart_items)
    coupon = request.session.get('coupon')
    coupon_discount = Decimal('0.00')

    if coupon:
        try:
            coupon_obj = Coupon.objects.get(code=coupon)
            if coupon_obj.is_valid() and coupon_obj.can_use(request.user):
                coupon_discount = coupon_obj.apply_discount(subtotal)
                
        except Coupon.DoesNotExist:
            del request.session['coupon']

    total = subtotal - coupon_discount

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    razorpay_order = client.order.create({
        'amount': int(total * 100),  
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
            return process_order(request, cart_items, total, coupon, client,coupon_discount)

    return render(request, 'store/checkout.html', context)

def process_order(request, cart_items, total, coupon, razorpay_client, coupon_discount):
    wallet = Wallet.objects.get(user=request.user)

  
    if not validate_cart_items(request, cart_items):
        return redirect('cart')

 
    order = create_order(request, total, coupon, coupon_discount)

    if order:
       
        if not handle_order_address(request, order, request.user):
            order.delete()  
            return redirect('checkout')

    
        payment_method = request.POST.get('payment_method')

     
        if payment_method == 'razorpay':
            razorpay_payment_id = request.POST.get('razorpay_payment_id')
            razorpay_order_id = request.POST.get('razorpay_order_id')
            razorpay_signature = request.POST.get('razorpay_signature')

            if process_razorpay_payment(request, razorpay_client, order, razorpay_payment_id, razorpay_order_id, razorpay_signature):
                finalize_order(request, order, cart_items, 'razorpay')
                return redirect('order_confirmation', order_id=order.id)
            else:
                order.delete() 
                messages.error(request, "Razorpay payment failed.")
                return redirect('checkout')

       
        elif payment_method == 'cod':
            if total < Decimal('1000.00'):
                messages.error(request, "Cash on Delivery is not available for orders below ₹1000.")
                order.delete()  
                return redirect('checkout')

            finalize_order(request, order, cart_items, 'cod')
            return redirect('order_confirmation', order_id=order.id)


        elif payment_method == 'wallet':
            if total > wallet.balance:
                messages.error(request, "Insufficient balance in your wallet to complete this purchase.")
                order.delete()  
                return redirect('checkout')

       
            wallet.balance -= total
            wallet.save()

      
            WalletTransaction.objects.create(
                wallet=wallet,
                amount=total,
                transaction_type='debit'
            )

            finalize_order(request, order, cart_items, 'wallet')

            return redirect('order_confirmation', order_id=order.id)

    else:
        messages.error(request, "There was an error processing your order. Please try again.")
        return redirect('checkout')


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

def create_order(request, total, coupon,coupon_discount):
    return Order.objects.create(
        user = request.user,
        total_price =total,
        payment_method = request.POST.get('payment_method'),
        coupon = coupon,
        discount_amount_coupon = coupon_discount,
    )


def handle_order_address(request, order, user):
    use_new_address = request.POST.get('use_new_address')
    if use_new_address:

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
        except user.addresses.model.DoesNotExist:
            messages.error(request, "The selected address is no longer available. Please choose another or enter a new one.")
            return False
    
    return True


def process_razorpay_payment(request, client, order, payment_id, order_id, signature):
    try:
        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        client.utility.verify_payment_signature(params_dict)
        
    
        order.status = 'incomplete'
        order.payment_status = 'paid'
        order.razorpay_order_id = order_id
        order.razorpay_payment_id = payment_id
        order.save()

        return True
    
    except razorpay.errors.SignatureVerificationError:
        messages.error(request, "Razorpay payment verification failed. Please contact support if you've been charged.")
        return False
    except Exception as e:
        messages.error(request, f"An error occurred during payment processing: {str(e)}")
        return False

def finalize_order(request, order, cart_items, payment_method):

    create_order_items_and_update_stock(order, cart_items, payment_method)
    
 
    cart = Cart.objects.get(user=request.user)
    cart.items.all().delete()
    if 'coupon' in request.session:
        del request.session['coupon']



def process_cod_order(order):
    order.status = 'incomplete'
    order.payment_status = 'unpaid'
    order.save()

def create_order_items_and_update_stock(order, cart_items, payment_method):
    total_price = sum(item.quantity * item.product_variant.product.get_discounted_price() for item in cart_items)
    
    for item in cart_items:

        discounted_price = item.product_variant.product.get_discounted_price()

      
        if total_price > 0:
            item_coupon_discount = (item.quantity * discounted_price / total_price) * order.discount_amount_coupon
        else:
            item_coupon_discount = Decimal('0.00')

        
        if payment_method == 'razorpay':
            item_status = 'processing'
            payment_status_item = 'paid'
        elif payment_method == 'wallet':
            item_status = 'processing' 
            payment_status_item = 'paid'
            order.payment_status = 'paid'
            order.save()
        elif payment_method == 'cod':
            item_status = 'pending'
            payment_status_item = 'unpaid'


        OrderItem.objects.create(
            order=order,
            product_variant=item.product_variant,
            quantity=item.quantity,
            price=discounted_price,
            item_status=item_status,
            payment_status_item=payment_status_item,
            orderItem_coupon_discount=item_coupon_discount 
        )
        
        item.product_variant.stock -= item.quantity
        item.product_variant.save()
        

@require_POST
def apply_coupon(request):
    code = request.POST.get('coupon_code')
    try:
        coupon = Coupon.objects.get(code=code)
        cart = Cart.objects.get(user=request.user)
        cart_total = cart.get_total_price()

        if coupon.is_valid():
            if cart_total > coupon.min_purchase_amount:
                can_use, message = coupon.can_use(request.user)
                if can_use:
                    request.session['coupon'] = code
                    coupon.increment_usage(request.user)
                    messages.success(request, "Coupon applied successfully!")
                else:
                    messages.error(request, message)
            else:
                messages.error(request, f"This coupon requires a minimum purchase of {coupon.min_purchase_amount}.")
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
    
    try:
        user_wishlist_count = Wishlist.objects.filter(user=request.user).count()
    except Wishlist.DoesNotExist:
        user_wishlist_count = 0
    
    try:
        user_cart_count = CartItem.objects.filter(cart__user=request.user).count() 
    except Cart.DoesNotExist:
        user_cart_count = 0

    cart, created = Cart.objects.get_or_create(user=request.user)   
    cart_total = cart.get_total_price()

    context = {
        'order': order,
        'order_items': order_items,
        'order_address': order_address,
        'wishlist_count': user_wishlist_count,
        'cart_count': user_cart_count,
        'cart_total': cart_total,
    }
    return render(request,'store/ordered_product_info.html',context)



def download_invoice(request, item_id):
    order_item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)

    if order_item.item_status != 'delivered':
        return HttpResponse("Invoice is only available for delivered items.")

    template = get_template('store/invoice.html')
    context = {
        'order_item': order_item,
        'user': request.user,
    }
    html = template.render(context)

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)

    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order_item.order.id}_{order_item.id}.pdf"'
        return response
 
    return HttpResponse("Error generating PDF", status=400)

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

from django.db import transaction

@require_POST
@transaction.atomic
def cancel_item(request):
    item_id = request.POST.get('item_id')
    
    try:
        item = OrderItem.objects.select_related('order', 'product_variant').get(id=item_id, order__user=request.user)
        
        if item.item_status in ['pending', 'processing', 'shipped']:
           
            refund_amount = item.get_total_price() - item.orderItem_coupon_discount
            
    
            item.item_status = 'cancelled'
            item.save()

            item.product_variant.stock += item.quantity
            item.product_variant.save()

     
            order = item.order
            if all(i.item_status == 'cancelled' for i in order.ordered_items.all()):
                order.status = 'cancelled'
                order.save()

      
            if order.payment_status == 'paid':
                user_wallet, _ = Wallet.objects.get_or_create(user=request.user)
                user_wallet.balance += Decimal(refund_amount)
                user_wallet.save()

                WalletTransaction.objects.create(
                    wallet=user_wallet,
                    amount=refund_amount,
                    transaction_type='credit',
                )

            return JsonResponse({
                'success': True, 
                'message': 'Item cancelled successfully',
                'refund_amount': float(refund_amount) if order.payment_status == 'paid' else 0
            })
        else:
            return JsonResponse({'success': False, 'message': 'Item cannot be cancelled in its current status'})

    except OrderItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Item not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'})


# @require_POST
# def cancel_item(request):
#     item_id = request.POST.get('item_id')
#     variant_id = request.POST.get('variant_id')
#     inc_quantity = request.POST.get('inc_quantity')
#     variant = ProductVariant.objects.get(id=variant_id)
#     print(item_id,'item id ddddddd')
#     print(variant_id)
    
    
#     try:
#         item = OrderItem.objects.get(id=item_id, order__user=request.user)
        
#         if item.item_status in ['pending', 'processing', 'shipped']:
#             item.item_status = 'cancelled'
            
#             variant.stock = variant.stock + int(inc_quantity)
#             variant.save()
#             item.save()

#             order = item.order
#             if all(i.item_status == 'cancelled' for i in order.ordered_items.all()):
#                 order.status = 'cancelled'
#                 order.save()

#             if order.payment_method == 'razorpay':
#                 # refund_amount = item.get_total_price()
#                 refund_amount = item.orderItem_coupon_discount
#                 request.user.wallet.balance += refund_amount
#                 request.user.wallet.save()

#                 WalletTransaction.objects.create(
#                     wallet=request.user.wallet,
#                     amount=refund_amount,
#                     transaction_type='credit'
#                 )

#             return JsonResponse({'success': True, 'message': 'Item cancelled successfully'})
#         else:
#             return JsonResponse({'success': False, 'message': 'Item cannot be cancelled in its current status'})

#     except OrderItem.DoesNotExist:
#         return JsonResponse({'success': False, 'message': 'Item not found'})


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

        


# @require_POST
# def cancel_item(request):
#     item_id = request.POST.get('item_id')
#     variant_id = request.POST.get('variant_id')
#     inc_quantity = request.POST.get('inc_quantity')
#     variant = ProductVariant.objects.get(id=variant_id)
#     print(item_id,'item id ddddddd')
#     print(variant_id============
#     try:
#         item = OrderItem.objects.get(id=item_id, order__user=request.user)
        
#         if item.item_status in ['pending', 'processing', 'shipped']:
#             item.item_status = 'cancelled'
            
#             variant.stock = variant.stock + int(inc_quantity)
#             variant.save()
#             item.save()

#             order = item.order
#             if all(oi.item_status == 'cancelled' for oi in order.ordered_items.all()):
#                 order.status = 'cancelled'
#                 order.save()

#             return JsonResponse({'success': True, 'message': 'Item cancelled successfully'})
#         else:
#             return JsonResponse({'success': False, 'message': 'Item cannot be cancelled in its current status'})

#     except OrderItem.DoesNotExist:
#         return JsonResponse({'success': False, 'message': 'Item not found'})

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