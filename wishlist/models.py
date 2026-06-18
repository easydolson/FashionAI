from django.db import models
from django.contrib.auth.models import User
from quiz.models import Product, Look

class WishlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    look = models.ForeignKey(Look, on_delete=models.CASCADE, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product', 'look')  # чтобы не дублировать

    def __str__(self):
        if self.product:
            return f"{self.user.username} - {self.product.name}"
        if self.look:
            return f"{self.user.username} - Образ #{self.look.id}"
        return f"{self.user.username} - Избранное"