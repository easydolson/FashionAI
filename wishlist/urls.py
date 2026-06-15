# wishlist/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.wishlist_page, name='wishlist_page'),
    path('toggle/', views.toggle_wishlist, name='toggle_wishlist'),
    path('remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
]