from django.contrib import admin
from .models import ContactMessage, LabReview, Ball, Boot, Cart, CartItem


@admin.register(Ball)
class BallAdmin(admin.ModelAdmin):
    list_display = ("index", "name", "category", "price", "is_active")
    list_filter = ("category", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Boot)
class BootAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "status", "price", "is_active")
    list_filter = ("status", "is_active")
    prepopulated_fields = {"slug": ("name",)}


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "session_key", "total_qty", "subtotal", "updated_at")
    inlines = [CartItemInline]


admin.site.register(ContactMessage)
admin.site.register(LabReview)