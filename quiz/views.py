# quiz/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from .models import Question, AnswerOption
from chat.models import ChatSession


from .models import Look


def start_quiz(request):
    """Начинает опрос: очищает сессию и перенаправляет на первый вопрос"""
    request.session['quiz_answers'] = {}
    first_question = Question.objects.filter(order=1).first()

    if not first_question:
        messages.error(request, 'Вопросы не найдены. Обратитесь к администратору.')
        return redirect('quiz_result')

    # return redirect('quiz_question', order=1)
    return render(request, 'quiz/start_quiz.html')


def quiz_question(request, order):
    """Отображает вопрос с указанным порядковым номером"""
    question = get_object_or_404(Question, order=order)
    options = question.options.all()
    answers = request.session.get('quiz_answers', {})
    total_questions = Question.objects.count()

    if request.method == 'POST':
        selected_value = request.POST.get('answer')

        if selected_value:
            answers[str(order)] = selected_value
            request.session['quiz_answers'] = answers

            next_order = order + 1
            if next_order <= total_questions:
                return redirect('quiz_question', order=next_order)
            else:
                return redirect('quiz_result')
        else:
            messages.warning(request, 'Пожалуйста, выберите вариант ответа.')

    progress = {
        'current': order,
        'total': total_questions,
        'percent': int((order - 1) / total_questions * 100) if total_questions > 0 else 0
    }

    context = {
        'question': question,
        'options': options,
        'progress': progress,
        'current_answer': answers.get(str(order), None),
    }

    return render(request, 'quiz/question.html', context)


def quiz_result(request):
    """Показывает результаты опроса и рекомендации"""
    answers = request.session.get('quiz_answers', {})

    if not answers:
        messages.info(request, 'Пройдите опрос, чтобы получить рекомендации.')
        return redirect('start_quiz')

    figure_type = get_figure_type(answers)
    color_type = get_color_type(answers)
    kibbe_type = get_kibbe_type(answers)

    # СОХРАНЯЕМ В СЕССИЮ
    request.session['figure_type'] = figure_type
    request.session['color_type'] = color_type
    request.session['kibbe_type'] = kibbe_type

    # recommendations = get_recommendations(figure_type, color_type, kibbe_type)

    # Ищем подходящие образы (проверяем "Все" как универсальное значение)
    suitable_looks = []
    for look in Look.objects.all():
        # Проверка фигуры
        figure_ok = (look.suitable_figure == 'Все' or
                     figure_type in look.suitable_figure.split(', '))

        # Проверка цвета
        color_ok = (look.suitable_color == 'Все' or
                    color_type in look.suitable_color.split(', '))

        # Проверка кибби
        kibbe_ok = (look.suitable_kibbe == 'Все' or
                    kibbe_type in look.suitable_kibbe.split(', '))

        if figure_ok and color_ok and kibbe_ok:
            suitable_looks.append(look)

    # Сохраняем образы в сессию
    quiz_products = []
    for look in suitable_looks[:5]:
        look_image = look.photos.first().photo_url if look.photos.exists() else None
        products_list = []
        for product in look.get_products():
            products_list.append({
                'name': product.name,
                'price': float(product.price),
                'image_filename': product.image,
                'url': product.url
            })
        quiz_products.append({
            'look_image': look_image,
            'products': products_list
        })

    request.session['quiz_products'] = quiz_products

    # Перенаправляем в чат вместо страницы с результатами
    request.session['quiz_products'] = quiz_products
    request.session['quiz_completed'] = True

    # ========== ВСТАВИТЬ СЮДА ==========
    from chat.models import ChatSession
    session_id = request.session.get('chat_session_id')
    if session_id:
        chat_session = ChatSession.objects.filter(session_id=session_id).first()
        if chat_session:
            chat_session.figure_type = figure_type
            chat_session.color_type = color_type
            chat_session.kibbe_type = kibbe_type
            chat_session.save()
    # ===================================

    return redirect('chat_page')
    # return render(request, 'quiz/result.html', context)


def reset_quiz(request):
    """Сбрасывает опрос и позволяет начать заново"""
    if 'quiz_answers' in request.session:
        del request.session['quiz_answers']
    messages.success(request, 'Опрос сброшен. Можете пройти его заново.')
    return redirect('start_quiz')


# ========== Функции определения типов ==========

def get_figure_type(answers):
    q1 = answers.get('1')
    q2 = answers.get('2')
    q3 = answers.get('3')

    if q1 == 'A' and q3 == 'A':
        return 'Перевёрнутый треугольник'
    if q1 == 'B' and q2 == 'A' and q3 == 'B':
        return 'Песочные часы'
    if q1 == 'C' and q3 == 'C':
        return 'Груша'
    if q1 == 'B' and q2 == 'C' and q3 == 'D':
        return 'Прямоугольник'
    if q3 == 'E':
        return 'Яблоко'

    # fallback
    if q3 == 'A':
        return 'Перевёрнутый треугольник'
    if q3 == 'B':
        return 'Песочные часы'
    if q3 == 'C':
        return 'Груша'
    if q3 == 'D':
        return 'Прямоугольник'
    return 'Прямоугольник'


