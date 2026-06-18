from django.urls import path
from . import views

app_name = 'wishlist'

urlpatterns = [
    path('', views.wishlist_page, name='wishlist_page'),
    path('toggle/', views.toggle_wishlist, name='toggle_wishlist'),
    path('toggle-look/', views.toggle_look_wishlist, name='toggle_look_wishlist'),
    path('remove/<int:item_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('get-status/', views.get_wishlist_status, name='get_wishlist_status'),
]