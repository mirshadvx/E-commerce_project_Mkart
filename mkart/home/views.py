from django.db import IntegrityError
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
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
import razorpay
from django.conf import settings
from decimal import Decimal
from Admin.models import *
from django.utils import timezone as django_timezone
import os
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Min, Sum, IntegerField
from django.db.models.functions import Coalesce
import json
import logging
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.views import PasswordResetView
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from .services.email_service import (
    send_otp_email,
    send_password_reset_email,
    send_welcome_email,
)

logger = logging.getLogger('registration')


def redirect_to_product_reviews(product_id):
    return HttpResponseRedirect(f"{reverse('product_info', kwargs={'id': product_id})}#product-review-tab")


def attach_review_state(order_items, user):
    product_ids = [item.product_variant.product_id for item in order_items]
    reviews_by_product_id = {
        review.product_id: review
        for review in Review.objects.filter(user=user, product_id__in=product_ids)
    }

    for item in order_items:
        product = item.product_variant.product
        user_review = reviews_by_product_id.get(product.id)
        item.user_review = user_review
        item.can_review = item.item_status == 'delivered' and user_review is None
        item.review_url = f"{reverse('product_info', kwargs={'id': product.id})}#product-review-tab"

    return order_items

def custom_404(request, exception):
    return render(request, 'store/404.html', status=404)

def custom_500(request):
    return render(request, 'store/500.html', status=500)

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
    
    return render(request,'store/home.html',context)


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
        elif not re.match(r'^\d{10}$', phone_number):
            errors['phone_number'] = 'Phone number must be exactly 10 digits (0-9 only)'

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
        if not send_otp_email(email, username, otp):
            logger.error("OTP email sending failed for %s", email)
     
        stored_data = request.session.get('registration_data')
       
        return redirect('validate_otp')
    return render(request, 'store/register.html')


def validate_otp(request):
    if request.method == "POST":
        user_otp = request.POST.get('otp')
        stored_data = request.session.get('registration_data', {})

        if not stored_data:
            logger.error("No registration data found in session.")
            return redirect('register')

        try:
            otp_created_at = timezone.datetime.fromisoformat(stored_data.get('otp_created_at'))
            time_elapsed = (timezone.now() - otp_created_at).total_seconds()
            time_left = max(300 - int(time_elapsed), 0)

            if time_left == 0:
                del request.session['registration_data']
                logger.error("OTP expired for user: %s", stored_data.get('email'))
                return render(request, 'store/validateOTP.html', {'error': 'OTP has expired. Please try again.', 'time_left': 0})

            if user_otp == stored_data.get('otp'):
                try:
                    existing_user = User.objects.filter(email=stored_data['email']).first()
                    if existing_user:
                        logger.error("User with email %s already exists.", stored_data.get('email'))
                        return render(request, 'store/validateOTP.html', {'error': 'An account with this email already exists.', 'time_left': time_left})

                
                    new_user = User.objects.create_user(
                        username=stored_data['username'],
                        email=stored_data['email'],
                        password=stored_data['password']
                    )
                    new_user.save()

                    if not Profile.objects.filter(user=new_user).exists():
                        profile = Profile.objects.create(user=new_user, phone=stored_data['phone_number'])
                    if not Wallet.objects.filter(user=new_user).exists():
                        wallet = Wallet.objects.create(user=new_user)

            
                    if stored_data.get('referral_code'):
                        Profile.apply_referral(new_user, stored_data['referral_code'])

                    user = authenticate(request, username=stored_data['username'], password=stored_data['password'])
                    if user is not None:
                        login(request, user)

                    if not send_welcome_email(new_user.email, new_user.username):
                        logger.error("Welcome email sending failed for %s", new_user.email)
                
                    return redirect('home')

                except IntegrityError as e:
                    logger.error("IntegrityError while creating user: %s", str(e))
                    return render(request, 'store/validateOTP.html', {'error': 'An error occurred while creating your account. Please try again.', 'time_left': time_left})

            else:
                logger.error("Invalid OTP entered by user: %s", stored_data.get('email'))
                return render(request, 'store/validateOTP.html', {'error': 'Invalid OTP', 'time_left': time_left})

        except Exception as e:
            logger.error("Unexpected error during OTP validation: %s", str(e))
            return render(request, 'store/validateOTP.html', {'error': 'An unexpected error occurred. Please try again later.', 'time_left': time_left})

    stored_data = request.session.get('registration_data', {})
    if not stored_data:
        return redirect('register')

    otp_created_at = timezone.datetime.fromisoformat(stored_data.get('otp_created_at'))
    time_elapsed = (timezone.now() - otp_created_at).total_seconds()
    time_left = max(300 - int(time_elapsed), 0)

    return render(request, 'store/validateOTP.html', {'time_left': time_left})

def resend_otp(request):
    stored_data = request.session.get('registration_data', {})
    if not stored_data:
        return redirect('register')

    new_otp = str(random.randint(100000, 999999))

    if not send_otp_email(stored_data['email'], stored_data['username'], new_otp):
        logger.error("Resent OTP email sending failed for %s", stored_data['email'])
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
            
    elif request.user.is_authenticated:
        return redirect('home')  
    return render(request, 'store/login.html')

