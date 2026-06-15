from django.urls import path
from . import views

urlpatterns = [
    path('', views.start_quiz, name='start_quiz'),
    path('quiz/', views.start_quiz, name='quiz_start'),
    path('quiz/question/<int:order>/', views.quiz_question, name='quiz_question'),
    path('quiz/result/', views.quiz_result, name='quiz_result'),
    path('quiz/reset/', views.reset_quiz, name='quiz_reset'),
]