from django.db import IntegrityError
from django.shortcuts import render, redirect , get_object_or_404
from django.urls import reverse
from django.utils.text import slugify
from django.utils.text import Truncator
from products.models import Category , Brand, Color, Gender, Product , ProductVariant
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST, require_GET
import base64
import re
from base64 import b64decode
from PIL import Image
import os
from django.core.files.base import ContentFile
from django.views.decorators.http import require_POST
import base64
from io import BytesIO
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test , login_required
from django.core.exceptions import PermissionDenied
from django.contrib.auth import logout
from django.urls import reverse
from home.models import *
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from .models import *
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum
from django.utils.dateparse import parse_datetime
from django.views.decorators.cache import never_cache
from django.db.models import Sum, F, Count, DecimalField, Case, When, Value , Q
from django.db.models.functions import Coalesce
from django.db import transaction
import cloudinary.uploader
import logging
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import ProtectedError
from datetime import datetime
from django.template.loader import get_template
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)

CATEGORY_NAME_PATTERN = re.compile(r'^[A-Za-z]+$')
def _is_valid_category_name(name):
    return bool(name and CATEGORY_NAME_PATTERN.fullmatch(name))


def _get_int_param(request, name, default):
    try:
        return int(request.GET.get(name, default))
    except (TypeError, ValueError):
        return default


def _cloudinary_public_id(image_field):
    return getattr(image_field, 'public_id', None) or str(image_field)


def _delete_cloudinary_image(image_field):
    if not image_field:
        return
    public_id = _cloudinary_public_id(image_field)
    if not public_id:
        return
    try:
        cloudinary.uploader.destroy(public_id, resource_type='image')
    except Exception as exc:
        logger.warning("Cloudinary delete failed for %s: %s", public_id, exc)


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def dashboard(request):
    return render(request,'dashboard.html') 


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_Category(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        logo = request.FILES.get('logo')

        if not _is_valid_category_name(name):
            messages.error(request, 'Category name must contain letters only, without spaces or special characters.')
            return render(request, 'addCategory.html', {'name': name, 'description': description})

        if Category.objects.filter(name__iexact=name).exists():
            messages.error(request, 'A category with this name already exists.')
            return render(request, 'addCategory.html', {'name': name, 'description': description})

        slug = slugify(name)

        if Category.objects.filter(slug=slug).exists():
            messages.error(request, 'A category with this name already exists.')
            return render(request, 'addCategory.html', {'name': name, 'description': description})

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
    category_name = request.GET.get('name', '').strip()
    category_id = request.GET.get('id')
    category_query = Category.objects.filter(name__iexact=category_name)
    if category_id:
        category_query = category_query.exclude(id=category_id)
    data = {
        'exists': category_query.exists(),
        'valid': _is_valid_category_name(category_name),
    }
    return JsonResponse(data)


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def category_list(request):
    offers = Offer.objects.filter(is_active=True)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        columns = ['name', 'description', 'status', 'offer__name', 'id']
        draw = _get_int_param(request, 'draw', 1)
        start = max(_get_int_param(request, 'start', 0), 0)
        length = _get_int_param(request, 'length', 10)
        length = 10 if length <= 0 else min(length, 100)
        search_value = request.GET.get('search[value]', '').strip()

        categories = Category.objects.select_related('offer').all()
        records_total = categories.count()

        if search_value:
            categories = categories.filter(
                Q(name__icontains=search_value)
                | Q(description__icontains=search_value)
                | Q(offer__name__icontains=search_value)
            )

        records_filtered = categories.count()

        order_column = request.GET.get('order[0][column]', '0')
        order_dir = request.GET.get('order[0][dir]', 'asc')
        try:
            order_field = columns[int(order_column)]
        except (ValueError, IndexError):
            order_field = 'name'
        if order_dir == 'desc':
            order_field = f'-{order_field}'

        page_categories = categories.order_by(order_field, 'id')[start:start + length]
        data = [
            {
                'id': category.id,
                'name': category.name,
                'description': Truncator(category.description or '-').words(7),
                'status': category.status,
                'offer_id': category.offer_id,
            }
            for category in page_categories
        ]

        return JsonResponse({
            'draw': draw,
            'recordsTotal': records_total,
            'recordsFiltered': records_filtered,
            'data': data,
        })

    offer_options = [{'id': offer.id, 'label': f'{offer.name} {offer.discount}% off'} for offer in offers]
    return render(request, 'categoryList.html', {'offers': offers, 'offer_options': offer_options})

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def toggle_category_status(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.status = not category.status
    category.save()
    return JsonResponse({'status': category.status})


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_category(request, category_id):
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Invalid request method."}, status=405
        )

    category = get_object_or_404(Category, id=category_id)
    if Product.objects.filter(category=category).exists():
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "This category cannot be deleted because one or more "
                    "products are assigned to it. Remove or reassign those "
                    "products first."
                ),
            },
            status=400,
        )

    try:
        category_name = category.name
        category.delete()

        return JsonResponse(
            {
                "success": True,
                "message": f"Category '{category_name}' deleted successfully.",
            }
        )

    except ProtectedError:
        return JsonResponse(
            {
                "success": False,
                "message": "This category is being used by other records and cannot be deleted.",
            },
            status=400,
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Error deleting category: {str(e)}"},
            status=500,
        )


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()

        if not _is_valid_category_name(name):
            messages.error(
                request,
                "Category name must contain letters only, without spaces or special characters.",
            )
            category.name = name
            category.description = description
        elif (
            Category.objects.filter(name__iexact=name).exclude(id=category.id).exists()
        ):
            messages.error(request, "A category with this name already exists.")
            category.name = name
            category.description = description
        else:
            category.name = name
            category.description = description
            category.slug = slugify(category.name)
            category.save()
            messages.success(request, "Category updated successfully.")
            return redirect("Admin:categorylist")

    return render(request, "editCategory.html", {"category": category})


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def brand_list(request):
    brands = Brand.objects.all()
    return render(request, "brandList.html", {"brands": brands})