def get_color_type(answers):
    """
    Определяет цветотип по ответам на вопросы order 4,5,6,7
    """
    q_skin = answers.get('4')  # тон кожи
    q_sun = answers.get('5')  # реакция на солнце
    q_eyes = answers.get('6')  # цвет глаз
    q_hair = answers.get('7')  # цвет волос

    # Голосование
    votes = {'Весна': 0, 'Лето': 0, 'Осень': 0, 'Зима': 0}

    mapping = {
        '4': {'A': 'Весна', 'B': 'Лето', 'C': 'Осень', 'D': 'Зима'},
        '5': {'A': 'Весна', 'B': 'Лето', 'C': 'Осень', 'D': 'Зима'},
        '6': {'A': 'Весна', 'B': 'Лето', 'C': 'Осень', 'D': 'Зима'},
        '7': {'A': 'Весна', 'B': 'Лето', 'C': 'Осень', 'D': 'Зима'},
    }

    for q_num, answer in answers.items():
        if q_num in mapping and answer in mapping[q_num]:
            votes[mapping[q_num][answer]] += 1

    # Находим победителя
    max_votes = max(votes.values())
    winners = [k for k, v in votes.items() if v == max_votes]

    if len(winners) == 1:
        return winners[0]

    # При ничьей используем дополнительные правила
    if q_eyes == 'B' or q_hair == 'B':
        return 'Лето'
    if q_eyes == 'A':
        return 'Весна'
    if q_eyes == 'C' or q_hair == 'C':
        return 'Осень'
    if q_hair == 'D':
        return 'Зима'

    return 'Лето'


def get_kibbe_type(answers):
    """
    Определяет типаж по Кибби (вопросы order 8,9,10,11)
    """
    q_bones = answers.get('8')  # костная структура
    q_body = answers.get('9')  # форма тела
    q_face = answers.get('10')  # черты лица
    q_height = answers.get('11')  # рост

    kibbe_answers = [q_bones, q_body, q_face]
    kibbe_answers = [a for a in kibbe_answers if a]

    if not kibbe_answers:
        return 'Классик'

    from collections import Counter
    counter = Counter(kibbe_answers)
    most_common = counter.most_common(1)[0][0]

    mapping = {'A': 'Драматик', 'B': 'Натурал', 'C': 'Классик', 'D': 'Романтик', 'E': 'Гамин'}
    result = mapping.get(most_common, 'Классик')

    # Корректировка по росту
    if q_height == 'A' and result == 'Гамин':
        result = 'Драматик'
    if q_height == 'C' and result == 'Драматик':
        result = 'Гамин'

    return result


def get_recommendations(figure_type, color_type, kibbe_type):
    recommendations_figure = {
        'Песочные часы': '✓ Подчёркивайте талию: приталенные платья, ремни, пояса.\n✓ V-образные и круглые вырезы.\n✗ Избегайте мешковатых вещей.',
        'Груша': '✓ Акцент на верх: светлые топы, декольте, подплечники.\n✓ Тёмный низ прямого кроя или юбка-карандаш.\n✗ Избегайте накладных карманов на бёдрах.',
        'Перевёрнутый треугольник': '✓ Балансируйте бёдрами: юбки-клёш, светлые брюки.\n✓ V-образные вырезы, тёмный верх.\n✗ Избегайте подплечников.',
        'Прямоугольник': '✓ Создавайте изгибы: пояса, драпировки, пышные юбки, баски.\n✗ Избегайте прямых бесформенных силуэтов.',
        'Яблоко': '✓ V-образные вырезы, завышенная талия, вертикальные линии, платья-трапеции.\n✗ Избегайте облегающих вещей в области талии.'
    }

    recommendations_color = {
        'Весна': '✓ Тёплые и свежие оттенки: персиковый, коралловый, золотистый, цвет молодой зелени.\n✓ Прозрачные, легкие ткани.\n✗ Избегайте чёрного и ярко-синего у лица.',
        'Лето': '✓ Пастельные, приглушённые тона: лаванда, мятный, пыльная роза, серо-голубой.\n✓ Холодные оттенки с дымкой.\n✗ Избегайте ярких оранжевых и золотистых.',
        'Осень': '✓ Землистые, насыщенные цвета: горчичный, терракотовый, оливковый, тёплый беж.\n✓ Фактурные ткани: замша, твид, шерсть.\n✗ Избегайте холодных и неоновых оттенков.',
        'Зима': '✓ Чистые, яркие, контрастные цвета: чёрный, белый, фуксия, изумруд, королевский синий.\n✓ Глянцевые и блестящие ткани.\n✗ Избегайте пастельных и блёклых оттенков.'
    }

    recommendations_kibbe = {
        'Драматик': '✓ Чёткие линии, минимализм, геометрические принты.\n✓ Крупные аксессуары, глубокие вырезы.\n✗ Избегайте рюшей, бантиков и мелких узоров.',
        'Натурал': '✓ Свободные силуэты, натуральные ткани (лён, хлопок).\n✓ Крупные детали, этно-стиль.\n✗ Избегайте строгих костюмов и синтетики.',
        'Классик': '✓ Симметрия, лаконичность, качественные базовые вещи.\n✓ Элегантные ткани: кашемир, шёлк, твид.\n✗ Избегайте излишеств и авангардных форм.',
        'Романтик': '✓ Мягкие ткани (шёлк, кружево, шифон), оборки, воланы.\n✓ Приталенные силуэты, мелкий цветочный принт.\n✗ Избегайте грубых тканей и угловатых форм.',
        'Гамин': '✓ Игривость, смелые сочетания, контрасты, нестандартные детали.\n✓ Короткие длины, яркие акценты.\n✗ Избегайте скучных и слишком серьёзных образов.'
    }

    return {
        'figure': recommendations_figure.get(figure_type, 'Рекомендации по фигуре временно отсутствуют.'),
        'color': recommendations_color.get(color_type, 'Рекомендации по цвету временно отсутствуют.'),
        'kibbe': recommendations_kibbe.get(kibbe_type, 'Рекомендации по стилю временно отсутствуют.')
    }