def logoutPage(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect('login')

@never_cache
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
            user_cart_count = CartItem.objects.filter(cart__user=request.user).count()
        except Cart.DoesNotExist:
            user_cart_count = 0

        cart, created = Cart.objects.get_or_create(user=request.user)   
        cart_items = CartItem.objects.filter(cart=cart)
        cart_total = cart.get_total_price()

    all_products = (
        Product.objects
        .filter(
            category__status=True,
            variants__is_available=True,
            variants__stock__gt=0
        )
        .annotate(
            total_bought=Coalesce(
                Sum('variants__order_items__quantity'),
                0,
                output_field=IntegerField()
            )
        )
        .order_by('-total_bought')
        .distinct()[:8]
    )

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

@never_cache
def show_products(request):
    user_wishlist_count = 0
    user_cart_count = 0
    cart_total = 0

    if request.user.is_authenticated:
        user_wishlist_count = Wishlist.objects.filter(user=request.user).count()
        
        try:
            user_cart = Cart.objects.get(user=request.user)
            user_cart_count = CartItem.objects.filter(cart=user_cart).count()
            cart_total = user_cart.get_total_price()
        except Cart.DoesNotExist:
            pass


    products = Product.objects.filter(category__status=True).prefetch_related(
        'variants', 'variants__color'
    ).select_related('category', 'brand', 'gender')

    search_query = request.GET.get('search', '').strip()
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(brand__name__icontains=search_query)
        ).distinct()

    selected_categories = request.GET.getlist('category')
    selected_genders = request.GET.getlist('gender')
    selected_brands = request.GET.getlist('brand')
    selected_colors = request.GET.getlist('color')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if selected_categories:
        products = products.filter(category__name__in=selected_categories)
    if selected_genders:
        products = products.filter(gender__name__in=selected_genders)
    if selected_brands:
        products = products.filter(brand__name__in=selected_brands)
    if selected_colors:
        products = products.filter(variants__color__name__in=selected_colors).distinct()
    if min_price and max_price:
        products = products.filter(
            variants__price__gte=min_price, 
            variants__price__lte=max_price
        ).distinct()

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
    else:
        products = products.order_by('-created_at')

    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    page_range = []
    current = page_obj.number
    total = paginator.num_pages

    if total <= 7:
        page_range = list(range(1, total + 1))
    else:
        page_range = [1]
        if current > 4:
            page_range.append(None)
        start = max(2, current - 2)
        end = min(total - 1, current + 2)
        page_range.extend(range(start, end + 1))
        if current < total - 3:
            page_range.append(None)
        if total not in page_range:
            page_range.append(total)

    filter_params = request.GET.copy()
    filter_params.pop('page', None)
    filter_query_string = filter_params.urlencode()

    for product in page_obj:
        variant = product.variants.first()
        if variant:
            product.display_price = variant.price
            product.discounted_price = product.get_discounted_price()
            if product.discounted_price and product.discounted_price < variant.price:
                product.discount_percentage = round(100 * (1 - product.discounted_price / variant.price), 2)
            else:
                product.discount_percentage = None

    context = {
        'products': page_obj,
        'paginator': paginator,
        'page_obj': page_obj,
        'page_range': page_range,
        'filter_query_string': filter_query_string,

        'categories': Category.objects.filter(status=True),
        'genders': Gender.objects.all(),
        'brands': Brand.objects.all(),
        'colors': Color.objects.all(),

        'sort_by': sort_by,
        'wishlist_count': user_wishlist_count,
        'cart_count': user_cart_count,
        'cart_total': cart_total,

        'selected_categories': selected_categories,
        'selected_genders': selected_genders,
        'selected_brands': selected_brands,
        'selected_colors': selected_colors,
        'min_price': min_price,
        'max_price': max_price,
        'search_query': search_query,
    }

    return render(request, 'store/products_home.html', context)

@never_cache
def mens_items(request):
    user_wishlist_count = 0
    user_cart_count = 0
    cart_total = 0

    if request.user.is_authenticated:
        user_wishlist_count = Wishlist.objects.filter(user=request.user).count()
        try:
            user_cart = Cart.objects.get(user=request.user)
            user_cart_count = CartItem.objects.filter(cart=user_cart).count()
            cart_total = user_cart.get_total_price()
        except Cart.DoesNotExist:
            pass

    products = Product.objects.filter(
        category__status=True, gender__name='Men'
    ).prefetch_related('variants', 'variants__color').select_related(
        'category', 'brand', 'gender'
    )

    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(brand__name__icontains=search_query)
        ).distinct()

    selected_categories = request.GET.getlist('category')
    selected_brands = request.GET.getlist('brand')
    selected_colors = request.GET.getlist('color')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if selected_categories:
        products = products.filter(category__name__in=selected_categories)
    if selected_brands:
        products = products.filter(brand__name__in=selected_brands)
    if selected_colors:
        products = products.filter(variants__color__name__in=selected_colors).distinct()
    if min_price and max_price:
        products = products.filter(
            variants__price__gte=min_price,
            variants__price__lte=max_price
        ).distinct()

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
    else:
        products = products.order_by('-created_at')

    for product in products:
        variant = product.variants.first()
        if variant:
            product.display_price = variant.price
            product.discounted_price = product.get_discounted_price()
            if product.discounted_price < variant.price:
                product.discount_percentage = round(100 * (1 - product.discounted_price / variant.price), 2)
            else:
                product.discount_percentage = None

    paginator = Paginator(products, 4)
    page_number = request.GET.get('page', 1)
    try:
        products_page = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        products_page = paginator.page(1)

    current = products_page.number
    total = paginator.num_pages
    delta = 2
    page_range = []
    for i in range(1, total + 1):
        if i == 1 or i == total or (current - delta <= i <= current + delta):
            if page_range and page_range[-1] is not None and i - page_range[-1] > 1:
                page_range.append(None)
            page_range.append(i)

    filter_params = request.GET.copy()
    filter_params.pop('page', None)
    filter_query_string = filter_params.urlencode()

    all_categories = Category.objects.filter(status=True)
    all_brands = Brand.objects.all()
    all_colors = Color.objects.all()

    context = {
        'products': products_page,
        'paginator': paginator,
        'page_range': page_range,
        'filter_query_string': filter_query_string,
        'categories': all_categories,
        'brands': all_brands,
        'colors': all_colors,
        'sort_by': sort_by,
        'wishlist_count': user_wishlist_count,
        'cart_count': user_cart_count,
        'cart_total': cart_total,
        'selected_categories': selected_categories,
        'selected_brands': selected_brands,
        'selected_colors': selected_colors,
        'min_price': min_price,
        'max_price': max_price,
        'search_query': search_query,
    }

    return render(request, 'store/mens_items.html', context)