@require_GET
def check_brand_exists(request):
    brand_name = request.GET.get("name")
    brand_id = request.GET.get("id")
    if brand_id:
        exists = (
            Brand.objects.filter(name__iexact=brand_name).exclude(id=brand_id).exists()
        )
    else:
        exists = Brand.objects.filter(name__iexact=brand_name).exists()
    return JsonResponse({"exists": exists})


@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_brand(request):
    brand_name = request.POST.get("name")
    if Brand.objects.filter(name__iexact=brand_name).exists():
        return JsonResponse({"success": False, "error": "This brand already exists."})
    else:
        Brand.objects.create(name=brand_name)
        return JsonResponse({"success": True})


@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_brand(request):
    brand_id = request.POST.get("id")
    brand_name = request.POST.get("name")
    try:
        brand = Brand.objects.get(id=brand_id)
        if Brand.objects.filter(name__iexact=brand_name).exclude(id=brand_id).exists():
            return JsonResponse(
                {"success": False, "error": "This brand name is already in use."}
            )
        brand.name = brand_name
        brand.save()
        return JsonResponse({"success": True})
    except Brand.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Brand not found.'})

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_brand(request):
    brand_id = request.POST.get('id')
    try:
        brand = Brand.objects.get(id=brand_id)
        brand.delete()
        return JsonResponse({'success': True})
    except Brand.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Brand not found.'})
    

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_product(request, product_id):
    product  = get_object_or_404(Product, id=product_id)
    variants = product.variants.select_related('color').all()
 
    if request.method == 'POST':
        try:
            with transaction.atomic():

                product.name = request.POST.get("name", "").strip()
                product.gender = get_object_or_404(
                    Gender, id=request.POST.get("gender")
                )
                product.category = get_object_or_404(
                    Category, id=request.POST.get("category")
                )
                product.brand = get_object_or_404(Brand, id=request.POST.get("brand"))
                product.description = request.POST.get("description", "").strip()
                product.save()

                for variant in variants:
                    vid = variant.id

                    color_id = request.POST.get(f"variant_color_{vid}")
                    if color_id:
                        variant.color = get_object_or_404(Color, id=color_id)

                    variant.price = request.POST.get(f"variant_price_{vid}")
                    variant.stock = request.POST.get(f"variant_stock_{vid}")
                    variant.is_available = (
                        request.POST.get(f"variant_is_available_{vid}") == "True"
                    )

                    for slot in range(1, 4):
                        image_attr = f"image_{slot}"
                        delete_value = request.POST.get(
                            f"delete_image_{vid}_{slot}", ""
                        ).strip()
                        cropped_image = request.POST.get(
                            f"new_image_{vid}_{slot}", ""
                        ).strip()
                        existing = getattr(variant, image_attr)

                        if delete_value == "true" and existing and not cropped_image:
                            try:
                                cloudinary.uploader.destroy(
                                    str(existing), resource_type="image"
                                )
                                logger.info("Deleted Cloudinary image: %s", existing)
                            except Exception as exc:
                                logger.warning(
                                    "Cloudinary delete failed for %s: %s", existing, exc
                                )
                            setattr(variant, image_attr, None)

                        if cropped_image:
                            if not cropped_image.startswith("data:image"):
                                messages.warning(
                                    request,
                                    f"Image slot {slot} for variant {vid} was skipped (invalid data).",
                                )
                                continue

                            if existing:
                                try:
                                    cloudinary.uploader.destroy(
                                        str(existing), resource_type="image"
                                    )
                                except Exception as exc:
                                    logger.warning(
                                        "Could not delete old image %s before replace: %s",
                                        existing,
                                        exc,
                                    )

                            try:
                                result = cloudinary.uploader.upload(
                                    cropped_image,
                                    folder="products",
                                    resource_type="image",
                                )
                                public_id = result.get("public_id")
                                if public_id:
                                    setattr(variant, image_attr, public_id)
                                    logger.info(
                                        "Uploaded new image to %s for variant %s slot %s",
                                        public_id,
                                        vid,
                                        slot,
                                    )
                            except Exception as exc:
                                logger.exception(
                                    "Cloudinary upload failed for variant %s slot %s",
                                    vid,
                                    slot,
                                )
                                messages.warning(
                                    request,
                                    f"Image {slot} (variant {vid}) failed to upload: {exc}",
                                )

                    variant.save()

            messages.success(request, "Product updated successfully.")
            return redirect("Admin:productlist")

        except Exception as exc:
            logger.exception("Product update failed for product_id=%s", product_id)
            messages.error(request, f"Product update failed: {exc}")

    context = {
        "product": product,
        "variants": variants,
        "genders": Gender.objects.all(),
        "categories": Category.objects.all(),
        "brands": Brand.objects.all(),
        "colors": Color.objects.all(),
    }
    return render(request, "editProduct.html", context)


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_product(request):
    if request.method == "POST":
        print("=" * 60)
        print("ADD PRODUCT POST RECEIVED")
        print("=" * 60)

        name = request.POST.get("name")
        gender_id = request.POST.get("gender")
        category_id = request.POST.get("category")
        brand_id = request.POST.get("brand")
        description = request.POST.get("description")
        color_id = request.POST.get("color")
        price = request.POST.get("price")
        stock = request.POST.get("stock")
        is_available = request.POST.get("is_available") == "True"

        for i in range(1, 4):
            val = request.POST.get(f"cropped_image_{i}", "")
            starts_with_data = val.startswith("data:image") if val else False
            print(
                f"cropped_image_{i} length: {len(val)} | starts_with_data: {starts_with_data}"
            )

        try:
            gender = Gender.objects.get(id=gender_id)
            category = Category.objects.get(id=category_id)
            brand = Brand.objects.get(id=brand_id)
            color = Color.objects.get(id=color_id)
        except Exception as e:
            print(f"FK lookup failed: {e}")
            messages.error(request, f"Invalid selection: {e}")
            return redirect("addProduct")

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
            print(f"Product created: id={product.id}, name={product.name}")
        except IntegrityError as e:
            print(f"Product creation IntegrityError: {e}")
            messages.error(request, "Error creating product. Please try again.")
            return redirect("addProduct")

        variant = ProductVariant(
            product=product,
            color=color,
            price=price,
            stock=stock,
            is_available=is_available,
        )
        variant.save()
        print(f"Variant created: id={variant.id}")

        for i in range(1, 4):
            image_data_url = request.POST.get(f"cropped_image_{i}", "").strip()
            if not image_data_url:
                print(f"Image {i}: SKIPPED - empty")
                continue
            if not image_data_url.startswith("data:image"):
                print(
                    f"Image {i}: SKIPPED - not a valid data URL. Got: {image_data_url[:50]}"
                )
                continue
            try:
                print(f"Image {i}: Uploading to Cloudinary...")
                upload_result = cloudinary.uploader.upload(
                    image_data_url,
                    folder="products",
                    resource_type="image",
                )
                public_id = upload_result.get("public_id")
                secure_url = upload_result.get("secure_url")
                print(
                    f"Image {i}: Upload SUCCESS | public_id={public_id} | url={secure_url}"
                )
                setattr(variant, f"image_{i}", public_id)
            except Exception as e:
                print(f"Image {i}: Cloudinary UPLOAD FAILED - {e}")
                messages.warning(request, f"Image {i} failed to upload: {e}")

        variant.save()
        print(
            f"Variant saved with images: image_1={variant.image_1}, image_2={variant.image_2}, image_3={variant.image_3}"
        )
        print("=" * 60)

        messages.success(request, "Product added successfully!")
        return redirect(reverse("Admin:productlist"))

    else:
        context = {
            "genders": Gender.objects.all(),
            "categories": Category.objects.all(),
            "brands": Brand.objects.all(),
            "colors": Color.objects.all(),
        }
        return render(request, "addProduct.html", context)


