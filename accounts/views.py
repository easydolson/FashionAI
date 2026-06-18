from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegisterForm
from chat.models import ChatSession
from wishlist.models import WishlistItem


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешна!')
            return redirect('profile_page')
        else:
            messages.error(request, 'Ошибка регистрации. Проверьте введённые данные.')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def profile_page(request):
    # Получаем последнюю сессию (без привязки к пользователю, так как поля user нет)
    last_session = ChatSession.objects.last()
    wishlist = WishlistItem.objects.filter(user=request.user).select_related('product', 'look')

    context = {
        'user': request.user,
        'figure': last_session.figure_type if last_session else None,
        'color': last_session.color_type if last_session else None,
        'kibbe': last_session.kibbe_type if last_session else None,
        'wishlist': wishlist,
    }
    return render(request, 'accounts/profile.html', context)


def logout_view(request):
    logout(request)
    messages.info(request, 'Вы вышли из системы.')
    return redirect('login')