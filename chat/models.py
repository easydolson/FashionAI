from django.db import models

class ChatSession(models.Model):
    session_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Добавь эти поля
    figure_type = models.CharField(max_length=50, blank=True, null=True)
    color_type = models.CharField(max_length=50, blank=True, null=True)
    kibbe_type = models.CharField(max_length=50, blank=True, null=True)

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10)  # 'user' или 'assistant'
    content = models.TextField()
    products_data = models.JSONField(null=True, blank=True)  # для хранения рекомендованных товаров
    created_at = models.DateTimeField(auto_now_add=True)
    message_type = models.CharField(max_length=20, default='text')  # 'text', 'look', 'products'