def superuser_required(view_func):
    def check_superuser(user):
        return user.is_superuser

    decorated_view_func = user_passes_test(check_superuser, login_url="login")(
        view_func
    )
    return decorated_view_func


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def products_list(request):
    products = (
        Product.objects.prefetch_related("variants", "variants__color")
        .select_related("offer", "category", "brand", "gender")
        .all()
        .order_by("-created_at")
    )

    paginator = Paginator(products, 10)
    page_number = request.GET.get("page")

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    offers = Offer.objects.filter(is_active=True)

    context = {
        "products": page_obj,
        "offers": offers,
        "paginator": paginator,
    }
    return render(request, "productsList.html", context)


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def product_details(request, product_id):
    product = get_object_or_404(
        Product.objects.prefetch_related("variants", "variants__color").select_related(
            "offer", "category", "brand", "gender"
        ),
        id=product_id,
    )

    context = {
        "product": product,
        "variants": product.variants.all().order_by("color__name"),
    }

    return render(request, "productDetails.html", context)


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        try:
            with transaction.atomic():
                for variant in product.variants.all():
                    for i in range(1, 4):
                        image_field = getattr(variant, f"image_{i}")
                        if image_field:
                            try:
                                cloudinary.uploader.destroy(
                                    str(image_field), resource_type="image"
                                )
                            except:
                                pass
                product.delete()

            messages.success(
                request,
                f"Product '{product.name}' and all its variants have been deleted successfully.",
            )
            return JsonResponse({"success": True})

        except Exception as e:
            logger.exception("Error deleting product %s", product_id)
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product_name = variant.product.name
    color_name = variant.color.name

    if request.method == "POST":
        try:
            with transaction.atomic():
                for i in range(1, 4):
                    image_field = getattr(variant, f"image_{i}")
                    if image_field:
                        try:
                            cloudinary.uploader.destroy(
                                str(image_field), resource_type="image"
                            )
                        except:
                            pass

                variant.delete()

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Variant ({color_name}) deleted from {product_name}.",
                }
            )

        except Exception as e:
            logger.exception("Error deleting variant %s", variant_id)
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({"success": False}, status=400)


@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def toggle_variant_availability(request):
    variant_id = request.POST.get("variant_id")
    try:
        variant = ProductVariant.objects.get(id=variant_id)
        variant.is_available = not variant.is_available
        variant.save()
        return JsonResponse(
            {
                "success": True,
                "is_available": variant.is_available,
                "status_text": "Available" if variant.is_available else "Not Available",
            }
        )
    except ProductVariant.DoesNotExist:
        return JsonResponse({"success": False}, status=404)


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_list(request):
    users = User.objects.all().order_by("-date_joined")
    return render(request, "userList.html", {"users": users})