@never_cache
def womens_items(request):
    user_wishlist_count = 0
    user_cart_count = 0
    cart_total = 0

    if request.user.is_authenticated:
        user_wishlist_count = Wishlist.objects.filter(user=request.user).count()
        try:
            user_cart = Cart.objects.get(user=request.user)
            user_cart_count = CartItem.objects.filter(cart=user_cart).count()
            cart_total = user_cart.get_total_price()
        except Cart.DoesNotExist:
            pass

    products = Product.objects.filter(
        category__status=True, gender__name='Women'
    ).prefetch_related('variants', 'variants__color').select_related(
        'category', 'brand', 'gender'
    )

    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(brand__name__icontains=search_query)
        ).distinct()

    selected_categories = request.GET.getlist('category')
    selected_brands = request.GET.getlist('brand')
    selected_colors = request.GET.getlist('color')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if selected_categories:
        products = products.filter(category__name__in=selected_categories)
    if selected_brands:
        products = products.filter(brand__name__in=selected_brands)
    if selected_colors:
        products = products.filter(variants__color__name__in=selected_colors).distinct()
    if min_price and max_price:
        products = products.filter(
            variants__price__gte=min_price,
            variants__price__lte=max_price
        ).distinct()

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
    else:
        products = products.order_by('-created_at')

    for product in products:
        variant = product.variants.first()
        if variant:
            product.display_price = variant.price
            product.discounted_price = product.get_discounted_price()
            if product.discounted_price < variant.price:
                product.discount_percentage = round(100 * (1 - product.discounted_price / variant.price), 2)
            else:
                product.discount_percentage = None

    paginator = Paginator(products, 10)
    page_number = request.GET.get('page', 1)
    try:
        products_page = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        products_page = paginator.page(1)

    current = products_page.number
    total = paginator.num_pages
    delta = 2
    page_range = []
    for i in range(1, total + 1):
        if i == 1 or i == total or (current - delta <= i <= current + delta):
            if page_range and page_range[-1] is not None and i - page_range[-1] > 1:
                page_range.append(None)
            page_range.append(i)

    filter_params = request.GET.copy()
    filter_params.pop('page', None)
    filter_query_string = filter_params.urlencode()

    all_categories = Category.objects.filter(status=True)
    all_brands = Brand.objects.all()
    all_colors = Color.objects.all()

    context = {
        'products': products_page,
        'paginator': paginator,
        'page_range': page_range,
        'filter_query_string': filter_query_string,
        'categories': all_categories,
        'brands': all_brands,
        'colors': all_colors,
        'sort_by': sort_by,
        'wishlist_count': user_wishlist_count,
        'cart_count': user_cart_count,
        'cart_total': cart_total,
        'selected_categories': selected_categories,
        'selected_brands': selected_brands,
        'selected_colors': selected_colors,
        'min_price': min_price,
        'max_price': max_price,
        'search_query': search_query,
    }

    return render(request, 'store/womens_items.html', context)

# @never_cache
# def product_info(request, id):

#     user_wishlist_count = 0
#     user_cart_count = 0
#     cart_total = 0
    
#     if request.user.is_authenticated:
#         try:
#             user_wishlist_count = Wishlist.objects.filter(user=request.user).count()
#         except Wishlist.DoesNotExist:
#             user_wishlist_count = None
        
#         try:
#             user_cart_count = CartItem.objects.filter(cart__user=request.user).count()
#         except Cart.DoesNotExist:
#             user_cart_count = None
        
#         cart, created = Cart.objects.get_or_create(user=request.user)   
#         cart_total = cart.get_total_price()

#     product = get_object_or_404(Product, id=id)
#     variants = product.variants.all()

    
#     variant_id = request.GET.get('variant_id')
#     if variant_id:
#         selected_variant = get_object_or_404(ProductVariant, id=variant_id)
#     else:
#         selected_variant = product.variants.first()

   
#     original_price = selected_variant.price
#     discounted_price = product.get_discounted_price()

#     active_offer = None
#     if product.offer and product.offer.is_active and product.offer.valid_from <= timezone.now() <= product.offer.valid_to:
#         active_offer = product.offer
#     elif product.category.offer and product.category.offer.is_active and product.category.offer.valid_from <= timezone.now() <= product.category.offer.valid_to:
#         active_offer = product.category.offer

#     reviews = product.reviews.select_related('user').all()
#     avg_rating, review_count = Review.get_average_rating(product)
#     user_review = None
#     user_can_review = False
#     if request.user.is_authenticated:
#         user_review = reviews.filter(user=request.user).first()
#         user_can_review = OrderItem.objects.filter(
#             order__user=request.user,
#             product_variant__product=product,
#             item_status='delivered'
#         ).exists()

#     rating_breakdown = {i: reviews.filter(rating=i).count() for i in range(5, 0, -1)}


#     context = {
#         'product': product,
#         'variants': variants,
#         'selected_variant': selected_variant,
#         'active_offer': active_offer,
#         'original_price': original_price,
#         'discounted_price': discounted_price,
#         'wishlist_count': user_wishlist_count,
#         'cart_count': user_cart_count,
#         'cart_total': cart_total,
#         'reviews': reviews,
#         'avg_rating': round(avg_rating, 1),
#         'review_count': review_count,
#         'user_review': user_review,
#         'user_can_review': user_can_review,
#         'rating_breakdown': rating_breakdown,

#     }

#     return render(request, 'store/product_info.html', context)



