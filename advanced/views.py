from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
import json
from .models import ContactMessage, LabReview, Ball, Boot, Cart, CartItem, Order, OrderItem
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction, IntegrityError
from decimal import Decimal, InvalidOperation
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def home(request):
    return render(request, "advanced/home.html")


def lab(request):
    return render(request, "advanced/lab.html")


def quality(request):
    return render(request, "advanced/quality.html")


def contact(request):
    return render(request, "advanced/contact.html")




def index(request):
    contacts = ContactMessage.objects.all()
    reviews = LabReview.objects.all()

    return render(request, "users.html", {
        "contacts": contacts,
        "reviews": reviews
    })


@require_POST
def store(request):
    # Parse the JSON payload from the request body
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    form_type = data.get("form_type")

    if form_type == "contact":
        name = data.get("name")
        email = data.get("email")
        dept = data.get("dept")
        message = data.get("message")

        if not all([name, email, dept, message]):
            return JsonResponse({"error": "All fields are required."}, status=400)

        ContactMessage.objects.create(
            name=name,
            email=email,
            dept=dept,
            message=message
        )
        return JsonResponse({"success": True})

    elif form_type == "review":
        reviewer_name = data.get("reviewer_name")
        rank = data.get("rank")
        revCat = data.get("revCat")
        score = data.get("score")
        body = data.get("body")

        if not all([reviewer_name, rank, revCat, score, body]):
            return JsonResponse({"error": "All fields are required."}, status=400)

        try:
            score = int(score)
        except ValueError:
            return JsonResponse({"error": "Score must be an integer."}, status=400)

        if score < 1 or score > 5:
            return JsonResponse({"error": "Score must be between 1 and 5."}, status=400)

        LabReview.objects.create(
            reviewer_name=reviewer_name,
            rank=rank,
            revCat=revCat,
            score=score,
            body=body
        )
        return JsonResponse({"success": True})

    return JsonResponse({"error": "Invalid form type"}, status=400)





def products(request):
    balls = Ball.objects.filter(is_active=True)
    return render(request, "advanced/products.html", {"balls": balls})


def collection(request):
    boots = Boot.objects.filter(is_active=True)
    return render(request, "advanced/collection.html", {"boots": boots})


# Server-side promo table — never trust a discount value sent from the client.
PROMO_CODES = {
    "PEAK10": Decimal("0.10"),  # 10% off subtotal
}


def _get_or_create_cart(request):
    if not request.session.session_key:
        request.session.create()
    cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart


def _cart_payload(cart):
    return {
        "items": [
            {
                "id": item.id,
                "product_type": item.product_type,
                "product_id": item.product_id,
                "name": item.name,
                "tag": item.tag,
                "price": float(item.price),
                "image": item.image,
                "qty": item.qty,
                "line_total": float(item.line_total),
            }
            for item in cart.items.all()
        ],
        "subtotal": float(cart.subtotal),
        "total_qty": cart.total_qty,
    }


@require_GET
def cart_view(request):
    cart = _get_or_create_cart(request)
    return JsonResponse(_cart_payload(cart))


