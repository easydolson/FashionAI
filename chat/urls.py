from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_page, name='chat_page'),
    path('send/', views.chat_send, name='chat_send'),
    path('clear/', views.chat_clear, name='chat_clear'),
]