@never_cache
def product_info(request, id):
    user_wishlist_count = 0
    user_cart_count = 0
    cart_total = 0

    if request.user.is_authenticated:
        user_wishlist_count = Wishlist.objects.filter(user=request.user).count()
        user_cart_count = CartItem.objects.filter(cart__user=request.user).count()
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_total = cart.get_total_price()

    product = get_object_or_404(Product, id=id)
    variants = product.variants.all()

    variant_id = request.GET.get('variant_id')
    if variant_id:
        selected_variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
    else:
        selected_variant = product.variants.first()

    if selected_variant is None:
        selected_variant = product.variants.first()  # safety fallback

    original_price = selected_variant.price if selected_variant else 0
    discounted_price = product.get_discounted_price()

    active_offer = None
    now = timezone.now()
    if product.offer and product.offer.is_active and product.offer.valid_from <= now <= product.offer.valid_to:
        active_offer = product.offer
    elif product.category.offer and product.category.offer.is_active and product.category.offer.valid_from <= now <= product.category.offer.valid_to:
        active_offer = product.category.offer

    # ---- REVIEWS ----
    reviews = product.reviews.select_related('user').order_by('-created_at')
    avg_rating, review_count = Review.get_average_rating(product)

    user_review = None
    user_can_review = False
    user_has_purchased = False

    if request.user.is_authenticated:
        user_review = Review.objects.filter(product=product, user=request.user).first()
        # Check if user has a DELIVERED order containing any variant of this product
        user_has_purchased = OrderItem.objects.filter(
            order__user=request.user,
            product_variant__product=product,
            item_status='delivered'
        ).exists()
        # Can add a review only if purchased AND hasn't reviewed yet
        user_can_review = user_has_purchased and user_review is None

    rating_breakdown = {i: reviews.filter(rating=i).count() for i in range(5, 0, -1)}

    context = {
        'product': product,
        'variants': variants,
        'selected_variant': selected_variant,
        'active_offer': active_offer,
        'original_price': original_price,
        'discounted_price': discounted_price,
        'wishlist_count': user_wishlist_count,
        'cart_count': user_cart_count,
        'cart_total': cart_total,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1) if avg_rating else 0,
        'avg_rating_int': round(avg_rating) if avg_rating else 0,
        'review_count': review_count,
        'user_review': user_review,
        'user_can_review': user_can_review,
        'user_has_purchased': user_has_purchased,
        'rating_breakdown': rating_breakdown,
    }

    return render(request, 'store/product_info.html', context)


@never_cache
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

# @never_cache
# @login_required
# def add_wishlist(request, id):
#     if request.method == 'POST':
#         variant_id = request.POST.get('variant_id')
        
#         variant = get_object_or_404(ProductVariant, id=variant_id, product_id=id)
        
#         try:
#             Wishlist.objects.create(user=request.user, variant=variant)
#             messages.success(request, f"{variant.product.name} ({variant.color.name}) added to your wishlist.")
#         except IntegrityError:
#             None
#         return redirect(request.META.get('HTTP_REFERER', 'home'))
    
#     return JsonResponse({'success': False, 'error': 'Invalid request method'})

@never_cache
@login_required
def add_wishlist(request, id):
    if request.method == 'POST':
        variant_id = request.POST.get('variant_id')

        variant = get_object_or_404(ProductVariant, id=variant_id, product_id=id)

        try:
            Wishlist.objects.create(
                user=request.user,
                variant=variant)

            messages.success(request, f"{variant.product.name} added to wishlist.")

        except IntegrityError:
            messages.warning(request, f"{variant.product.name} is already in your wishlist.")

        return redirect( request.META.get('HTTP_REFERER', 'home') )

    messages.error(request, "Invalid request.")
    return redirect('home')

@never_cache
@login_required
def remove_wishlist(request, id):
    if request.method == 'POST':
        try:
            wishlist_item = Wishlist.objects.get(user=request.user, variant_id=id)
            wishlist_item.delete()
            return JsonResponse({'success': True})
        except Wishlist.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Item not found in wishlist'}, status=404)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)
    
@never_cache
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


@never_cache
@login_required
def add_to_cart(request, id):
    if request.method == 'POST':
        variant_id = request.POST.get('variant_id')
        quantity = int(request.POST.get('quantity', 1))

        variant = get_object_or_404(ProductVariant,id=variant_id)

        if not variant.is_available:
            messages.error( request, "This product is currently unavailable.")

            return redirect(request.META.get('HTTP_REFERER', 'home'))

        if variant.stock < quantity:
            messages.error(request, f"Only {variant.stock} items available.")

            return redirect(request.META.get('HTTP_REFERER', 'home'))

        cart, created = Cart.objects.get_or_create(user=request.user)

        cart_item, item_created = CartItem.objects.get_or_create(cart=cart,product_variant=variant,defaults={'quantity': quantity})

        if not item_created:
            cart_item.quantity += quantity
            cart_item.save()

            messages.success(request,f"Quantity updated in cart.")
        else:
            messages.success( request, f"{variant.product.name} added to cart." )

        return redirect(request.META.get('HTTP_REFERER', 'home'))

    messages.error(request, "Invalid request.")
    return redirect('home')


@never_cache
@login_required
def update_cart(request, cart_item_id):
    if request.method == 'POST':
        try:
            cart_item = CartItem.objects.get(id=cart_item_id, cart__user=request.user)
            quantity = int(request.POST.get('quantity', 1))
            
            cart_item.quantity = quantity
            cart_item.save()
            
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

@never_cache
@login_required
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

@never_cache
@login_required
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
    orders = Order.objects.filter(user=user).prefetch_related(
        'ordered_items__product_variant__product'
    ).order_by('-created_at')
    for order in orders:
        attach_review_state(list(order.ordered_items.all()), request.user)
    profile = Profile.objects.get(user=user)
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all()

    form_data = request.session.pop('account_form_data', {})

    context = {
        'user': user,
        'orders': orders,
        'profile': profile,
        'wallet': wallet,
        'transactions': transactions,
        'wishlist_count': user_wishlist_count,
        'cart_count': user_cart_count,
        'cart_total': cart_total,
        'form_data': form_data,
    }
    return render(request, 'store/Account.html', context)


@never_cache
@login_required
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
        
        address.save()
        messages.success(request,"Address created successfully!!!")
        
        if address.is_default:
            UserAddress.objects.filter(user=request.user).exclude(id=address.id).update(is_default=False)

        return redirect('account') 
    return redirect('account',)

@never_cache
@login_required
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
     
