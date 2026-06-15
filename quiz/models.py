from django.db import models

class QuizCategory(models.Model):
    """Категория опроса: figure, color, kibbe"""
    name = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=50)

    def __str__(self):
        return self.title

class Question(models.Model):
    category = models.ForeignKey(QuizCategory, on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['category', 'order']

    def __str__(self):
        return f"{self.category.name}: {self.text[:50]}"

class AnswerOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=200)
    value = models.CharField(max_length=10)  # буквенный код ответа: A, B, C, D, E
    # Доп. поле для оценки, если нужно (например, вес)
    score = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.question.text[:30]} -> {self.value}: {self.text}"

class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    category = models.CharField(max_length=100, blank=True)
    url = models.URLField(blank=True)
    image = models.URLField(blank=True, null=True)
    color = models.CharField(max_length=50, blank=True)
    silhouette = models.CharField(max_length=50, blank=True)
    suitable_figure = models.CharField(max_length=200, blank=True)
    suitable_color = models.CharField(max_length=200, blank=True)
    suitable_kibbe = models.CharField(max_length=200, blank=True)


class Look(models.Model):
    obraz_id = models.CharField(max_length=50, unique=True)
    skus = models.CharField(max_length=500)
    obraz_ids_all = models.CharField(max_length=500, blank=True)
    suitable_figure = models.CharField(max_length=200, blank=True)
    suitable_color = models.CharField(max_length=200, blank=True)
    suitable_kibbe = models.CharField(max_length=200, blank=True)
    name = models.CharField(max_length=200, blank=True)

    def get_products(self):
        """Возвращает список товаров, входящих в образ"""
        sku_list = [s.strip() for s in self.skus.split(',') if s.strip()]
        return Product.objects.filter(sku__in=sku_list)

class LookPhoto(models.Model):
    look = models.ForeignKey(Look, on_delete=models.CASCADE, related_name='photos')
    photo_url = models.URLField()
    order = models.PositiveSmallIntegerField(default=0)