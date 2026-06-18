from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from quiz.models import Product, Look
from .models import WishlistItem


@login_required
def wishlist_page(request):
    """Страница избранного (отображает и товары, и образы)."""
    items = WishlistItem.objects.filter(user=request.user).select_related('product', 'look')
    context = {
        'wishlist_items': items,
        'page_title': 'Мои избранные товары и образы'
    }
    return render(request, 'wishlist/wishlist.html', context)


@login_required
@require_POST
def toggle_wishlist(request):
    """AJAX: добавить/удалить товар."""
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
@require_POST
def toggle_look_wishlist(request):
    """AJAX: добавить/удалить образ."""
    look_id = request.POST.get('look_id')
    if not look_id:
        return HttpResponseBadRequest('look_id required')

    look = get_object_or_404(Look, pk=look_id)
    wish_item = WishlistItem.objects.filter(user=request.user, look=look)

    if wish_item.exists():
        wish_item.delete()
        is_in_wishlist = False
    else:
        WishlistItem.objects.create(user=request.user, look=look)
        is_in_wishlist = True

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'is_in_wishlist': is_in_wishlist, 'look_id': look_id})

    return redirect(request.META.get('HTTP_REFERER', 'wishlist_page'))


@login_required
def remove_from_wishlist(request, item_id):
    """Удаление элемента из избранного (без AJAX)."""
    item = get_object_or_404(WishlistItem, pk=item_id, user=request.user)
    item.delete()
    return redirect('wishlist_page')

@login_required
def get_wishlist_status(request):
    """Возвращает список SKU избранных товаров пользователя."""
    skus = WishlistItem.objects.filter(
        user=request.user,
        product__isnull=False
    ).values_list('product__sku', flat=True)
    return JsonResponse({'wishlist_skus': list(skus)})