@never_cache     
@login_required
def checkout(request):
    checkout_state = get_checkout_state(request)
    if not checkout_state['cart_items']:
        messages.warning(request, "Your cart is empty. Add some items before checking out.")
        return redirect('cart')

    context = {
        'cart_items': checkout_state['cart_items'],
        'subtotal': checkout_state['subtotal'],
        'coupon_discount': checkout_state['coupon_discount'],
        'total': checkout_state['total'],
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'available_coupons': checkout_state['available_coupons'],
        'coupon': checkout_state['coupon_code'],
        'wallet_balance': checkout_state['wallet'].balance,
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
            return process_order(request)

    return render(request, 'store/checkout.html', context)


def get_checkout_state(request):
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart).select_related(
            'product_variant__product',
            'product_variant__color',
        )
    except Cart.DoesNotExist:
        cart = None
        cart_items = CartItem.objects.none()

    subtotal = sum(item.quantity * item.product_variant.product.get_discounted_price() for item in cart_items)
    coupon_code = request.session.get('coupon')
    coupon = None
    coupon_discount = Decimal('0.00')

    available_coupons = Coupon.objects.filter(
        active=True,
        valid_from__lte=django_timezone.now(),
        valid_to__gte=django_timezone.now()
    )

    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            can_use, _message = coupon.can_use(request.user)
            min_purchase = coupon.min_purchase_amount or Decimal('0.00')
            if coupon.is_valid() and can_use and subtotal >= min_purchase:
                coupon_discount = coupon.apply_discount(subtotal)
            else:
                request.session.pop('coupon', None)
                coupon_code = None
                coupon = None
        except Coupon.DoesNotExist:
            request.session.pop('coupon', None)
            coupon_code = None

    total = max(subtotal - coupon_discount, Decimal('0.00'))
    wallet, _created = Wallet.objects.get_or_create(user=request.user)

    return {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'coupon': coupon,
        'coupon_code': coupon_code,
        'coupon_discount': coupon_discount,
        'total': total,
        'wallet': wallet,
        'available_coupons': available_coupons,
    }

CHECKOUT_PAYMENT_METHODS = {'cod', 'razorpay', 'wallet'}
PENDING_RAZORPAY_CHECKOUT_SESSION_KEY = 'pending_razorpay_checkout'

def get_validated_checkout_data(request, payment_method=None, include_razorpay_fields=False):
    checkout_state = get_checkout_state(request)
    errors = []

    if not checkout_state['cart'] or not checkout_state['cart_items']:
        errors.append("Your cart is empty. Add some items before checking out.")

    payment_method = payment_method or request.POST.get('payment_method')
    if payment_method not in CHECKOUT_PAYMENT_METHODS:
        errors.append("Please select a valid payment method.")

    address_data = extract_checkout_address(request, errors)
    cart_snapshot = []

    for item in checkout_state['cart_items']:
        variant = item.product_variant
        if item.quantity <= 0:
            errors.append(f"Invalid quantity for {variant.product.name}.")
            continue
        if not variant.is_available:
            errors.append(f"{variant.product.name} - {variant.color} is not available.")
        if item.quantity > variant.stock:
            errors.append(f"Only {variant.stock} item(s) available for {variant.product.name} - {variant.color}.")

        cart_snapshot.append({
            'cart_item_id': item.id,
            'variant_id': variant.id,
            'quantity': item.quantity,
            'price': str(variant.product.get_discounted_price()),
        })

    coupon = checkout_state['coupon']
    if coupon:
        can_use, coupon_message = coupon.can_use(request.user)
        min_purchase = coupon.min_purchase_amount or Decimal('0.00')
        if not coupon.is_valid():
            errors.append("The applied coupon is invalid or expired.")
        elif checkout_state['subtotal'] < min_purchase:
            errors.append(f"This coupon requires a minimum purchase of {coupon.min_purchase_amount}.")
        elif not can_use:
            errors.append(coupon_message or "You cannot use this coupon.")

    if payment_method == 'cod' and checkout_state['total'] < Decimal('1000.00'):
        errors.append("Cash on Delivery is not available for orders below ₹1000.")

    if payment_method == 'wallet' and checkout_state['total'] > checkout_state['wallet'].balance:
        errors.append("Insufficient balance in your wallet to complete this purchase.")

    if include_razorpay_fields:
        for field in ('razorpay_payment_id', 'razorpay_order_id', 'razorpay_signature'):
            if not request.POST.get(field):
                errors.append("Missing Razorpay payment details.")
                break

    return {
        'is_valid': not errors,
        'errors': errors,
        'payment_method': payment_method,
        'address_data': address_data,
        'cart_snapshot': cart_snapshot,
        **checkout_state,
    }


def extract_checkout_address(request, errors):
    use_new_address = request.POST.get('use_new_address') == 'on'

    if not use_new_address:
        selected_address_id = request.POST.get('selected_address')
        if not selected_address_id:
            errors.append("Please select an address or enter a new one.")
            return None
        try:
            selected_address = request.user.addresses.get(id=selected_address_id)
            return {
                'full_name': selected_address.full_name,
                'last_name': selected_address.last_name,
                'phone_number': selected_address.phone_number,
                'email': selected_address.email,
                'address_line_1': selected_address.address_line_1,
                'address_line_2': selected_address.address_line_2,
                'city': selected_address.city,
                'state': selected_address.state,
                'postal_code': selected_address.postal_code,
                'country': selected_address.country,
            }
        except UserAddress.DoesNotExist:
            errors.append("The selected address is no longer available. Please choose another or enter a new one.")
            return None

    required_fields = [
        'full_name', 'last_name', 'phone_number', 'email', 'address_line_1',
        'city', 'state', 'postal_code', 'country'
    ]
    address_data = {}
    for field in required_fields:
        value = request.POST.get(field, '').strip()
        if not value:
            errors.append(f"{field.replace('_', ' ').title()} is required.")
        address_data[field] = value

    address_data['address_line_2'] = request.POST.get('address_line_2', '').strip()

    if address_data.get('full_name') and not re.match(r'^[A-Za-z]+$', address_data['full_name']):
        errors.append("First name should contain letters only.")
    if address_data.get('last_name') and not re.match(r'^[A-Za-z]+$', address_data['last_name']):
        errors.append("Last name should contain letters only.")
    if address_data.get('phone_number') and not re.match(r'^[0-9]{10}$', address_data['phone_number']):
        errors.append("Phone number must contain exactly 10 digits.")
    if address_data.get('email') and not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', address_data['email']):
        errors.append("Enter a valid email address.")
    for field in ('city', 'state', 'country'):
        if address_data.get(field) and not re.match(r'^[A-Za-z ]+$', address_data[field]):
            errors.append(f"{field.title()} should contain letters only.")
    if address_data.get('postal_code') and not re.match(r'^[0-9]{6}$', address_data['postal_code']):
        errors.append("Postal code must contain exactly 6 digits.")

    return address_data