@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def toggle_user_status(request):
    user_id = request.POST.get("user_id")
    is_active = request.POST.get("is_active") == "true"

    try:
        user = User.objects.get(id=user_id)
        user.is_active = is_active
        user.save()
        return JsonResponse({"success": True})
    except User.DoesNotExist:
        return JsonResponse({"success": False}, status=404)


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_variant(request, id):
    product = get_object_or_404(Product, id=id)

    if request.method == "POST":
        try:
            with transaction.atomic():
                color_id = request.POST.get("color")
                if not color_id:
                    messages.error(request, "Color is required.")
                    return render(request, "addVariant.html", get_context(product))

                if ProductVariant.objects.filter(
                    product=product, color_id=color_id
                ).exists():
                    messages.warning(
                        request,
                        f"A variant with color '{Color.objects.get(id=color_id).name}' already exists for this product.",
                    )
                    return render(request, "addVariant.html", get_context(product))

                variant = ProductVariant(
                    product=product,
                    color_id=color_id,
                    stock=request.POST.get("stock"),
                    price=request.POST.get("price"),
                    is_available=request.POST.get("is_available") == "True",
                )

                for i in range(1, 4):
                    cropped_data = request.POST.get(f"cropped_image_{i}")
                    if cropped_data and cropped_data.startswith("data:image"):
                        try:
                            result = cloudinary.uploader.upload(
                                cropped_data, folder="products", resource_type="image"
                            )
                            setattr(variant, f"image_{i}", result["public_id"])
                        except Exception as e:
                            logger.warning(f"Image {i} upload failed for variant: {e}")
                            messages.warning(request, f"Image {i} failed to upload.")

                variant.save()

                messages.success(request, "Variant added successfully!")
                return redirect("Admin:productlist")

        except Exception as exc:
            logger.exception("Failed to add variant for product %s", id)
            messages.error(request, f"Failed to add variant: {exc}")

    context = get_context_colors(product)
    return render(request, "addVariant.html", context)


def get_context_colors(product):
    used_colors = ProductVariant.objects.filter(product=product).values_list(
        "color_id", flat=True
    )
    available_colors = Color.objects.exclude(id__in=used_colors)
    return {
        "product": product,
        "colors": available_colors,
    }


