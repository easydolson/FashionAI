import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ToolResult:
    success: bool
    data: Any
    error: Optional[str] = None

class SearchTool:
    def __init__(self, search_service):
        self.search_service = search_service

    @property
    def function_spec(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "search_products",
                "description": "Поиск товаров в каталоге по текстовому запросу",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Поисковый запрос пользователя"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Количество результатов (по умолчанию 5)",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    def execute(self, query: str, top_k: int = 5) -> ToolResult:
        try:
            print(f"🔍 SearchTool.execute: query='{query}', top_k={top_k}")

            results_df = self.search_service.hybrid_search(query, top_k=top_k)

            print(f"📊 hybrid_search вернул {len(results_df)} строк")
            print(results_df[['name', 'price']].head())

            items = []
            for _, row in results_df.iterrows():
                price = row.get('price', 0)
                if hasattr(price, 'item'):
                    price = price.item()
                items.append({
                    'name': str(row.get('name', '')),
                    'price': price,
                    'image_filename': str(row.get('image_filename', '')),
                    'url': str(row.get('url', '#')),
                    'category': str(row.get('category', ''))
                })

            print(f"✅ Возвращаем {len(items)} товаров")
            return ToolResult(success=True, data={'items': items, 'query': query})
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            logger.error(f"Search error: {e}")
            return ToolResult(success=False, data=None, error=str(e))

class ToolManager:
    def __init__(self, search_service):
        self.search_tool = SearchTool(search_service)
        self.tools = {self.search_tool.function_spec['function']['name']: self.search_tool}

    def get_functions_specs(self):
        return [self.search_tool.function_spec]

    def execute_tool_call(self, tool_name: str, arguments: dict) -> ToolResult:
        tool = self.tools.get(tool_name)
        if not tool:
            return ToolResult(success=False, data=None, error=f"Unknown tool {tool_name}")
        return tool.execute(**arguments)

# """
# Инструменты для GigaChat Function Calling.
# Каждый инструмент — это функция, которую GigaChat может вызвать для выполнения конкретного действия.
# """
#
# import json
# import logging
# from typing import List, Dict, Any, Optional
# from dataclasses import dataclass, field
#
# # Настройка логирования
# logger = logging.getLogger(__name__)
#
#
# # ============================================
# # 1. ОПРЕДЕЛЕНИЕ ТИПОВ И ФОРМАТОВ
# # ============================================
#
# @dataclass
# class ToolCall:
#     """Представляет вызов инструмента от GigaChat"""
#     name: str
#     arguments: Dict[str, Any]
#
#
# @dataclass
# class ToolResult:
#     """Результат выполнения инструмента"""
#     success: bool
#     data: Any
#     error: Optional[str] = None
#
#
# # ============================================
# # 2. ИНСТРУМЕНТ ДЛЯ ПОИСКА ТОВАРОВ
# # ============================================
#
# class SearchTool:
#     """
#     Инструмент поиска товаров по текстовому запросу.
#     Использует FAISS + TF-IDF гибридный поиск.
#     """
#
#     def __init__(self, search_service):
#         """
#         Args:
#             search_service: экземпляр SearchService с методом hybrid_search
#         """
#         self.search_service = search_service
#
#     # @property
#     # def function_spec(self) -> Dict[str, Any]:
#     #     """Спецификация инструмента для GigaChat API"""
#     #     return {
#     #         "type": "function",
#     #         "function": {
#     #             "name": "search_products",
#     #             "description": "Поиск товаров в каталоге по текстовому запросу. Возвращает список товаров с названиями, ценами и ссылками.",
#     #             "parameters": {
#     #                 "type": "object",
#     #                 "properties": {
#     #                     "query": {
#     #                         "type": "string",
#     #                         "description": "Поисковый запрос пользователя. Например: 'лёгкое летнее платье', 'широкие брюки', 'обувь на осень'"
#     #                     },
#     #                     "top_k": {
#     #                         "type": "integer",
#     #                         "description": "Количество возвращаемых товаров",
#     #                         "default": 5,
#     #                         "minimum": 1,
#     #                         "maximum": 20
#     #                     },
#     #                     "category": {
#     #                         "type": "string",
#     #                         "description": "Фильтр по категории (опционально). Например: 'платья', 'брюки', 'обувь'"
#     #                     }
#     #                 },
#     #                 "required": ["query"]
#     #             }
#     #         }
#     #     }
#
#     @property
#     def function_spec(self) -> Dict[str, Any]:
#         return {
#             "type": "function",
#             "function": {
#                 "name": "search_products",
#                 "description": "Поиск товаров в каталоге по текстовому запросу",
#                 "parameters": {
#                     "type": "object",
#                     "properties": {
#                         "query": {
#                             "type": "string",
#                             "description": "Поисковый запрос. Например: 'лёгкое летнее платье'"
#                         },
#                         "top_k": {
#                             "type": "integer",
#                             "description": "Количество возвращаемых товаров",
#                             "default": 5
#                         }
#                     },
#                     "required": ["query"]
#                 }
#             }
#         }
#
#     def execute(self, query: str, top_k: int = 5, category: Optional[str] = None) -> ToolResult:
#         """
#         Выполняет поиск товаров.
#
#         Returns:
#             ToolResult с data в формате:
#             {
#                 "items": [...],
#                 "total": 5,
#                 "query": "..."
#             }
#         """
#         try:
#             # Выполняем поиск через SearchService
#             results_df = self.search_service.hybrid_search(query, top_k=top_k * 2)
#
#             # Фильтрация по категории, если указана
#             if category:
#                 results_df = results_df[results_df['category'].str.contains(category, case=False, na=False)]
#
#             # Ограничиваем результат
#             results_df = results_df.head(top_k)
#
#             # Преобразуем в список словарей
#             items = []
#             for _, row in results_df.iterrows():
#                 # Преобразуем numpy типы в Python
#                 price = row.get('price', 0)
#                 if hasattr(price, 'item'):
#                     price = price.item()
#
#                 items.append({
#                     'name': str(row.get('name', '')),
#                     'price': price,
#                     'category': str(row.get('category', '')),
#                     'image_filename': str(row.get('image_filename', '')),
#                     'url': str(row.get('url', '#'))
#                 })
#
#             return ToolResult(
#                 success=True,
#                 data={
#                     'items': items,
#                     'total': len(items),
#                     'query': query
#                 }
#             )
#         except Exception as e:
#             logger.error(f"SearchTool execution error: {e}")
#             return ToolResult(
#                 success=False,
#                 data=None,
#                 error=str(e)
#             )
#
#
# # ============================================
# # 3. ИНСТРУМЕНТ ДЛЯ ФИЛЬТРАЦИИ ПО ПРОФИЛЮ ПОЛЬЗОВАТЕЛЯ
# # ============================================
#
# class FilterByProfileTool:
#     """
#     Фильтрует товары по результатам опросника (фигура, цветотип, типаж Кибби).
#     """
#
#     @property
#     def function_spec(self) -> Dict[str, Any]:
#         return {
#             "type": "function",
#             "function": {
#                 "name": "filter_by_profile",
#                 "description": "Фильтрует список товаров по параметрам внешности пользователя (фигура, цветотип, типаж Кибби). Применяется после поиска товаров.",
#                 "parameters": {
#                     "type": "object",
#                     "properties": {
#                         "products": {
#                             "type": "array",
#                             "description": "Список товаров для фильтрации",
#                             "items": {"type": "object"}
#                         },
#                         "figure": {
#                             "type": "string",
#                             "description": "Тип фигуры пользователя (Груша, Песочные часы, Прямоугольник, Яблоко, Перевёрнутый треугольник)",
#                             "enum": ["Груша", "Песочные часы", "Прямоугольник", "Яблоко", "Перевёрнутый треугольник"]
#                         },
#                         "color_type": {
#                             "type": "string",
#                             "description": "Цветотип пользователя (Весна, Лето, Осень, Зима)",
#                             "enum": ["Весна", "Лето", "Осень", "Зима"]
#                         },
#                         "kibbe_type": {
#                             "type": "string",
#                             "description": "Типаж по Кибби (Драматик, Натурал, Классик, Романтик, Гамин)",
#                             "enum": ["Драматик", "Натурал", "Классик", "Романтик", "Гамин"]
#                         }
#                     }
#                 }
#             }
#         }
#
#     def execute(self, products: List[Dict], figure: str = None, color_type: str = None,
#                 kibbe_type: str = None) -> ToolResult:
#         """Фильтрует товары по параметрам профиля"""
#         try:
#             filtered = []
#             for p in products:
#                 # Здесь должна быть логика проверки suitable_* полей
#                 # В текущей реализации — пропускаем все товары
#                 # TODO: добавить проверку suitable_figure, suitable_color, suitable_kibbe
#                 filtered.append(p)
#
#             return ToolResult(
#                 success=True,
#                 data={'items': filtered, 'original_count': len(products), 'filtered_count': len(filtered)}
#             )
#         except Exception as e:
#             logger.error(f"FilterByProfileTool error: {e}")
#             return ToolResult(success=False, data=None, error=str(e))
#
#
# # ============================================
# # 4. ИНСТРУМЕНТ ДЛЯ СБОРКИ ОБРАЗА
# # ============================================
#
# class ComposeOutfitTool:
#     """
#     Собирает образ из товаров разных категорий (верх, низ, обувь, аксессуар).
#     """
#
#     def __init__(self, search_service):
#         self.search_service = search_service
#
#     @property
#     def function_spec(self) -> Dict[str, Any]:
#         return {
#             "type": "function",
#             "function": {
#                 "name": "compose_outfit",
#                 "description": "Собирает целостный образ из товаров разных категорий: верх, низ, обувь, аксессуар.",
#                 "parameters": {
#                     "type": "object",
#                     "properties": {
#                         "occasion": {
#                             "type": "string",
#                             "description": "Повод: свидание, работа, прогулка, вечеринка",
#                             "enum": ["свидание", "работа", "прогулка", "вечеринка"]
#                         },
#                         "style": {
#                             "type": "string",
#                             "description": "Стиль: романтичный, кэжуал, деловой, спортивный",
#                             "enum": ["романтичный", "кэжуал", "деловой", "спортивный"]
#                         },
#                         "season": {
#                             "type": "string",
#                             "description": "Сезон: лето, осень, зима, весна",
#                             "enum": ["лето", "осень", "зима", "весна"]
#                         }
#                     },
#                     "required": ["occasion", "style", "season"]
#                 }
#             }
#         }
#
#     def execute(self, occasion: str, style: str, season: str) -> ToolResult:
#         """Собирает образ на основе параметров"""
#         try:
#             # Формируем запросы для каждой категории
#             slots = {
#                 'top': {'query': f"{style} {season} топ рубашка блуза", 'category': ['топы', 'рубашки и блузы']},
#                 'bottom': {'query': f"{style} {season} брюки юбка",
#                            'category': ['брюки и шорты', 'юбки', 'джинсы и деним']},
#                 'shoes': {'query': f"{season} обувь туфли босоножки", 'category': ['обувь']},
#                 'accessory': {'query': f"{occasion} {style} аксессуары сумка", 'category': ['сумки и аксессуары']}
#             }
#
#             outfit = {}
#             for slot, config in slots.items():
#                 results = self.search_service.hybrid_search(config['query'], top_k=5)
#
#                 # Фильтрация по категории
#                 for cat in config['category']:
#                     filtered = results[results['category'].str.contains(cat, case=False, na=False)]
#                     if len(filtered) > 0:
#                         row = filtered.iloc[0]
#                         price = row.get('price', 0)
#                         if hasattr(price, 'item'):
#                             price = price.item()
#                         outfit[slot] = {
#                             'name': str(row.get('name', '')),
#                             'price': price,
#                             'category': str(row.get('category', '')),
#                             'image_filename': str(row.get('image_filename', ''))
#                         }
#                         break
#
#             return ToolResult(
#                 success=True,
#                 data={
#                     'outfit': outfit,
#                     'occasion': occasion,
#                     'style': style,
#                     'season': season
#                 }
#             )
#         except Exception as e:
#             logger.error(f"ComposeOutfitTool error: {e}")
#             return ToolResult(success=False, data=None, error=str(e))
#
#
# # ============================================
# # 5. ИНСТРУМЕНТ ДЛЯ СРАВНЕНИЯ ТОВАРОВ
# # ============================================
#
# class CompareProductsTool:
#     """
#     Сравнивает два товара по характеристикам (пока заглушка).
#     """
#
#     @property
#     def function_spec(self) -> Dict[str, Any]:
#         return {
#             "type": "function",
#             "function": {
#                 "name": "compare_products",
#                 "description": "Сравнивает два товара по основным характеристикам: цена, материал, описание.",
#                 "parameters": {
#                     "type": "object",
#                     "properties": {
#                         "product_a": {"type": "string", "description": "Название или SKU первого товара"},
#                         "product_b": {"type": "string", "description": "Название или SKU второго товара"}
#                     },
#                     "required": ["product_a", "product_b"]
#                 }
#             }
#         }
#
#     def execute(self, product_a: str, product_b: str) -> ToolResult:
#         """Сравнивает два товара"""
#         # TODO: реализовать сравнение
#         return ToolResult(
#             success=True,
#             data={
#                 'comparison': f"Сравнение {product_a} и {product_b}",
#                 'product_a': product_a,
#                 'product_b': product_b,
#                 'note': 'Функция сравнения в разработке'
#             }
#         )
#
#
# # ============================================
# # 6. ИНИЦИАЛИЗАЦИЯ ТУЛЗ-МЕНЕДЖЕРА
# # ============================================
#
# class ToolManager:
#     """
#     Менеджер для регистрации и выполнения инструментов.
#     """
#
#     def __init__(self, search_service):
#         self.tools = {}
#         self._register_default_tools(search_service)
#
#     def _register_default_tools(self, search_service):
#         """Регистрирует стандартные инструменты"""
#         self.search_tool = SearchTool(search_service)
#         # self.filter_tool = FilterByProfileTool()
#         self.outfit_tool = ComposeOutfitTool(search_service)
#         # self.compare_tool = CompareProductsTool()
#
#         self.tools[self.search_tool.function_spec['function']['name']] = self.search_tool
#         # self.tools[self.filter_tool.function_spec['function']['name']] = self.filter_tool
#         self.tools[self.outfit_tool.function_spec['function']['name']] = self.outfit_tool
#         # self.tools[self.compare_tool.function_spec['function']['name']] = self.compare_tool
#
#     def get_functions_specs(self) -> List[Dict]:
#         """Возвращает список спецификаций для GigaChat API"""
#         return [tool.function_spec for tool in self.tools.values()]
#
#     def execute_tool_call(self, tool_call: Dict) -> ToolResult:
#         """Выполняет вызов инструмента по спецификации от GigaChat"""
#         tool_name = tool_call.get('function', {}).get('name')
#         arguments = json.loads(tool_call.get('function', {}).get('arguments', '{}'))
#
#         tool = self.tools.get(tool_name)
#         if not tool:
#             return ToolResult(
#                 success=False,
#                 data=None,
#                 error=f"Unknown tool: {tool_name}"
#             )
#
#         return tool.execute(**arguments)
#
#     def get_tool_by_name(self, name: str):
#         return self.tools.get(name)