@never_cache
@login_required
@require_POST
def create_razorpay_checkout_order(request):
    validated = get_validated_checkout_data(request, payment_method='razorpay')
    if not validated['is_valid']:
        return JsonResponse({'success': False, 'errors': validated['errors']}, status=400)

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    amount_paise = int(validated['total'] * 100)
    if amount_paise <= 0:
        return JsonResponse({'success': False, 'errors': ["Invalid payable amount."]}, status=400)

    try:
        razorpay_order = client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'payment_capture': '1'
        })
    except Exception:
        logger.exception("Razorpay order creation failed for user %s", request.user.id)
        return JsonResponse({'success': False, 'errors': ["Unable to start Razorpay payment. Please try again."]}, status=502)

    request.session[PENDING_RAZORPAY_CHECKOUT_SESSION_KEY] = {
        'razorpay_order_id': razorpay_order['id'],
        'amount_paise': amount_paise,
        'address_data': validated['address_data'],
        'cart_snapshot': validated['cart_snapshot'],
        'coupon': validated['coupon_code'],
        'coupon_discount': str(validated['coupon_discount']),
        'total': str(validated['total']),
    }
    request.session.modified = True

    return JsonResponse({
        'success': True,
        'key': settings.RAZORPAY_KEY_ID,
        'order_id': razorpay_order['id'],
        'amount': amount_paise,
        'currency': 'INR',
    })


@never_cache
@csrf_exempt
@login_required
@require_POST
def handle_failed_payment(request):
    request.session.pop(PENDING_RAZORPAY_CHECKOUT_SESSION_KEY, None)
    request.session.modified = True
    return JsonResponse({
        'success': True,
        'message': 'Payment was not completed. No order was created.'
    })


def process_order(request):
    payment_method = request.POST.get('payment_method')
    include_razorpay_fields = payment_method == 'razorpay'
    validated = get_validated_checkout_data(request, include_razorpay_fields=include_razorpay_fields)

    if not validated['is_valid']:
        for error in validated['errors']:
            messages.error(request, error)
        return redirect('checkout')

    try:
        if payment_method == 'razorpay':
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            order = process_razorpay_checkout(request, validated, client)
        else:
            order = create_validated_order(request, validated)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('checkout')
    except razorpay.errors.SignatureVerificationError:
        messages.error(request, "Razorpay payment verification failed. Please contact support if you've been charged.")
        return redirect('checkout')
    except Exception:
        logger.exception("Checkout processing failed for user %s", request.user.id)
        messages.error(request, "There was an error processing your order. Please try again.")
        return redirect('checkout')

    return redirect('order_confirmation', order_id=order.id)


def process_razorpay_checkout(request, validated, client):
    razorpay_payment_id = request.POST.get('razorpay_payment_id')
    razorpay_order_id = request.POST.get('razorpay_order_id')
    razorpay_signature = request.POST.get('razorpay_signature')

    pending_checkout = request.session.get(PENDING_RAZORPAY_CHECKOUT_SESSION_KEY)
    if not pending_checkout or pending_checkout.get('razorpay_order_id') != razorpay_order_id:
        raise ValueError("Razorpay checkout session expired. Please try again.")

    if Order.objects.filter(razorpay_payment_id=razorpay_payment_id).exists():
        raise ValueError("This Razorpay payment has already been processed.")

    client.utility.verify_payment_signature({
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    })

    if int(validated['total'] * 100) != int(pending_checkout.get('amount_paise', 0)):
        raise ValueError("Checkout amount changed. Please retry payment.")

    if validated['cart_snapshot'] != pending_checkout.get('cart_snapshot'):
        raise ValueError("Your cart changed after payment started. Please contact support if payment was captured.")

    order = create_validated_order(
        request,
        validated,
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
    )
    request.session.pop(PENDING_RAZORPAY_CHECKOUT_SESSION_KEY, None)
    request.session.modified = True
    return order


