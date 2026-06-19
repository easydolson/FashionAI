from django.urls import path
from . import views

urlpatterns = [
    path('', views.start_quiz, name='start_quiz'),  # ← корень quiz
    path('question/<int:order>/', views.quiz_question, name='quiz_question'),
    path('result/', views.quiz_result, name='quiz_result'),
    path('reset/', views.reset_quiz, name='reset_quiz'),
]