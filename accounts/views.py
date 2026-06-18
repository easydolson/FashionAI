from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from wishlist.models import WishlistItem
from quiz.models import Product
from chat.models import ChatSession
from .forms import RegisterForm



def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('profile_page')
        else:
            messages.error(request, 'Ошибка регистрации. Проверьте введённые данные.')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})


@login_required
def profile_page(request):
    # Получаем последнюю сессию чата пользователя (с параметрами внешности)
    last_session = ChatSession.objects.filter(user=request.user).last()

    # Получаем избранные товары
    wishlist = WishlistItem.objects.filter(user=request.user).select_related('product')

    context = {
        'user': request.user,
        'figure_type': last_session.figure_type if last_session else None,
        'color_type': last_session.color_type if last_session else None,
        'kibbe_type': last_session.kibbe_type if last_session else None,
        'wishlist': wishlist,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'Вы вышли из системы.')
    return redirect('login')


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешна!')
            return redirect('profile_page')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    # Используем стандартную форму Django
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'Вы вышли')
    return redirect('chat_page')

@login_required
def profile_page(request):
    last_session = ChatSession.objects.filter(user=request.user).last()
    wishlist = WishlistItem.objects.filter(user=request.user).select_related('product', 'look')
    return render(request, 'accounts/profile.html', {
        'user': request.user,
        'figure': last_session.figure_type if last_session else None,
        'color': last_session.color_type if last_session else None,
        'kibbe': last_session.kibbe_type if last_session else None,
        'wishlist': wishlist,
    })