@never_cache
def logout_admin(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect(reverse("login"))


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def show_order_list(request):
    orders = (
        Order.objects.all().select_related("user").prefetch_related("ordered_items")
    )
    for order in orders:
        order.admin_display_status = calculate_order_status(order)

    context = {"orders": orders}
    return render(request, "orderlist.html", context)


def get_order_with_pricing_details(order_id):
    order = get_object_or_404(
        Order.objects.select_related("user", "order_address").prefetch_related(
            "ordered_items__product_variant__product__brand",
            "ordered_items__product_variant__product__category",
            "ordered_items__product_variant__color",
        ),
        id=order_id,
    )
    order_items = list(order.ordered_items.all())
    subtotal = Decimal("0.00")
    total_coupon_discount = Decimal("0.00")
    total_paid_amount = Decimal("0.00")
    refunded_amount = Decimal("0.00")

    for item in order_items:
        item.line_total = item.get_total_price()
        item.paid_amount = item.get_paid_amount()
        subtotal += item.line_total
        total_coupon_discount += item.orderItem_coupon_discount
        if item.item_status in ["cancelled", "returned"]:
            refunded_amount += item.paid_amount
        else:
            total_paid_amount += item.paid_amount

    order.subtotal_before_coupon = subtotal
    order.total_coupon_discount_display = total_coupon_discount
    order.total_paid_amount_display = subtotal - total_coupon_discount
    order.refunded_amount_display = refunded_amount
    order.active_paid_amount_display = total_paid_amount
    return order, order_items


def calculate_order_status(order):
    prefetched_items = getattr(order, "_prefetched_objects_cache", {}).get(
        "ordered_items"
    )
    if prefetched_items is not None:
        items = list(prefetched_items)
    else:
        items = list(order.ordered_items.all())

    item_statuses = [item.item_status for item in items]

    if item_statuses and all(status == "cancelled" for status in item_statuses):
        return "cancelled"
    if (
        item_statuses
        and all(status in ["delivered", "returned"] for status in item_statuses)
        and not any(item.return_request for item in items)
    ):
        return "completed"
    return "incomplete"


def refresh_order_status(order):
    order.status = calculate_order_status(order)
    order.save(update_fields=["status", "updated_at"])


def refund_returned_order_item(order_item):
    refund_amount = order_item.get_paid_amount()
    if refund_amount <= 0:
        return Decimal("0.00")

    wallet, _created = Wallet.objects.select_for_update().get_or_create(
        user=order_item.order.user
    )
    wallet.balance += refund_amount
    wallet.save(update_fields=["balance"])

    WalletTransaction.objects.create(
        wallet=wallet,
        amount=refund_amount,
        transaction_type="credit",
        description=f"Refund for returned item in order #{order_item.order.id}",
        balance_after=wallet.balance,
        reference_type="order_item",
        reference_id=str(order_item.id),
    )
    return refund_amount


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def show_order_details(request, id):
    order, order_items = get_order_with_pricing_details(id)

    context = {
        "order": order,
        "order_items": order_items,
    }
    return render(request, "order_Details.html", context)


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def download_order_details_pdf(request, id):
    order, order_items = get_order_with_pricing_details(id)
    template = get_template("order_details_pdf.html")
    html = template.render(
        {
            "order": order,
            "order_items": order_items,
        }
    )

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)

    if pdf.err:
        logger.error("Admin order PDF generation failed for order %s", id)
        return HttpResponse("Error generating order PDF", status=400)

    response = HttpResponse(result.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = (
        f"attachment; filename='order_{order.id}_details.pdf'"
    )
    return response


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def return_request_list(request):
    return_items = list(
        OrderItem.objects.filter(return_request=True)
        .select_related(
            "order__user",
            "product_variant__product__brand",
            "product_variant__product__category",
            "product_variant__color",
        )
        .order_by("-date_added")
    )

    for item in return_items:
        item.line_total = item.get_total_price()
        item.refund_amount = item.get_paid_amount()

    context = {
        "return_items": return_items,
    }
    return render(request, "return_requests.html", context)


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def manage_return_request(request):
    item_id = request.POST.get("item_id")
    action = request.POST.get("action")
    admin_message = request.POST.get("admin_message", "")

    if action not in ["approve", "reject"]:
        messages.error(request, "Invalid return request action.")
        return redirect("Admin:return_requests")

    with transaction.atomic():
        order_item = get_object_or_404(
            OrderItem.objects.select_for_update(),
            id=item_id,
            return_request=True,
            order__isnull=False,
        )
        order_item.order = (
            Order.objects.select_for_update()
            .select_related("user")
            .get(id=order_item.order_id)
        )

        if order_item.item_status != "delivered":
            order_item.return_request = False
            order_item.save(update_fields=["return_request"])
            messages.error(request, "Only delivered items can be returned.")
            return redirect("Admin:return_requests")

        if action == "approve":
            order_item.item_status = "returned"
            order_item.return_request = False
            order_item.action_status = "return"
            # clear any previous rejection info when approving
            order_item.return_rejected = False
            order_item.return_reject_message = ""
            order_item.save(
                update_fields=["item_status", "return_request", "action_status"]
            )
            refund_amount = refund_returned_order_item(order_item)
            refresh_order_status(order_item.order)
            messages.success(
                request,
                f"Return approved. ₹{refund_amount:.2f} refunded to the customer's wallet.",
            )
        else:
            # mark rejected and save admin message so customer and admins can see why
            order_item.return_request = False
            order_item.return_rejected = True
            if admin_message:
                order_item.return_reject_message = admin_message[:2000]
            order_item.save(
                update_fields=[
                    "return_request",
                    "return_rejected",
                    "return_reject_message",
                ]
            )
            messages.success(request, "Return request rejected.")

    return redirect("Admin:return_requests")


@login_required
@user_passes_test(lambda u: u.is_superuser)
def update_order_item_status(request):
    if request.method == "POST":
        item_id = request.POST.get("item_id")
        new_status = request.POST.get("new_status")

        try:
            with transaction.atomic():
                order_item = OrderItem.objects.select_for_update().get(id=item_id)

                if order_item.update_status(new_status):
                    if order_item.item_status == "delivered":
                        order_item.payment_status_item = "paid"
                        order_item.save(update_fields=["payment_status_item"])
                    elif order_item.item_status == "returned":
                        order_item.return_request = False
                        order_item.action_status = "return"
                        order_item.save(
                            update_fields=["return_request", "action_status"]
                        )
                        refund_returned_order_item(order_item)

                    order = order_item.order
                    refresh_order_status(order)

                    return JsonResponse({"success": True})
                else:
                    return JsonResponse(
                        {"success": False, "error": "Invalid status transition."}
                    )

        except OrderItem.DoesNotExist:
            return JsonResponse({"success": False, "error": "Order item not found."})

    return JsonResponse({"success": False, "error": "Invalid request method."})


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_coupon(request):
    form_data = {
        "code": "",
        "discount": "",
        "valid_from": "",
        "valid_to": "",
        "active": "True",
        "usage_limit": "",
        "min_purchase_amount": "",
        "description": "",
    }

    if request.method == "POST":
        form_data.update(
            {
                "code": request.POST.get("code", "") or "",
                "discount": request.POST.get("discount", "") or "",
                "valid_from": request.POST.get("valid_from", "") or "",
                "valid_to": request.POST.get("valid_to", "") or "",
                "active": request.POST.get("active", "True") or "True",
                "usage_limit": request.POST.get("usage_limit", "") or "",
                "min_purchase_amount": request.POST.get("min_purchase_amount", "")
                or "",
                "description": request.POST.get("description", "") or "",
            }
        )

        has_error = False

        code = form_data["code"].strip()
        discount = form_data["discount"].strip()
        valid_from = form_data["valid_from"].strip()
        valid_to = form_data["valid_to"].strip()
        active = form_data["active"] == "True"
        usage_limit = form_data["usage_limit"].strip()
        min_purchase_amount = form_data["min_purchase_amount"].strip()
        description = form_data["description"].strip()

        if not code:
            messages.error(request, "Coupon code is required.")
            has_error = True
        elif len(code) > 50:
            messages.error(request, "Coupon code cannot exceed 50 characters.")
            has_error = True
        elif Coupon.objects.filter(code__iexact=code).exists():
            messages.error(request, f"A coupon with code '{code}' already exists.")
            has_error = True

        if not discount:
            messages.error(request, "Discount percentage is required.")
            has_error = True
        else:
            try:
                discount_value = Decimal(discount)
            except (InvalidOperation, ValueError):
                messages.error(request, "Discount must be a valid number.")
                has_error = True
                discount_value = None
            else:
                if discount_value < 0:
                    messages.error(request, "Discount cannot be negative.")
                    has_error = True
                elif discount_value > 70:
                    messages.error(request, "Discount cannot exceed 70%.")
                    has_error = True

        valid_from_dt = None
        valid_to_dt = None
        now = django_timezone.now()

        if not valid_from:
            messages.error(request, "Valid From date is required.")
            has_error = True
        else:
            try:
                valid_from_dt = datetime.fromisoformat(valid_from)
                if django_timezone.is_naive(valid_from_dt):
                    valid_from_dt = django_timezone.make_aware(valid_from_dt)
            except ValueError:
                messages.error(request, "Valid From is not a valid date/time.")
                has_error = True
            else:
                if valid_from_dt < now:
                    messages.error(request, "Valid From cannot be in the past.")
                    has_error = True

        if not valid_to:
            messages.error(request, "Valid To date is required.")
            has_error = True
        else:
            try:
                valid_to_dt = datetime.fromisoformat(valid_to)
                if django_timezone.is_naive(valid_to_dt):
                    valid_to_dt = django_timezone.make_aware(valid_to_dt)
            except ValueError:
                messages.error(request, "Valid To is not a valid date/time.")
                has_error = True
            else:
                if valid_to_dt < now:
                    messages.error(request, "Valid To cannot be in the past.")
                    has_error = True

        if valid_from_dt and valid_to_dt and valid_to_dt <= valid_from_dt:
            messages.error(request, "Valid To must be later than Valid From.")
            has_error = True

        usage_limit_value = None
        if not usage_limit:
            messages.error(request, "Usage limit is required.")
            has_error = True
        else:
            try:
                usage_limit_value = int(usage_limit)
            except ValueError:
                messages.error(request, "Usage limit must be a whole number.")
                has_error = True
            else:
                if usage_limit_value <= 0:
                    messages.error(request, "Usage limit must be at least 1.")
                    has_error = True

        min_purchase_value = None
        if min_purchase_amount:
            try:
                min_purchase_value = Decimal(min_purchase_amount)
            except (InvalidOperation, ValueError):
                messages.error(
                    request, "Minimum purchase amount must be a valid number."
                )
                has_error = True
            else:
                if min_purchase_value < 0:
                    messages.error(
                        request, "Minimum purchase amount cannot be negative."
                    )
                    has_error = True

        if not has_error:
            try:
                coupon = Coupon(
                    code=code,
                    discount=discount_value,
                    valid_from=valid_from_dt,
                    valid_to=valid_to_dt,
                    active=active,
                    description=description,
                )

                coupon.usage_limit = usage_limit_value
                if min_purchase_value is not None:
                    coupon.min_purchase_amount = min_purchase_value

                coupon.full_clean()
                coupon.save()

                messages.success(request, f'Coupon "{code}" has been successfully added.')
                return redirect('Admin:coupon_list')

            except ValidationError as e:
                error_messages = []
                if hasattr(e, 'message_dict'):
                    for field, errors in e.message_dict.items():
                        error_messages.extend(errors)
                else:
                    error_messages = e.messages
                for message in error_messages:
                    messages.error(request, message)

            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")

    return render(request, "addCoupon.html", {"form_data": form_data})


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def coupon_exists(request):
    code = request.GET.get("code", "").strip()
    exists = Coupon.objects.filter(code__iexact=code).exists()
    return JsonResponse({"exists": exists})


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def show_coupon_list(request):
    coupons = Coupon.objects.all()
    return render(request, "couponList.html", {"coupons": coupons})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def get_coupon_details(request):
    coupon_id = request.GET.get("id")
    try:
        coupon = Coupon.objects.get(id=coupon_id)
        data = {
            "id": coupon.id,
            "code": coupon.code,
            "discount": coupon.discount,
            "valid_from": coupon.valid_from.strftime("%Y-%m-%dT%H:%M"),
            "valid_to": coupon.valid_to.strftime("%Y-%m-%dT%H:%M"),
            "active": coupon.active,
            "usage_limit": coupon.usage_limit,
            "min_purchase_amount": coupon.min_purchase_amount,
            "description": coupon.description,
        }
        return JsonResponse(data)
    except Coupon.DoesNotExist:
        return JsonResponse({"error": "Coupon not found"}, status=404)


@csrf_exempt
@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_coupon(request):
    if request.method == "POST":
        coupon_id = request.POST.get("id")
        try:
            coupon = Coupon.objects.get(id=coupon_id)

            code = (request.POST.get("code") or "").strip()
            discount = (request.POST.get("discount") or "").strip()
            valid_from = (request.POST.get("valid_from") or "").strip()
            valid_to = (request.POST.get("valid_to") or "").strip()
            usage_limit = (request.POST.get("usage_limit") or "").strip()
            min_purchase_amount = (
                request.POST.get("min_purchase_amount") or ""
            ).strip()
            description = (request.POST.get("description") or "").strip()

            errors = []

            if not code:
                errors.append("Coupon code is required.")
            elif len(code) > 50:
                errors.append("Coupon code cannot exceed 50 characters.")
            elif (
                Coupon.objects.filter(code__iexact=code).exclude(id=coupon.id).exists()
            ):
                errors.append(f"A coupon with code '{code}' already exists.")

            discount_value = None
            if not discount:
                errors.append("Discount percentage is required.")
            else:
                try:
                    discount_value = Decimal(discount)
                except (InvalidOperation, ValueError):
                    errors.append("Discount must be a valid number.")
                else:
                    if discount_value <= 0:
                        errors.append("Discount must be greater than 0.")
                    elif discount_value > 70:
                        errors.append("Discount cannot exceed 70%.")

            valid_from_dt = None
            valid_to_dt = None
            now = django_timezone.now()

            if not valid_from:
                errors.append("Valid From date is required.")
            else:
                try:
                    valid_from_dt = datetime.fromisoformat(valid_from)
                    if django_timezone.is_naive(valid_from_dt):
                        valid_from_dt = django_timezone.make_aware(valid_from_dt)
                except ValueError:
                    errors.append("Valid From is not a valid date/time.")
                else:
                    if valid_from_dt < now:
                        errors.append("Valid From cannot be in the past.")

            if not valid_to:
                errors.append("Valid To date is required.")
            else:
                try:
                    valid_to_dt = datetime.fromisoformat(valid_to)
                    if django_timezone.is_naive(valid_to_dt):
                        valid_to_dt = django_timezone.make_aware(valid_to_dt)
                except ValueError:
                    errors.append("Valid To is not a valid date/time.")
                else:
                    if valid_to_dt < now:
                        errors.append("Valid To cannot be in the past.")

            if valid_from_dt and valid_to_dt and valid_to_dt <= valid_from_dt:
                errors.append("Valid To must be later than Valid From.")

            usage_limit_value = None
            if not usage_limit:
                errors.append("Usage limit is required.")
            else:
                try:
                    usage_limit_value = int(usage_limit)
                except ValueError:
                    errors.append("Usage limit must be a whole number.")
                else:
                    if usage_limit_value <= 0:
                        errors.append("Usage limit must be at least 1.")

            min_purchase_value = None
            if min_purchase_amount:
                try:
                    min_purchase_value = Decimal(min_purchase_amount)
                except (InvalidOperation, ValueError):
                    errors.append("Minimum purchase amount must be a valid number.")
                else:
                    if min_purchase_value < 0:
                        errors.append("Minimum purchase amount cannot be negative.")

            if errors:
                return JsonResponse(
                    {"success": False, "error": " ".join(errors)}, status=400
                )

            coupon.code = code
            coupon.discount = discount_value
            coupon.valid_from = valid_from_dt
            coupon.valid_to = valid_to_dt
            coupon.active = request.POST.get("active") == "true"
            coupon.usage_limit = usage_limit_value
            coupon.min_purchase_amount = min_purchase_value
            coupon.description = description
            coupon.full_clean()
            coupon.save()
            return JsonResponse({"success": True})
        except Coupon.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Coupon not found."}, status=404
            )
        except ValidationError as e:
            if hasattr(e, "message_dict"):
                errors = [
                    message
                    for messages_list in e.message_dict.values()
                    for message in messages_list
                ]
            else:
                errors = e.messages
            return JsonResponse(
                {"success": False, "error": " ".join(errors)}, status=400
            )
    return JsonResponse(
        {"success": False, "error": "Invalid request method."}, status=400
    )


