# wishlist/models.py
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from quiz.models import Product  # модель товара


class WishlistItem(models.Model):
    """Модель избранного товара пользователя."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist_items',
        verbose_name='Пользователь'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlisted_by',
        verbose_name='Товар'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    class Meta:
        unique_together = ('user', 'product')  # один товар не может быть добавлен в избранное дважды
        verbose_name = 'Избранный товар'
        verbose_name_plural = 'Избранные товары'

    def __str__(self):
        return f"{self.user.username} – {self.product.name}"


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')  # чтобы не дублировать