def create_validated_order(request, validated, razorpay_order_id=None, razorpay_payment_id=None):
    payment_method = validated['payment_method']

    with transaction.atomic():
        cart = Cart.objects.select_for_update().get(user=request.user)
        cart_items = list(
            CartItem.objects.select_for_update()
            .filter(cart=cart)
            .select_related('product_variant__product', 'product_variant__color')
        )

        if not cart_items:
            raise ValueError("Your cart is empty. Add some items before checking out.")

        variant_ids = [item.product_variant_id for item in cart_items]
        locked_variants = {
            variant.id: variant
            for variant in ProductVariant.objects.select_for_update()
            .filter(id__in=variant_ids)
            .select_related('product', 'color')
        }

        subtotal = Decimal('0.00')
        for item in cart_items:
            variant = locked_variants.get(item.product_variant_id)
            if not variant:
                raise ValueError("One of your cart items is no longer available.")
            if item.quantity <= 0:
                raise ValueError(f"Invalid quantity for {variant.product.name}.")
            if not variant.is_available:
                raise ValueError(f"{variant.product.name} - {variant.color} is not available.")
            if item.quantity > variant.stock:
                raise ValueError(f"Only {variant.stock} item(s) available for {variant.product.name} - {variant.color}.")
            subtotal += item.quantity * variant.product.get_discounted_price()

        coupon_code = request.session.get('coupon')
        coupon = None
        coupon_discount = Decimal('0.00')
        if coupon_code:
            try:
                coupon = Coupon.objects.select_for_update().get(code=coupon_code)
            except Coupon.DoesNotExist:
                raise ValueError("Applied coupon no longer exists.")
            
            can_use, coupon_message = coupon.can_use(request.user)
            min_purchase = coupon.min_purchase_amount or Decimal('0.00')
            if not coupon.is_valid():
                raise ValueError("The applied coupon is invalid or expired.")
            if subtotal < min_purchase:
                raise ValueError(f"This coupon requires a minimum purchase of {coupon.min_purchase_amount}.")
            if not can_use:
                raise ValueError(coupon_message or "You cannot use this coupon.")
            coupon_discount = coupon.apply_discount(subtotal)

        total = max(subtotal - coupon_discount, Decimal('0.00'))
        if total != validated['total']:
            raise ValueError("Checkout total changed. Please review your cart and try again.")

        wallet = Wallet.objects.select_for_update().get(user=request.user)
        if payment_method == 'wallet':
            if total > wallet.balance:
                raise ValueError("Insufficient balance in your wallet to complete this purchase.")
            wallet.balance -= total
            wallet.save()
        elif payment_method == 'cod':
            if total < Decimal('1000.00'):
                raise ValueError("Cash on Delivery is not available for orders below ₹1000.")
        elif payment_method == 'razorpay':
            if not razorpay_order_id or not razorpay_payment_id:
                raise ValueError("Missing Razorpay payment details.")
            if Order.objects.select_for_update().filter(razorpay_payment_id=razorpay_payment_id).exists():
                raise ValueError("This Razorpay payment has already been processed.")

        order = Order.objects.create(
            user=request.user,
            total_price=total,
            payment_method=payment_method,
            payment_status='paid' if payment_method in ('razorpay', 'wallet') else 'unpaid',
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            coupon=coupon_code,
            discount_amount_coupon=coupon_discount,
        )

        if payment_method == 'wallet':
            WalletTransaction.objects.create(
                wallet=wallet,
                amount=total,
                transaction_type='debit',
                description=f'Wallet payment for order #{order.id}',
                balance_after=wallet.balance,
                reference_type='order',
                reference_id=str(order.id),
            )

        OrderAddress.objects.create(order=order, **validated['address_data'])

        total_before_coupon = subtotal
        for item in cart_items:
            variant = locked_variants[item.product_variant_id]
            discounted_price = variant.product.get_discounted_price()
            if total_before_coupon > 0:
                item_coupon_discount = (item.quantity * discounted_price / total_before_coupon) * coupon_discount
            else:
                item_coupon_discount = Decimal('0.00')

            OrderItem.objects.create(
                order=order,
                product_variant=variant,
                quantity=item.quantity,
                price=discounted_price,
                item_status='pending' if payment_method == 'cod' else 'processing',
                payment_status_item='unpaid' if payment_method == 'cod' else 'paid',
                orderItem_coupon_discount=item_coupon_discount
            )

            variant.stock -= item.quantity
            variant.save()

        if coupon:
            coupon.increment_usage(request.user)

        cart.items.all().delete()
        request.session.pop('coupon', None)

    return order


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
        required_fields = [
            'full_name','last_name','phone_number','email','address_line_1',
            'city','state','postal_code','country']

        for field in required_fields:
            if not request.POST.get(field, '').strip():
                messages.error(
                    request,
                    f"{field.replace('_', ' ').title()} is required.")
                return False


        full_name = request.POST.get('full_name').strip()
        last_name = request.POST.get('last_name').strip()
        phone_number = request.POST.get('phone_number').strip()
        email = request.POST.get('email').strip()
        city = request.POST.get('city').strip()
        state = request.POST.get('state').strip()
        country = request.POST.get('country').strip()
        postal_code = request.POST.get('postal_code').strip()

        name_regex = r'^[A-Za-z]+$'
        city_regex = r'^[A-Za-z ]+$'
        phone_regex = r'^[0-9]{10}$'
        postal_regex = r'^[0-9]{6}$'

        if not re.match(name_regex, full_name):
            messages.error(request,"First name should contain letters only.")
            return False

        if not re.match(name_regex, last_name):
            messages.error(request,"Last name should contain letters only.")
            return False

        if not re.match(phone_regex, phone_number):
            messages.error(request,"Phone number must contain exactly 10 digits.")
            return False

        if not re.match(city_regex, city):
            messages.error(request,"City should contain letters only.")
            return False

        if not re.match(city_regex, state):
            messages.error(request,"State should contain letters only.")
            return False

        if not re.match(city_regex, country):
            messages.error(request,"Country should contain letters only.")
            return False

        if not re.match(postal_regex, postal_code):
            messages.error(request,"Postal code must contain exactly 6 digits.")
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

@never_cache
@login_required
def show_order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = attach_review_state(
        list(OrderItem.objects.filter(order=order).select_related('product_variant__product')),
        request.user
    )
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

    razorpay_order = None
    if order.payment_method == 'razorpay' and order.payment_status == 'unpaid':
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = client.order.create({
            'amount': int(order.total_price * 100),  
            'currency': 'INR',
            'payment_capture': '1'
        })

    context = {
        'order': order,
        'order_items': order_items,
        'order_address': order_address,
        'wishlist_count': user_wishlist_count,
        'cart_count': user_cart_count,
        'cart_total': cart_total,
        'razorpay_order': razorpay_order,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    }
    return render(request, 'store/ordered_product_info.html', context)

@csrf_exempt
def razorpay_payment_success(request):
    if request.method == 'POST':
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        params_dict = {
            'razorpay_payment_id': request.POST.get('razorpay_payment_id'),
            'razorpay_order_id': request.POST.get('razorpay_order_id'),
            'razorpay_signature': request.POST.get('razorpay_signature')
        }

        try:
            client.utility.verify_payment_signature(params_dict)
        except:
            return JsonResponse({'success': False})

        order_id = request.POST.get('order_id')
        order = Order.objects.get(id=order_id)

        order.payment_status = 'paid'
        order.save()

        OrderItem.objects.filter(order=order).update(payment_status_item='paid')

        return JsonResponse({'success': True})

    return JsonResponse({'success': False})

@login_required
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