@csrf_exempt
@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_coupon(request):
    if request.method == "POST":
        coupon_id = request.POST.get("id")
        try:
            coupon = Coupon.objects.get(id=coupon_id)
            coupon.delete()
            return JsonResponse({"success": True})
        except Coupon.DoesNotExist:
            return JsonResponse({"success": False})


@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def control_coupon_status(request):
    coupon_id = request.POST.get("id")
    is_active = request.POST.get("active") == "true"

    try:
        coupon = Coupon.objects.get(id=coupon_id)
        coupon.active = is_active
        coupon.save()
        return JsonResponse({"success": True})
    except Coupon.DoesNotExist:
        return JsonResponse({"success": False}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@never_cache
@login_required
@login_required
@user_passes_test(lambda u: u.is_superuser)
def offer_list(request):
    offers = Offer.objects.all().order_by("-valid_from")
    context = {
        "offers": offers,
    }
    return render(request, "Offer.html", context)


@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_offer(request):
    try:
        name = request.POST.get("name")
        discount = request.POST.get("discount")
        valid_from = request.POST.get("valid_from")
        valid_to = request.POST.get("valid_to")
        description = request.POST.get("description")
        is_active = request.POST.get("is_active") == "on"

        if not name or not discount or not valid_from or not valid_to:
            return JsonResponse(
                {"success": False, "message": "All fields are required."}, status=400
            )

        Offer.objects.create(
            name=name,
            discount=discount,
            valid_from=valid_from,
            valid_to=valid_to,
            description=description,
            is_active=is_active,
        )
        return JsonResponse({"success": True, "message": "Offer added successfully!"})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=400)


