# wishlist/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from quiz.models import Product
from .models import WishlistItem


@login_required
def wishlist_page(request):
    """Страница со списком избранных товаров пользователя."""
    items = WishlistItem.objects.filter(user=request.user).select_related('product')
    context = {
        'wishlist_items': items,
        'page_title': 'Мои избранные товары'
    }
    return render(request, 'wishlist/wishlist.html', context)


@login_required
@require_POST
def toggle_wishlist(request):
    """
    AJAX-обработчик добавления/удаления товара из избранного.
    Принимает product_id.
    """
    product_id = request.POST.get('product_id')
    if not product_id:
        return HttpResponseBadRequest('product_id required')

    product = get_object_or_404(Product, pk=product_id)
    wish_item = WishlistItem.objects.filter(user=request.user, product=product)

    if wish_item.exists():
        wish_item.delete()
        is_in_wishlist = False
    else:
        WishlistItem.objects.create(user=request.user, product=product)
        is_in_wishlist = True

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'is_in_wishlist': is_in_wishlist, 'product_id': product_id})

    return redirect(request.META.get('HTTP_REFERER', 'wishlist_page'))


@login_required
def remove_from_wishlist(request, product_id):
    """Удаление товара из избранного (без AJAX)."""
    product = get_object_or_404(Product, pk=product_id)
    WishlistItem.objects.filter(user=request.user, product=product).delete()
    return redirect('wishlist_page')