@never_cache
@require_POST
@login_required
def edit_details(request):
    user = request.user

    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        messages.error(request, "Profile does not exist.")
        return redirect(reverse('account') + '#tab-account')

    username = request.POST.get("username", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    phone_number = request.POST.get("phone_number", "").strip()

    current_password = request.POST.get("current_password", "").strip()
    new_password = request.POST.get("new_password", "").strip()
    confirm_new_password = request.POST.get("confirm_new_password", "").strip()

    def preserve_and_redirect(error_message):
        form_data = request.POST.dict()
        form_data.pop('csrfmiddlewaretoken', None)
        form_data.pop('current_password', None)
        form_data.pop('new_password', None)
        form_data.pop('confirm_new_password', None)
        request.session['account_form_data'] = form_data
        messages.error(request, error_message)
        return redirect(reverse('account') + '#tab-account')

    user_updated = False
    profile_updated = False

    if username:
        if not re.match(r"^[A-Za-z\s]+$", username):
            return preserve_and_redirect("First name can contain only letters and spaces.")

        user.username = username
        user_updated = True

    if last_name:
        if not re.match(r"^[A-Za-z\s]+$", last_name):
            return preserve_and_redirect("Last name can contain only letters and spaces.")

        user.last_name = last_name
        user_updated = True

    if phone_number:
        if not phone_number.isdigit():
            return preserve_and_redirect("Phone number must contain only digits.")

        if len(phone_number) != 10:
            return preserve_and_redirect("Phone number must be 10 digits long.")

        profile.phone = phone_number
        profile_updated = True

    if current_password or new_password or confirm_new_password:
        if not (current_password and new_password and confirm_new_password):
            return preserve_and_redirect("Please fill all password fields.")

        if not user.check_password(current_password):
            return preserve_and_redirect("Current password is incorrect.")

        if len(new_password) < 8:
            return preserve_and_redirect("New password must be at least 8 characters long.")

        if not re.search(r"[A-Z]", new_password):
            return preserve_and_redirect("New password must contain at least one uppercase letter.")

        if not re.search(r"[a-z]", new_password):
            return preserve_and_redirect("New password must contain at least one lowercase letter.")

        if not re.search(r"[0-9]", new_password):
            return preserve_and_redirect("New password must contain at least one number.")

        if not re.search(r"[\W_]", new_password):
            return preserve_and_redirect("New password must contain at least one special character.")

        if new_password != confirm_new_password:
            return preserve_and_redirect("New passwords do not match.")

        user.set_password(new_password)
        user_updated = True

    if user_updated:
        user.save()
        if current_password:
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was successfully updated!")

    if profile_updated:
        profile.save()

    if user_updated or profile_updated:
        messages.success(request, "Your profile was successfully updated.")
        request.session.pop('account_form_data', None)
    else:
        messages.info(request, "No changes were made.")
        
    return redirect(reverse('account') + '#tab-account')


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
                    description=f'Refund for cancelled item in order #{order.id}',
                    balance_after=user_wallet.balance,
                    reference_type='order_item',
                    reference_id=str(item.id),
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

@never_cache
@login_required
def contact(request):
    return render(request,'store/contact.html')

@require_POST
def return_item(request):
    item_id = request.POST.get('item_id')
    reason = request.POST.get('reason')
    try:
        item = OrderItem.objects.get(id=item_id, order__user=request.user)
        if item.item_status == 'delivered' and not item.return_request:
            item.return_request = True   
            item.save()

            return JsonResponse({'success': True, 'message': 'Return request submitted successfully !!!'})
        else:
            return JsonResponse({'success': False, 'message': 'Unable to process return request !!!'})
    except OrderItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Item not found !!!'})


class RequestDomainPasswordResetView(PasswordResetView):
    def form_valid(self, form):
        email = form.cleaned_data["email"]
        for user in form.get_users(email):
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = self.token_generator.make_token(user)
            reset_path = reverse(
                "password_reset_confirm",
                kwargs={"uidb64": uid, "token": token},
            )
            reset_link = self.request.build_absolute_uri(reset_path)
            username = user.get_username()

            if not send_password_reset_email(user.email, username, reset_link):
                logger.error("Password reset email sending failed for %s", user.email)

        return HttpResponseRedirect(self.get_success_url())

    
@login_required
@never_cache
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # One review per user per product
    if Review.objects.filter(product=product, user=request.user).exists():
        messages.warning(request, "You have already reviewed this product.")
        return redirect_to_product_reviews(product.id)

    # Only users who purchased & received the product can review
    delivered_order_item = OrderItem.objects.filter(
        order__user=request.user,
        product_variant__product=product,
        item_status='delivered'
    ).exclude(review__isnull=False).first()

    if not delivered_order_item:
        messages.error(request, "You can only review products you have purchased and received.")
        return redirect_to_product_reviews(product.id)

    if request.method != 'POST':
        return redirect_to_product_reviews(product.id)

    rating = request.POST.get('rating')
    title = request.POST.get('title', '').strip()
    comment = request.POST.get('comment', '').strip()

    try:
        rating = int(rating)
    except (TypeError, ValueError):
        rating = None

    if rating not in range(1, 6) or not comment:
        messages.error(request, "Rating and comment are required.")
        return redirect_to_product_reviews(product.id)

    Review.objects.create(
        product=product,
        user=request.user,
        order_item=delivered_order_item,
        rating=rating,
        title=title,
        comment=comment,
    )
    messages.success(request, "Thank you! Your review has been submitted.")

    return redirect_to_product_reviews(product.id)


@login_required
@never_cache
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        title = request.POST.get('title', '').strip()
        comment = request.POST.get('comment', '').strip()

        try:
            rating = int(rating)
        except (TypeError, ValueError):
            rating = None

        if rating not in range(1, 6) or not comment:
            messages.error(request, "Rating and comment are required.")
        else:
            review.rating = rating
            review.title = title
            review.comment = comment
            review.save()
            messages.success(request, "Your review has been updated.")

    return redirect_to_product_reviews(review.product.id)


@login_required
@require_POST
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    product_id = review.product_id
    review.delete()
    messages.success(request, "Review deleted.")
    return redirect_to_product_reviews(product_id)