@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_offer(request, offer_id):
    try:
        offer = get_object_or_404(Offer, id=offer_id)
        offer.name = request.POST.get("name")
        offer.discount = request.POST.get("discount")
        offer.valid_from = request.POST.get("valid_from")
        offer.valid_to = request.POST.get("valid_to")
        offer.description = request.POST.get("description")
        offer.is_active = request.POST.get("is_active") == "on"
        offer.save()
        return JsonResponse({"success": True, "message": "Offer updated successfully!"})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=400)


def control_offer_status(request, offer_id):
    if request.method == "POST":
        offer = get_object_or_404(Offer, id=offer_id)
        offer.is_active = not offer.is_active
        offer.save()
        return JsonResponse({"success": True, "new_status": offer.is_active})
    return JsonResponse({"success": False}, status=400)


@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_offer(request, offer_id):
    try:
        offer = get_object_or_404(Offer, id=offer_id)
        offer.delete()
        return JsonResponse({"success": True, "message": "Offer deleted successfully!"})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=400)


@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def update_product_offer(request):
    product_id = request.POST.get("product_id")
    offer_id = request.POST.get("offer_id")

    product = get_object_or_404(Product, id=product_id)

    if offer_id:
        offer = get_object_or_404(Offer, id=offer_id)
        product.offer = offer
    else:
        product.offer = None

    product.save()

    return JsonResponse(
        {
            "success": True,
            "message": f"Offer updated successfully for product: {product.name}",
        }
    )


# @require_POST
# @login_required
# @user_passes_test(lambda u: u.is_superuser)
# def update_category_offer(request):
#     category_id = request.POST.get("category_id")
#     offer_id = request.POST.get("offer_id")
#     action = request.POST.get("action")

#     try:
#         category = get_object_or_404(Category, id=category_id)

#         if action == "update":
#             offer = get_object_or_404(Offer, id=offer_id)
#             category.offer = offer
#             category.save()
#             message = f"Offer "{offer.name}" has been successfully applied to category "{category.name}"."
#         elif action == "remove":
#             old_offer_name = category.offer.name if category.offer else "No offer"
#             category.offer = None
#             category.save()
#             message = f"Offer has been successfully removed from category "{category.name}". Previous offer was "{old_offer_name}"."
#         else:
#             return JsonResponse({
#                 "success": False,
#                 "message": "Invalid action specified."
#             }, status=400)