@require_POST
def cart_add(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    product_type = data.get("product_type")
    product_id = data.get("product_id")
    try:
        qty = int(data.get("qty", 1))
    except (TypeError, ValueError):
        return JsonResponse({"error": "qty must be an integer"}, status=400)

    if qty < 1:
        return JsonResponse({"error": "qty must be at least 1"}, status=400)
    if product_type not in ("ball", "boot") or not product_id:
        return JsonResponse({"error": "product_type and product_id are required"}, status=400)

    model = Ball if product_type == "ball" else Boot
    product = get_object_or_404(model, pk=product_id, is_active=True)

    cart = _get_or_create_cart(request)

    try:
        with transaction.atomic():
            item, created = CartItem.objects.select_for_update().get_or_create(
                cart=cart,
                product_type=product_type,
                product_id=product.id,
                defaults={
                    "name": product.name,
                    "tag": product.tag if product_type == "ball" else product.get_status_display(),
                    "price": product.price,
                    "image": product.image,
                    "qty": qty,
                },
            )
            if not created:
                item.qty += qty
                item.save()
    except IntegrityError:
        # Lost a race to a concurrent add — fetch and increment instead.
        item = CartItem.objects.get(cart=cart, product_type=product_type, product_id=product.id)
        item.qty += qty
        item.save()

    return JsonResponse(_cart_payload(cart))


@require_POST
def cart_update_qty(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    item_id = data.get("item_id")
    try:
        qty = int(data.get("qty", 1))
    except (TypeError, ValueError):
        return JsonResponse({"error": "qty must be an integer"}, status=400)

    cart = _get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)

    if qty <= 0:
        item.delete()
    else:
        item.qty = qty
        item.save()

    return JsonResponse(_cart_payload(cart))


@require_POST
def cart_remove(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    item_id = data.get("item_id")
    cart = _get_or_create_cart(request)
    CartItem.objects.filter(pk=item_id, cart=cart).delete()

    return JsonResponse(_cart_payload(cart))


@require_POST
def cart_clear(request):
    cart = _get_or_create_cart(request)
    cart.items.all().delete()
    return JsonResponse(_cart_payload(cart))


@require_POST
def cart_apply_promo(request):
    """
    Validates a promo code server-side and returns the discount amount
    calculated off the REAL cart subtotal. The frontend must never compute
    this itself — it only displays what this endpoint returns.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    code = (data.get("code") or "").strip().upper()
    cart = _get_or_create_cart(request)

    if not cart.items.exists():
        return JsonResponse({"valid": False, "error": "Your cart is empty."}, status=400)

    pct = PROMO_CODES.get(code)
    if pct is None:
        return JsonResponse({"valid": False, "error": "Invalid promo code."}, status=400)

    discount_amount = (cart.subtotal * pct).quantize(Decimal("0.01"))
    return JsonResponse({"valid": True, "code": code, "discount_amount": float(discount_amount)})


@require_GET
def checkout_page(request):
    cart = _get_or_create_cart(request)

    if not cart.items.exists():
        messages.info(request, "Your cart is empty — add something before checking out.")
        return redirect("products")

    return render(request, "advanced/checkout.html", {
        "cart_data": _cart_payload(cart),
    })
    

def _send_order_confirmation_email(order, order_items):
    """
    Renders the HTML confirmation template and sends it to the customer.
    Failure here is logged but never allowed to break checkout — the order
    is already committed to the database by the time this runs.
    """
    context = {
        "order": order,
        "order_reference": f"#PT-{order.id:05d}-{order.created_at.year}",
        "order_items": order_items,
    }
    html_body = render_to_string("advanced/emails/order_confirmation.html", context)
    text_body = strip_tags(html_body)

    email = EmailMultiAlternatives(
        subject=f"[Prototype] Peak Theory Order Confirmed — #PT-{order.id:05d}-{order.created_at.year}",
        body=text_body,
        to=[order.email],
    )
    email.attach_alternative(html_body, "text/html")

    try:
        email.send(fail_silently=False)
    except Exception:
        # Don't let an email/SMTP failure turn a successful order into a
        # failed checkout response for the customer.
        logger.exception("Order confirmation email failed to send for order %s", order.id)



@require_POST
def process_checkout(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    cart = _get_or_create_cart(request)

    if not cart.items.exists():
        return JsonResponse({"error": "Cannot proceed to checkout. Cart is empty."}, status=400)

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    address = (data.get("address") or "").strip()

    if not all([name, email, phone, address]):
        return JsonResponse({"error": "Name, email, phone, and address are required."}, status=400)

    # Re-validate the promo server-side rather than trusting a discount
    # figure from the client.
    promo_code = (data.get("promo_code") or "").strip().upper()
    pct = PROMO_CODES.get(promo_code, Decimal("0"))
    discount_amount = (cart.subtotal * pct).quantize(Decimal("0.01"))

    try:
        shipping_cost = Decimal(str(data.get("shipping_cost", "0")))
    except InvalidOperation:
        shipping_cost = Decimal("0")
    # Only allow known shipping tiers — don't trust an arbitrary client number.
    if shipping_cost not in (Decimal("0.00"), Decimal("12.00")):
        shipping_cost = Decimal("12.00")

    total_amount = (cart.subtotal + shipping_cost - discount_amount).quantize(Decimal("0.01"))
    if total_amount < 0:
        total_amount = Decimal("0.00")

    with transaction.atomic():
        order = Order.objects.create(
            name=name,
            email=email,
            phone=phone,
            address=address,
            subtotal=cart.subtotal,
            shipping_cost=shipping_cost,
            discount_amount=discount_amount,
            total_amount=total_amount,
        )
        order_items = []
        for item in cart.items.all():
            oi = OrderItem.objects.create(
                order=order,
                product_type=item.product_type,
                product_id=item.product_id,
                name=item.name,
                price=item.price,
                qty=item.qty,
            )
            order_items.append(oi)
        cart.items.all().delete()

    # Sent after the transaction commits, so a slow SMTP call never holds
    # the database transaction open, and email delivery failure can't
    # roll back an order the customer was already told succeeded.
    _send_order_confirmation_email(order, order_items)

    return JsonResponse({
        "success": True,
        "message": "Order placed successfully!",
        "order_reference": f"#PT-{order.id:05d}-{order.created_at.year}",
        "cart": _cart_payload(cart),
    })