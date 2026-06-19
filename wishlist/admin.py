from django.contrib import admin
from .models import WishlistItem

@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'look', 'added_at')
    list_filter = ('user', 'added_at')
    search_fields = ('user__username', 'product__name')