import json
import sys
import io
import os
import random
from typing import Any, Optional
from dataclasses import dataclass
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole, Function, FunctionParameters

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


@dataclass
class ToolResult:
    success: bool
    data: Any
    error: Optional[str] = None


class GigaChatService:
    def __init__(self, search_service):
        self.client = GigaChat(
            credentials=os.environ.get('GIGACHAT_API_KEY'),
            scope="GIGACHAT_API_PERS",
            model="GigaChat",
            verify_ssl_certs=False,
            timeout=30.0
        )
        self.search_service = search_service
        self._get_functions()
        print("🔑 Ключ GigaChat:", os.environ.get('GIGACHAT_API_KEY')[:10] + "...")

    def _get_functions(self):
        """Регистрирует все доступные функции для GigaChat"""
        self.functions = [
            self._get_search_products_function(),
            self._get_compose_outfit_function(),
            self._get_add_to_outfit_function(),
            self._get_suggest_quiz_function()
        ]

    def _get_search_products_function(self) -> Function:
        return Function(
            name="search_products",
            description="Поиск товаров в каталоге по текстовому запросу",
            parameters=FunctionParameters(
                type="object",
                properties={
                    "query": {"type": "string", "description": "Поисковый запрос пользователя"},
                    "category": {"type": "string", "description": "Категория товара (платья, брюки, обувь и т.д.)"},
                    "color": {"type": "string", "description": "Цвет товара"},
                    "price_min": {"type": "integer", "description": "Минимальная цена"},
                    "price_max": {"type": "integer", "description": "Максимальная цена"},
                    "figure_type": {"type": "string", "description": "Тип фигуры (если известен)"},
                    "color_type": {"type": "string", "description": "Цветотип (если известен)"},
                    "kibbe_type": {"type": "string", "description": "Типаж Кибби (если известен)"}
                },
                required=["query"]
            )
        )

    def _get_compose_outfit_function(self) -> Function:
        return Function(
            name="compose_outfit",
            description="Собрать готовый образ из одежды",
            parameters=FunctionParameters(
                type="object",
                properties={
                    "occasion": {"type": "string", "description": "Повод (свидание, работа, прогулка, вечеринка)"},
                    "style": {"type": "string", "description": "Стиль (романтичный, деловой, кэжуал, спортивный)"},
                    "season": {"type": "string", "description": "Сезон (лето, осень, зима, весна)"},
                    "color_preference": {"type": "string", "description": "Предпочитаемый цвет"}
                },
                required=["occasion", "style"]
            )
        )

    def _get_add_to_outfit_function(self) -> Function:
        return Function(
            name="add_to_outfit",
            description="Добавить или заменить товар в существующем образе",
            parameters=FunctionParameters(
                type="object",
                properties={
                    "item_type": {"type": "string",
                                  "description": "Тип товара (сумка, обувь, аксессуар, юбка, брюки и т.д.)"},
                    "replace_slot": {"type": "string",
                                     "description": "Какой слот заменяем: top, bottom, shoes, accessory (если замена)"},
                    "outfit_id": {"type": "string", "description": "ID образа из истории (необязательно)"}
                },
                required=["item_type"]
            )
        )

    def _get_suggest_quiz_function(self) -> Function:
        return Function(
            name="suggest_quiz",
            description="Предложить пользователю пройти тест стиля для более точных рекомендаций",
            parameters=FunctionParameters(
                type="object",
                properties={},
                required=[]
            )
        )

    def _format_products(self, results_df):
        """Преобразует DataFrame с товарами в унифицированный список словарей для JSON"""
        items = []
        for _, row in results_df.iterrows():
            price = row.get('price', 0)
            if hasattr(price, 'item'):
                price = price.item()
            items.append({
                'sku': str(row.get('sku', '')),
                'name': str(row.get('name', '')),
                'price': price,
                'image_filename': str(row.get('image_filename', '')),
                'url': str(row.get('url', '#')),
                'category': str(row.get('category', ''))
            })
        return items

    def _execute_search_products(self, arguments: dict) -> ToolResult:
        """Выполняет поиск товаров по параметрам"""
        try:
            query = arguments.get('query', '')
            category = arguments.get('category')
            color = arguments.get('color')
            price_min = arguments.get('price_min')
            price_max = arguments.get('price_max')

            results = self.search_service.hybrid_search(query, top_k=30)

            if category:
                results = results[results['category'].str.contains(category, case=False, na=False)]
            if color:
                results = results[results['color'].str.contains(color, case=False, na=False)]
            if price_min:
                results = results[results['price'] >= price_min]
            if price_max:
                results = results[results['price'] <= price_max]

            results = results.drop_duplicates(subset=['name'], keep='first')
            items = self._format_products(results.head(5))

            return ToolResult(success=True, data={'items': items, 'query': query})
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

    def _execute_compose_outfit(self, arguments: dict, exclude_skus: list = None) -> ToolResult:
        """Собирает образ из товаров с учётом исключённых SKU"""
        try:
            occasion = arguments.get('occasion', '')
            style = arguments.get('style', '')
            season = arguments.get('season', '')
            slots = arguments.get('slots', ['top', 'bottom', 'shoes', 'accessory'])

            slot_queries = {
                'top': {
                    'query': f"{style} {season} топ рубашка блуза футболка свитер",
                    'keywords': ['топ', 'рубашк', 'блуз', 'футболк', 'свитер']
                },
                'bottom': {
                    'query': f"{style} {season} брюки юбка джинсы шорты",
                    'keywords': ['брюк', 'юбк', 'джинс', 'шорт']
                },
                'shoes': {
                    'query': f"{season} обувь туфли босоножки кроссовки балетки",
                    'keywords': ['обув']
                },
                'accessory': {
                    'query': f"{occasion} {style} аксессуары сумка ремень шарф украшения",
                    'keywords': ['сумк', 'аксессуар', 'ремень', 'шарф', 'украш']
                }
            }

            outfit = {}
            used_categories = set()

            # Собираем SKU уже выбранных товаров, чтобы исключить их из следующих слотов
            selected_skus = set(exclude_skus) if exclude_skus else set()

            for slot in slots:
                if slot not in slot_queries:
                    continue

                config = slot_queries[slot]
                # Добавляем случайное смещение для разнообразия
                offset = random.randint(0, 10)
                results = self.search_service.hybrid_search(
                    config['query'],
                    top_k=20,
                    exclude_skus=list(selected_skus),  # исключаем уже выбранные
                    offset=offset
                )

                if results.empty:
                    continue

                found = None
                for _, row in results.iterrows():
                    category = str(row.get('category', '')).lower()
                    if slot == 'top' and any(x in category for x in ['топ', 'рубашк', 'блуз', 'футболк']):
                        if category not in used_categories:
                            found = row
                            used_categories.add(category)
                            break
                    elif slot == 'bottom' and any(x in category for x in ['брюк', 'юбк', 'джинс', 'шорт']):
                        if category not in used_categories:
                            found = row
                            used_categories.add(category)
                            break
                    elif slot == 'shoes' and 'обув' in category:
                        if category not in used_categories:
                            found = row
                            used_categories.add(category)
                            break
                    elif slot == 'accessory' and any(x in category for x in ['сумк', 'аксессуар', 'ремень']):
                        if category not in used_categories:
                            found = row
                            used_categories.add(category)
                            break

                if found is None and not results.empty:
                    found = results.iloc[0]

                if found is not None:
                    price = found.get('price', 0)
                    if hasattr(price, 'item'):
                        price = price.item()
                    outfit[slot] = {
                        'sku': str(found.get('sku', '')),
                        'name': str(found.get('name', '')),
                        'price': price,
                        'image_filename': str(found.get('image_filename', '')),
                        'url': str(found.get('url', '#')),
                        'category': str(found.get('category', ''))
                    }

            return ToolResult(
                success=True,
                data={
                    'outfit': outfit,
                    'occasion': occasion,
                    'style': style,
                    'season': season,
                    'slots_used': list(outfit.keys())
                }
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

    def _execute_add_to_outfit(self, arguments: dict, session) -> ToolResult:
        """Добавляет или заменяет товар в образе"""
        try:
            item_type = arguments.get('item_type', '')
            replace_slot = arguments.get('replace_slot', None)

            from chat.models import ChatMessage
            last_look = ChatMessage.objects.filter(session=session, message_type='outfit').last()

            if not last_look or not last_look.products_data:
                return ToolResult(success=False, data=None, error="Нет предыдущих образов")

            # ========== ОПРЕДЕЛЯЕМ СЛОТ ПО КЛЮЧЕВЫМ СЛОВАМ ==========
            slot_keywords = {
                'bottom': ['шорты', 'джинсы', 'брюки', 'юбка', 'штаны', 'брюк', 'юбк', 'джинс', 'шорт'],
                'top': ['блуза', 'топ', 'рубашка', 'свитер', 'футболка', 'блуз', 'рубашк', 'футболк'],
                'shoes': ['туфли', 'кроссовки', 'босоножки', 'мюли', 'обувь', 'туфл', 'кроссовк'],
                'accessory': ['сумка', 'ремень', 'шарф', 'аксессуар', 'сумк', 'ремен', 'шарф']
            }

            if not replace_slot:
                # Если слот не указан — определяем по типу товара
                for slot, keywords in slot_keywords.items():
                    if any(kw in item_type.lower() for kw in keywords):
                        replace_slot = slot
                        break
                if not replace_slot:
                    replace_slot = 'accessory'  # fallback
            # =========================================================

            # Проверяем, есть ли товар в этом слоте
            # products_data может быть списком (для look) или словарём (для outfit)
            products_data = last_look.products_data
            if isinstance(products_data, list):
                # Если это список образов, берём первый
                products_data = products_data[0] if products_data else {}
            elif not isinstance(products_data, dict):
                products_data = {}

            # Проверяем слот
            replace_sku = None
            if replace_slot and replace_slot in last_look.products_data:
                replace_sku = last_look.products_data[replace_slot].get('sku')

            # Собираем все SKU из текущего образа (чтобы исключить их)
            all_skus_in_outfit = []
            for slot, product in last_look.products_data.items():
                if product and product.get('sku'):
                    all_skus_in_outfit.append(product.get('sku'))

            # ========== КАТЕГОРИИ ДЛЯ ПОИСКА ==========
            # Сначала ищем вручную по точным ключевым словам
            category_keywords = {
                'юбка': 'юбки', 'юбку': 'юбки',
                'брюки': 'брюки и шорты', 'шорты': 'брюки и шорты',
                'штаны': 'брюки и шорты',
                'джинсы': 'джинсы и деним',
                'сумка': 'сумки и аксессуары', 'сумку': 'сумки и аксессуары', 'рюкзак': 'сумки и аксессуары',
                'панама': 'головные уборы', 'шапка': 'головные уборы',
                'туфли': 'обувь', 'босоножки': 'обувь', 'обувь': 'обувь',
                'кроссовки': 'обувь', 'балетки': 'обувь', 'мюли': 'обувь', 'сандалии': 'обувь',
                'блуза': 'топы и блузы', 'блузу': 'топы и блузы',
                'топ': 'топы и блузы', 'рубашка': 'топы и блузы', 'рубашку': 'топы и блузы',
                'ремень': 'сумки и аксессуары', 'шарф': 'сумки и аксессуары',
                'платье': 'платья', 'сарафан': 'платья'
            }

            # Находим категорию для поиска (по ключевым словам)
            search_category = None
            for key, category in category_keywords.items():
                if key in item_type.lower():
                    search_category = category
                    break

            # Если категория не найдена вручную — передаём запрос в GigaChat
            if not search_category:
                category_result = self._determine_category(item_type)
                if category_result and category_result.get('category'):
                    search_category = category_result['category']
                    if not replace_slot and category_result.get('slot'):
                        replace_slot = category_result['slot']

            # ========== ПОИСК ТОВАРОВ ==========
            # Ищем по типу товара, исключая все SKU из образа
            results = self.search_service.hybrid_search(
                item_type,
                top_k=20,
                exclude_skus=all_skus_in_outfit  # исключаем все товары из образа
            )

            # Дополнительная фильтрация по категории
            if search_category:
                results = results[results['category'].str.contains(search_category, case=False, na=False)]

            # Если ничего не найдено — пробуем без фильтрации категории
            if results.empty:
                results = self.search_service.hybrid_search(item_type, top_k=15, exclude_skus=all_skus_in_outfit)

            # Если всё равно пусто — возвращаем fallback
            if results.empty:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Не нашла подходящий товар для замены '{item_type}'. Попробуйте другой запрос."
                )

            results = results.drop_duplicates(subset=['name'], keep='first')
            items = self._format_products(results.head(5))

            # ========== ФОРМИРУЕМ СООБЩЕНИЕ ==========
            if replace_slot:
                message = f"Нашла замену для {item_type.lower()} (вместо {replace_slot}). Выберите подходящий вариант:"
            else:
                message = f"Нашла {item_type.lower()} для вашего образа. Выберите подходящий вариант:"

            return ToolResult(
                success=True,
                data={
                    'items': items,
                    'item_type': item_type,
                    'replace_slot': replace_slot,
                    'message': message
                }
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

    def _determine_category(self, item_type: str) -> dict:
        """Определяет категорию и слот товара через GigaChat"""
        try:
            # Небольшой промпт для GigaChat
            messages = [
                Messages(role=MessagesRole.SYSTEM, content="""
    Ты — ассистент, который определяет категорию одежды по запросу пользователя.
    Ответь в формате JSON:
    {"category": "категория из списка: топы и блузы, брюки и шорты, юбки, обувь, сумки и аксессуары, головные уборы, платья, джинсы и деним", 
     "slot": "top|bottom|shoes|accessory"}
    Если категория не определена, верни {"category": null, "slot": null}
    """),
                Messages(role=MessagesRole.USER, content=f"Категория товара: {item_type}")
            ]

            response = self.client.chat(Chat(messages=messages))
            content = response.choices[0].message.content
            # Парсим JSON из ответа
            import json
            try:
                result = json.loads(content)
                return result
            except:
                return {"category": None, "slot": None}
        except Exception as e:
            print(f"❌ Ошибка определения категории: {e}")
            return {"category": None, "slot": None}

        #     search_category = category_map.get(item_type.lower(), '')
        #
        #     results = self.search_service.hybrid_search(item_type, top_k=15)
        #     if search_category:
        #         results = results[results['category'].str.contains(search_category, case=False, na=False)]
        #
        #     if replace_sku:
        #         results = results[results['sku'] != replace_sku]
        #
        #     results = results.drop_duplicates(subset=['name'], keep='first')
        #     items = self._format_products(results.head(5))
        #
        #     return ToolResult(success=True, data={'items': items, 'item_type': item_type, 'replace_slot': replace_slot})
        # except Exception as e:
        #     return ToolResult(success=False, data=None, error=str(e))

    def _execute_suggest_quiz(self) -> ToolResult:
        """Предлагает пройти тест стиля"""
        return ToolResult(
            success=True,
            data={
                'message': '✨ Хотите получать более точные рекомендации? Пройдите короткий тест стиля, и я буду учитывать вашу фигуру, цветотип и типаж Кибби!',
                'quiz_url': '/start_quiz/'
            }
        )

    def process_message(self, user_message: str, session, user_profile: dict = None, conversation_history: list = None):
        """Основной метод обработки сообщения"""
        messages = []

        system_content = """Ты — профессиональный ИИ-стилист интернет-магазина женской одежды Daisyknit.

## ПРАВИЛА ОТВЕТОВ
- Отвечай кратко, максимум 2-3 предложения.
- Называй только повод и стиль образа.
- Не перечисляй все товары текстом — они и так будут показаны.
- Не используй эмодзи.
- В конце каждого ответа предлагай 1-2 варианта действий: "Подобрать другой?", "Заменить что-то?", "Добавить аксессуары?"

Пример хорошего ответа: "Подобрал для вас лёгкий летний образ в стиле кэжуал. Он подчеркнёт вашу фигуру и подойдёт для прогулки. Хотите посмотреть другие варианты?"

## ДОСТУПНЫЕ ФУНКЦИИ
- search_products — для поиска конкретных товаров
- compose_outfit — для создания готовых образов
- add_to_outfit — для дополнения/замены товаров в образе
- suggest_quiz — для предложения пройти тест стиля

## ДОСТУПНЫЕ КАТЕГОРИИ ТОВАРОВ
В каталоге есть следующие категории:
- Верх: топы, блузы, рубашки, футболки, свитера, жакеты, кардиганы
- Низ: брюки, джинсы, юбки, шорты
- Платья: платья, сарафаны, комбинезоны
- Обувь: туфли, босоножки, кроссовки, мюли, балетки, сандалии, ботильоны
- Верхняя одежда: куртки, ветровки, пальто, тренчи, бомберы
- Аксессуары: сумки, рюкзаки, ремни, шарфы, головные уборы (панамы, шапки), очки, украшения

Если пользователь запрашивает товар, название которого не совпадает с категорией (например, "рюкзак" — это аксессуар, "панама" — головной убор), используй соответствующую категорию из списка.

## КОГДА КАКУЮ ФУНКЦИЮ ВЫЗЫВАТЬ
## ПРАВИЛА ДЛЯ compose_outfit
Используй compose_outfit для запросов:
- "образ на [повод]", "собери образ на [повод]", "на [повод]" → compose_outfit(occasion="[повод]")
- "образ для [повод]", "для [повод]" → compose_outfit(occasion="[повод]")
- "составь образ", "подбери образ", "собери лук" → compose_outfit(occasion="прогулка")
- "с платьем", "в платье", "образ с платьем" → compose_outfit(occasion="вечер", style="романтичный")
- "на выпускной", "на свадьбу", "на вечеринку" → compose_outfit(occasion="[повод]", style="праздничный")
- "в офис", "на работу", "деловой образ" → compose_outfit(occasion="работа", style="деловой")

## ПРАВИЛА ДЛЯ add_to_outfit
- "замени [что-то] на [что-то]" → add_to_outfit(item_type="[новое]", replace_slot="[старое]")
- "другую обувь", "другие туфли" → add_to_outfit(item_type="обувь", replace_slot="shoes")
- "добавь сумку", "сумку к этому" → add_to_outfit(item_type="сумку")
- "замени шорты на юбку" → add_to_outfit(item_type="юбку", replace_slot="bottom")
- "замени джинсы на брюки" → add_to_outfit(item_type="брюки", replace_slot="bottom")

### ПРАВИЛА ДЛЯ search_products (поиск товаров)
Используй search_products для запросов:
- "найди [товар]", "покажи [товар]", "где [товар]" → search_products(query="[товар]")
- "платье", "джинсы", "туфли" (без слова "образ") → search_products(query="[товар]")
- "подбери [товар]" → search_products(query="[товар]")

### suggest_quiz (предложение теста)
- ТОЛЬКО если пользователь НЕ проходил опрос (нет параметров фигура/цветотип/кибби)
- НЕ предлагать тест, если параметры уже переданы в user_profile

## ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ
Учитывай параметры пользователя (фигура, цветотип, типаж Кибби), если они переданы.  Если параметры переданы — НЕ ПРЕДЛАГАЙ тест стиля.
"""

        # ========== ФОРМИРУЕМ ОДНО СИСТЕМНОЕ СООБЩЕНИЕ ==========
        if user_profile and user_profile.get('figure'):
            profile_context = f"Параметры пользователя: фигура={user_profile['figure']}, цветотип={user_profile.get('color_type')}, типаж={user_profile.get('kibbe_type')}"
            system_content += "\n\n" + profile_context

        messages.append(Messages(role=MessagesRole.SYSTEM, content=system_content))
        # ========================================================

        if conversation_history:
            for msg in conversation_history[-10:]:
                role = MessagesRole.USER if msg['role'] == 'user' else MessagesRole.ASSISTANT
                messages.append(Messages(role=role, content=msg['content']))

        messages.append(Messages(role=MessagesRole.USER, content=user_message))

        print("📤 Запрос к GigaChat:", user_message[:50] + "..." if len(user_message) > 50 else user_message)
        print("🧠 Профиль:", user_profile)
        print("📜 История:", len(conversation_history) if conversation_history else 0, "сообщений")
        response = self.client.chat(
            Chat(
                messages=messages,
                functions=self.functions,
                function_call="auto"
            )
        )

        # messages.append(Messages(role=MessagesRole.SYSTEM, content=system_content))
        #
        # if user_profile and user_profile.get('figure'):
        #     profile_context = f"Параметры пользователя: фигура={user_profile['figure']}, цветотип={user_profile.get('color_type')}, типаж={user_profile.get('kibbe_type')}"
        #     messages.append(Messages(role=MessagesRole.SYSTEM, content=profile_context))
        #
        # if conversation_history:
        #     for msg in conversation_history[-10:]:
        #         role = MessagesRole.USER if msg['role'] == 'user' else MessagesRole.ASSISTANT
        #         messages.append(Messages(role=role, content=msg['content']))
        #
        # messages.append(Messages(role=MessagesRole.USER, content=user_message))
        #
        # response = self.client.chat(
        #     Chat(
        #         messages=messages,
        #         functions=self.functions,
        #         function_call="auto"
        #     )
        # )

        choice = response.choices[0]

        if choice.finish_reason == "function_call" and choice.message.function_call:
            fc = choice.message.function_call
            result = None
            response_type = None

            if fc.name == "search_products":
                result = self._execute_search_products(fc.arguments)
                response_type = "products"
            elif fc.name == "compose_outfit":
                exclude_skus = []
                if conversation_history:
                    for msg in reversed(conversation_history):
                        if msg.get('products_data'):
                            for product in msg.get('products_data', []):
                                sku = product.get('sku')
                                if sku:
                                    exclude_skus.append(sku)
                result = self._execute_compose_outfit(fc.arguments, exclude_skus=exclude_skus)
                response_type = "outfit"
            elif fc.name == "add_to_outfit":
                result = self._execute_add_to_outfit(fc.arguments, session)
                response_type = "products"
            elif fc.name == "suggest_quiz":
                result = self._execute_suggest_quiz()
                response_type = "quiz_suggestion"

            if not result or not result.success:
                return {"type": "message", "data": result.error if result else "Извините, не удалось выполнить запрос."}

            messages.append(
                Messages(role=MessagesRole.ASSISTANT, content=choice.message.content or "", function_call=fc))
            messages.append(
                Messages(role=MessagesRole.FUNCTION, content=json.dumps(result.data, ensure_ascii=False), name=fc.name))

            final_response = self.client.chat(Chat(messages=messages))
            final_text = final_response.choices[0].message.content

            if response_type in ["products", "outfit"]:
                return {"type": response_type, "data": result.data, "message": final_text}
            elif response_type == "quiz_suggestion":
                return {"type": "quiz_suggestion", "data": result.data}

        print("⚠️ GigaChat не вызвал функцию, активируем Fallback.")

        last_products = None
        last_message_type = None

        if conversation_history:
            for msg in reversed(conversation_history):
                if msg.get('role') == 'assistant' and msg.get('products_data'):
                    last_products = msg.get('products_data')
                    last_message_type = msg.get('message_type', 'text')
                    break

        if last_products:
            if last_message_type == 'outfit':
                return {
                    "type": "outfit",
                    "data": {"outfit": last_products},
                    "message": "Вот ваш образ:"
                }
            else:
                return {
                    "type": "products",
                    "data": {"items": last_products},
                    "message": "Вот что я нашёл:"
                }
        else:
            fallback_products = self.search_service.get_fallback_products(query=user_message, last_category=None)
            return {
                "type": "products",
                "data": {"items": fallback_products},
                "message": "Вот что я могу вам предложить:"
            }
