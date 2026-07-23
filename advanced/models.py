from django.db import models
from django.utils.text import slugify

class ContactMessage(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    dept = models.CharField(max_length=255)
    message = models.TextField()

    def __str__(self):
        return self.name


class LabReview(models.Model):
    reviewer_name = models.CharField(max_length=255)
    rank = models.CharField(max_length=255)
    revCat = models.CharField(max_length=255)
    score = models.PositiveSmallIntegerField()
    body = models.TextField()

    def __str__(self):
        return self.reviewer_name
    
    


class Ball(models.Model):
    CATEGORY_CHOICES = [
        ("match", "Match"),
        ("training", "Training"),
        ("academy", "Academy"),
        ("street", "Street"),
    ]

    slug = models.SlugField(max_length=255, unique=True, blank=True)
    index = models.PositiveSmallIntegerField(help_text="Display order, e.g. 01, 02")
    name = models.CharField(max_length=255)
    tag = models.CharField(max_length=255, help_text="e.g. Match Ball, Pro Ball")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.URLField(max_length=1000)
    description = models.TextField(blank=True)

    layering = models.CharField(max_length=255, blank=True, help_text="e.g. 5-Layer Premium Shell")
    core = models.CharField(max_length=255, blank=True, help_text="e.g. Composite Bladder")
    aero_tech = models.CharField(max_length=255, blank=True, help_text="e.g. Micro-Texturing")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["index"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def index_display(self):
        return str(self.index).zfill(2)


class Boot(models.Model):
    STATUS_CHOICES = [
        ("flagship", "Flagship Build"),
        ("prototype", "Prototype"),
        ("academy", "Academy"),
        ("pro_match", "Pro Match"),
        ("heritage", "Heritage"),
        ("testing", "Testing Phase"),
        ("concept", "Concept Drop"),
        ("limited", "Limited Stock"),
        ("upcoming", "Upcoming"),
    ]

    slug = models.SlugField(max_length=255, unique=True, blank=True)
    order = models.PositiveSmallIntegerField(default=0, help_text="Carousel display order")
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.URLField(max_length=1000)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Cart(models.Model):
    session_key = models.CharField(max_length=255, db_index=True, help_text="Django session key, ties cart to a browser session")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart {self.pk} ({self.session_key})"

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items.all())

    @property
    def total_qty(self):
        return sum(item.qty for item in self.items.all())


class CartItem(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ("ball", "Ball"),
        ("boot", "Boot"),
    ]

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")

    # Snapshot fields — captured at add-time so the cart still displays
    # correctly even if the product's price/name changes later.
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPE_CHOICES)
    product_id = models.PositiveIntegerField(help_text="PK of the Ball or Boot")
    name = models.CharField(max_length=255)
    tag = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.URLField(max_length=1000, blank=True)

    qty = models.PositiveIntegerField(default=1)

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "product_type", "product_id")

    def __str__(self):
        return f"{self.qty} x {self.name}"

    @property
    def line_total(self):
        return self.price * self.qty
    
    
class Order(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=500)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} — {self.name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_type = models.CharField(max_length=10)
    product_id = models.PositiveIntegerField()
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    qty = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.qty} x {self.name} (Order #{self.order_id})"