#         return JsonResponse({
#             "success": True,
#             "message": message
#         })
#     except Exception as e:
#         return JsonResponse({
#             "success": False,
#             "message": f"An error occurred: {str(e)}"
#         }, status=400)
@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def update_category_offer(request):
    category_id = request.POST.get("category_id")
    offer_id = request.POST.get("offer_id")

    if not category_id:
        return JsonResponse(
            {"success": False, "message": "Category ID is required."}, status=400
        )

    try:
        category = get_object_or_404(Category, id=category_id)

        if offer_id and offer_id.strip():  # Offer selected → Apply offer
            offer = get_object_or_404(Offer, id=offer_id)
            category.offer = offer
            message = f"Offer '{offer.name}' has been successfully applied to category '{category.name}'."
        else:  # No offer selected → Remove offer
            category.offer = None
            message = f"Offer has been removed from category '{category.name}'."

        category.save()

        return JsonResponse({"success": True, "message": message})

    except Offer.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Selected offer does not exist."}, status=404
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"An error occurred: {str(e)}"}, status=400
        )


@never_cache
@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def show_sales_details(request):
    return render(request, "sales_report.html")


def get_filtered_sales_data(request):
    report_type = request.GET.get("report_type", "all")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    now = timezone.now()
    if report_type == "daily":
        start_date = now.date()
        end_date = start_date + timedelta(days=1)
    elif report_type == "weekly":
        start_date = now.date() - timedelta(days=now.weekday())
        end_date = start_date + timedelta(weeks=1)
    elif report_type == "monthly":
        start_date = now.replace(day=1).date()
        end_date = (start_date + timedelta(days=32)).replace(day=1)
    elif report_type == "yearly":
        start_date = now.replace(day=1, month=1).date()
        end_date = start_date.replace(year=start_date.year + 1)
    elif report_type == "custom" and start_date and end_date:
        start_date = timezone.datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = timezone.datetime.strptime(end_date, "%Y-%m-%d").date() + timedelta(
            days=1
        )
    else:
        try:
            earliest_order = Order.objects.earliest("created_at")
            start_date = earliest_order.created_at.date()
        except Order.DoesNotExist:
            start_date = now.date()
        end_date = now.date() + timedelta(days=1)

    start_date = timezone.make_aware(
        timezone.datetime.combine(start_date, timezone.datetime.min.time())
    )
    end_date = timezone.make_aware(
        timezone.datetime.combine(end_date, timezone.datetime.min.time())
    )

    orders = Order.objects.filter(created_at__range=[start_date, end_date])

    sales = orders.annotate(
        total_items=Sum("ordered_items__quantity"),
        total_discount=Sum(
            F("ordered_items__quantity")
            * F("ordered_items__orderItem_coupon_discount"),
            output_field=DecimalField(),
        ),
        refunded_amount=Sum(
            Case(
                When(
                    ordered_items__item_status="cancelled",
                    payment_status="paid",
                    then=F("ordered_items__price") * F("ordered_items__quantity")
                    - F("ordered_items__orderItem_coupon_discount"),
                ),
                default=Value(0),
                output_field=DecimalField(),
            )
        ),
    ).values(
        "id",
        "created_at",
        "payment_method",
        "user__username",
        "total_price",
        "coupon",
        "discount_amount_coupon",
        "status",
        "total_items",
        "total_discount",
        "refunded_amount",
    )

    for sale in sales:
        sale["created_at"] = sale["created_at"].strftime("%Y-%m-%d %H:%M:%S")
        sale["total_price"] = float(sale["total_price"])
        sale["discount_amount_coupon"] = float(sale["discount_amount_coupon"])
        sale["total_discount"] = float(sale["total_discount"] or 0)
        sale["refunded_amount"] = float(sale["refunded_amount"] or 0)

    summary = orders.aggregate(
        sales_count=Count("id"),
        order_amount=Coalesce(
            Sum("total_price", distinct=True), Value(0), output_field=DecimalField()
        ),
        total_discount=Coalesce(
            Sum("discount_amount_coupon"), Value(0), output_field=DecimalField()
        )
        + Coalesce(
            Sum("ordered_items__orderItem_coupon_discount"),
            Value(0),
            output_field=DecimalField(),
        ),
        total_refunded=Sum(
            Case(
                When(
                    ordered_items__item_status="cancelled",
                    payment_status="paid",
                    then=F("ordered_items__price") * F("ordered_items__quantity")
                    - F("ordered_items__orderItem_coupon_discount"),
                ),
                default=Value(0),
                output_field=DecimalField(),
            )
        ),
    )

    summary["order_amount"] = float(summary["order_amount"])
    summary["total_discount"] = float(summary["total_discount"])
    summary["total_refunded"] = float(summary["total_refunded"] or 0)

    status_data = orders.aggregate(
        delivered=Count(
            "ordered_items", filter=Q(ordered_items__item_status="delivered")
        ),
        cancelled=Count(
            "ordered_items", filter=Q(ordered_items__item_status="cancelled")
        ),
        returned=Count(
            "ordered_items", filter=Q(ordered_items__item_status="returned")
        ),
    )

    top_products = (
        OrderItem.objects.filter(order__created_at__range=[start_date, end_date])
        .values("product_variant__product__name")
        .annotate(total_quantity=Sum("quantity"))
        .order_by("-total_quantity")[:10]
    )

    top_categories = (
        OrderItem.objects.filter(order__created_at__range=[start_date, end_date])
        .values("product_variant__product__category__name")
        .annotate(total_quantity=Sum("quantity"))
        .order_by("-total_quantity")[:10]
    )

    top_brands = (
        OrderItem.objects.filter(order__created_at__range=[start_date, end_date])
        .values("product_variant__product__brand__name")
        .annotate(total_quantity=Sum("quantity"))
        .order_by("-total_quantity")[:10]
    )

    data = {
        "sales": list(sales),
        "summary": summary,
        "status_data": status_data,
        "top_products": list(top_products),
        "top_categories": list(top_categories),
        "top_brands": list(top_brands),
    }

    return JsonResponse(data)
