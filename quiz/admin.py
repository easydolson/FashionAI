from django.contrib import admin
from .models import QuizCategory, Question, AnswerOption, Product, Look, LookPhoto

admin.site.register(QuizCategory)
admin.site.register(Question)
admin.site.register(AnswerOption)

admin.site.register(Product)
admin.site.register(Look)
admin.site.register(LookPhoto)
