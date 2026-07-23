from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.products, name='products'),
    path('collection/', views.collection, name='collection'),
    path('lab/', views.lab, name='lab'),
    path('quality/', views.quality, name='quality'),
    path('contact/', views.contact, name='contact'),

    path('store/', views.store, name='store'),
    path('users/', views.index, name='users'),

    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/', views.cart_add, name='cart_add'),
    path('cart/update/', views.cart_update_qty, name='cart_update_qty'),
    path('cart/remove/', views.cart_remove, name='cart_remove'),
    path('cart/clear/', views.cart_clear, name='cart_clear'),
    path('cart/promo/', views.cart_apply_promo, name='cart_apply_promo'),

    path('checkout/', views.checkout_page, name='checkout'),
    path('checkout/process/', views.process_checkout, name='process_checkout'),
]