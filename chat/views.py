import json
import uuid
import numpy as np
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import ChatSession, ChatMessage
from core.services.search_service import SearchService
from core.services.gigachat_service import GigaChatService

search_service = SearchService()
giga_service = GigaChatService(search_service=search_service)


def chat_page(request):
    session_id = request.session.get('chat_session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        request.session['chat_session_id'] = session_id
        ChatSession.objects.create(session_id=session_id)

    # try:
    #     session = ChatSession.objects.get(session_id=session_id)
    #     messages = session.messages.all().order_by('created_at')
    # except ChatSession.DoesNotExist:
    #     messages = []

    # ========== СОЗДАЁМ session ДО ИСПОЛЬЗОВАНИЯ ==========
    session, _ = ChatSession.objects.get_or_create(session_id=session_id)
    messages = session.messages.all().order_by('created_at')
    # ======================================================

    print(f"DEBUG: figure_type in session: {request.session.get('figure_type')}")  # ← добавить
    print(f"DEBUG: quiz_products in session: {request.session.get('quiz_products')}")  # ← добавить

    user_data = {
        # 'figure': request.session.get('figure_type'),
        # 'color_type': request.session.get('color_type'),
        # 'kibbe_type': request.session.get('kibbe_type'),

        'figure': session.figure_type,
        'color_type': session.color_type,
        'kibbe_type': session.kibbe_type,
    }

    # ========== Проверка новых образов ==========
    quiz_products = request.session.pop('quiz_products', None)
    if quiz_products and not messages:
        # Сообщение с образами
        ChatMessage.objects.create(
            session=session,
            role='assistant',
            content='🎉 Отлично! Я подобрал для вас товары, идеально подходящие под ваши параметры:',
            products_data=quiz_products,
            message_type='look'
        )

        # Направляющее сообщение
        ChatMessage.objects.create(
            session=session,
            role='assistant',
            content='Вот образы, которые вам подходят. Какой понравился больше?\n\nМогу дополнить его аксессуарами или найти похожие модели.',
            products_data=None,
            message_type='text'
        )

        messages = session.messages.all().order_by('created_at')
    # ======================================================

    quiz_completed = request.session.pop('quiz_completed', False)
    # quiz_completed = request.GET.get('quiz_completed') == '1' or request.session.pop('quiz_completed', False)

    return render(request, 'chat/chat_page.html', {
        'messages': messages,
        'user_data': user_data,
        'quiz_products': quiz_products,
        'quiz_completed': quiz_completed
    })


@require_http_methods(["POST"])
def chat_clear(request):
    session_id = request.session.get('chat_session_id')
    if session_id:
        ChatSession.objects.filter(session_id=session_id).delete()
    request.session['chat_session_id'] = str(uuid.uuid4())
    return JsonResponse({'status': 'ok'})


@csrf_exempt
@require_http_methods(["POST"])
def chat_send(request):
    data = json.loads(request.body)
    user_message = data.get('message', '')
    if not user_message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    session_id = request.session.get('chat_session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        request.session['chat_session_id'] = session_id
        ChatSession.objects.create(session_id=session_id)

    session = ChatSession.objects.get(session_id=session_id)

    # Сохраняем сообщение пользователя
    ChatMessage.objects.create(session=session, role='user', content=user_message)

    # Нормализуем запрос
    normalized_message = user_message.lower().strip()
    more_variants_keywords = [
        'ещё', 'еще', 'другой', 'другие', 'другой вариант', 'другие варианты',
        'другое', 'другой образ', 'другой лук', 'ещё вариант', 'еще вариант',
        'ещё образ', 'еще образ', 'ещё лук', 'еще лук', 'другие вещи',
        'не то', 'покажи другое', 'покажи другие', 'дай другое',
        'варианты', 'другие варианты', 'следующий', 'следующие', 'другой товар',
        'не нравится', 'хочу другое', 'замени', 'поменяй'
    ]
    is_more_request = any(keyword in normalized_message for keyword in more_variants_keywords)

    # Если запрос на "ещё" и есть сохранённый контекст
    if is_more_request:
        last_type = request.session.get('last_response_type')
        last_params = request.session.get('last_response_params', {})
        offset = request.session.get('last_search_offset', 0)

        if last_type == 'products' and last_params:
            # Поиск товаров со сдвигом и диверсификацией
            query = last_params.get('query', '')
            category = last_params.get('category')
            new_offset = offset + 5

            # Получаем SKU уже показанных товаров
            exclude_skus = request.session.get('shown_skus', [])

            # Ищем больше кандидатов для диверсификации
            results = search_service.hybrid_search(
                query,
                top_k=new_offset + 15,
                exclude_skus=exclude_skus
            )

            if category:
                results = results[results['category'].str.contains(category, case=False, na=False)]
            results = results.drop_duplicates(subset=['name'], keep='first')

            if len(results) > new_offset:
                # Берём следующие 5 результатов
                results = results.iloc[new_offset:new_offset + 5]
                request.session['last_search_offset'] = new_offset
            else:
                # Если дошли до конца — начинаем с начала, но с диверсификацией
                # Применяем MMR для разнообразия
                results = search_service.diversify_results(results, query, search_service.model, lambda_param=0.7)
                results = results.head(5)
                request.session['last_search_offset'] = 0

            products = []
            for _, row in results.iterrows():
                price = row.get('price', 0)
                if hasattr(price, 'item'):
                    price = price.item()
                products.append({
                    'sku': str(row.get('sku', '')),
                    'name': str(row.get('name', '')),
                    'price': price,
                    'image_filename': str(row.get('image_filename', '')),
                    'url': str(row.get('url', '#')),
                    'category': str(row.get('category', ''))
                })

            return JsonResponse({
                'message': 'Вот другие варианты:' if new_offset > 5 else 'Вот ещё варианты:',
                'products': products,
                'type': 'products',
                'quiz_url': None
            })

        elif last_type == 'outfit' and last_params:
            # Генерируем новый образ — сдвигаем параметры или меняем стиль
            occasion = last_params.get('occasion', 'прогулка')
            style = last_params.get('style', 'кэжуал')
            season = last_params.get('season', 'лето')

            # Получаем исключённые SKU
            exclude_skus = request.session.get('shown_skus', [])

            # Слегка меняем стиль для разнообразия
            style_variants = {
                'кэжуал': ['романтичный', 'спортивный', 'минимализм'],
                'романтичный': ['кэжуал', 'богемный', 'классический'],
                'деловой': ['кэжуал', 'минимализм', 'классический'],
                'спортивный': ['кэжуал', 'минимализм', 'романтичный']
            }
            if style in style_variants:
                new_style = style_variants[style][abs(hash(str(last_params))) % len(style_variants[style])]
            else:
                new_style = 'кэжуал'

            new_params = {
                'occasion': occasion,
                'style': new_style,
                'season': season
            }

            new_result = giga_service._execute_compose_outfit(new_params, exclude_skus=exclude_skus)
            if new_result.success:
                products = list(new_result.data.get('outfit', {}).values())

                # Сохраняем новые SKU
                shown_skus = request.session.get('shown_skus', [])
                for product in products:
                    sku = product.get('sku')
                    if sku and sku not in shown_skus:
                        shown_skus.append(sku)
                request.session['shown_skus'] = shown_skus[-50:]

                # Сохраняем новые параметры
                request.session['last_response_params'] = new_params
                return JsonResponse({
                    'message': f'Вот другой вариант образа в стиле {new_style}:',
                    'products': products,
                    'type': 'outfit',
                    'quiz_url': None
                })

    # Обычная обработка через GigaChat
    history = [
                  {"role": msg.role, "content": msg.content, "message_type": msg.message_type,
                   "products_data": msg.products_data}
                  for msg in session.messages.all().order_by('created_at')[:10]
              ][::-1]

    user_profile = {
        'figure': session.figure_type,
        'color_type': session.color_type,
        'kibbe_type': session.kibbe_type,
    }

    result = giga_service.process_message(
        user_message=user_message,
        session=session,
        user_profile=user_profile,
        conversation_history=history
    )

    # Формируем ответ
    if result['type'] == 'products':
        answer_text = result.get('message', 'Вот что я нашёл:')
        products = result['data'].get('items', [])
        message_type = 'products'
        request.session['last_response_type'] = 'products'
        request.session['last_response_params'] = {
            'query': user_message,
            'category': result['data'].get('category')
        }
        request.session['last_search_offset'] = 0

        # ========== СОХРАНЯЕМ SKU ==========
        shown_skus = request.session.get('shown_skus', [])
        for product in products:
            sku = product.get('sku')
            if sku and sku not in shown_skus:
                shown_skus.append(sku)
        request.session['shown_skus'] = shown_skus[-50:]  # храним последние 50
        # ===================================

    elif result['type'] == 'outfit':
        answer_text = result.get('message', 'Вот ваш образ:')
        products = list(result['data'].get('outfit', {}).values())
        message_type = 'outfit'
        request.session['last_response_type'] = 'outfit'
        request.session['last_response_params'] = {
            'occasion': result['data'].get('occasion'),
            'style': result['data'].get('style'),
            'season': result['data'].get('season')
        }

        # ========== СОХРАНЯЕМ SKU ==========
        shown_skus = request.session.get('shown_skus', [])
        for product in products:
            sku = product.get('sku')
            if sku and sku not in shown_skus:
                shown_skus.append(sku)
        request.session['shown_skus'] = shown_skus[-50:]  # храним последние 50
        # ===================================

    elif result['type'] == 'quiz_suggestion':
        answer_text = result['data'].get('message', '')
        products = []
        message_type = 'quiz_suggestion'
    else:
        answer_text = result['data']
        products = []
        message_type = 'text'

    ChatMessage.objects.create(
        session=session,
        role='assistant',
        content=answer_text,
        products_data=products if products else None,
        message_type=message_type
    )

    return JsonResponse({
        'message': answer_text,
        'products': products,
        'type': message_type,
        'quiz_url': result['data'].get('quiz_url') if result['type'] == 'quiz_suggestion' else None
    })

# @csrf_exempt
# @require_http_methods(["POST"])
# def chat_send(request):
#     data = json.loads(request.body)
#     user_message = data.get('message', '')
#     if not user_message:
#         return JsonResponse({'error': 'Empty message'}, status=400)
#
#     session_id = request.session.get('chat_session_id')
#     if not session_id:
#         session_id = str(uuid.uuid4())
#         request.session['chat_session_id'] = session_id
#         ChatSession.objects.create(session_id=session_id)
#
#     session = ChatSession.objects.get(session_id=session_id)
#
#     # Сохраняем сообщение пользователя
#     ChatMessage.objects.create(session=session, role='user', content=user_message)
#
#     # История диалога
#     history = [
#                   {"role": msg.role, "content": msg.content}
#                   for msg in session.messages.all().order_by('created_at')[:10]
#               ][::-1]
#
#     # Профиль пользователя из сессии чата
#     user_profile = {
#         'figure': session.figure_type,
#         'color_type': session.color_type,
#         'kibbe_type': session.kibbe_type,
#     }
#
#     # Обрабатываем сообщение
#     result = giga_service.process_message(
#         user_message=user_message,
#         session=session,
#         user_profile=user_profile,
#         conversation_history=history
#     )
#
#     # Формируем ответ
#     if result['type'] == 'products':
#         answer_text = result.get('message', 'Вот что я нашёл:')
#         products = result['data'].get('items', [])
#         message_type = 'products'
#     elif result['type'] == 'outfit':
#         answer_text = result.get('message', 'Вот ваш образ:')
#         products = list(result['data'].get('outfit', {}).values())
#         message_type = 'outfit'
#     elif result['type'] == 'quiz_suggestion':
#         answer_text = result['data'].get('message', '')
#         products = []
#         message_type = 'quiz_suggestion'
#     else:
#         answer_text = result['data']
#         products = []
#         message_type = 'text'
#
#     # Сохраняем ответ ассистента
#     ChatMessage.objects.create(
#         session=session,
#         role='assistant',
#         content=answer_text,
#         products_data=products if products else None,
#         message_type=message_type
#     )
#
#     return JsonResponse({
#         'message': answer_text,
#         'products': products,
#         'type': message_type,
#         'quiz_url': result['data'].get('quiz_url') if result['type'] == 'quiz_suggestion' else None
#     })

# @csrf_exempt
# @require_http_methods(["POST"])
# def chat_send(request):
#     data = json.loads(request.body)
#     user_message = data.get('message', '')
#     if not user_message:
#         return JsonResponse({'error': 'Empty message'}, status=400)
#
#     session_id = request.session.get('chat_session_id')
#     session, _ = ChatSession.objects.get_or_create(session_id=session_id)
#
#     ChatMessage.objects.create(session=session, role='user', content=user_message)
#
#     # история
#     history = [
#                   {"role": msg.role, "content": msg.content}
#                   for msg in session.messages.all().order_by('-created_at')[:10]
#               ][::-1]
#
#     # Данные из сессии
#     user_profile = {
#         'figure': request.session.get('figure_type'),
#         'color_type': request.session.get('color_type'),
#         'kibbe_type': request.session.get('kibbe_type'),
#     }
#
#     result = giga_service.chat_with_tools(user_message, user_profile, history)
#
#     if result['type'] == 'tool_result':
#         answer_text = result.get('message', 'Вот что я нашёл:')
#         products = result['data'].get('items', [])
#     else:
#         answer_text = result['data']
#         products = []
#
#     # Сохраняем только если есть товары или непустой ответ
#     if products or answer_text:
#         ChatMessage.objects.create(
#             session=session,
#             role='assistant',
#             content=answer_text,
#             products_data=products
#         )
#
#     return JsonResponse({'message': answer_text, 'products': products})
#
#
