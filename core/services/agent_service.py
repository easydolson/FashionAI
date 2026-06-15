import json
from core.services.search_service import SearchService
from core.services.gigachat_service import GigaChatService

class FashionAgent:
    def __init__(self):
        self.giga = GigaChatService()
        self.search = SearchService()

    def process(self, user_message: str, user_profile: dict = None) -> dict:
        # 1. GigaChat решает, какой инструмент вызвать
        response = self.giga.get_response_with_tools(user_message)

        # 2. Если нужно вызвать инструмент
        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.function.name == "search_products":
                    args = json.loads(tool_call.function.arguments)
                    products = self.search.hybrid_search(args['query'], args.get('top_k', 5))

                    # 3. Применяем фильтры из профиля пользователя
                    if user_profile:
                        products = self.apply_filters(products, user_profile)

                    return {"type": "products", "data": products}

                elif tool_call.function.name == "compose_outfit":
                    args = json.loads(tool_call.function.arguments)
                    outfit = self.build_outfit(args)
                    return {"type": "outfit", "data": outfit}

        # 4. Обычный ответ
        return {"type": "message", "data": response.content}