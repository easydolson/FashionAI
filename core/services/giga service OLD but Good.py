import json
import sys
import io
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole, FunctionCall
from .tools import ToolManager
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')



class GigaChatService:
    def __init__(self, search_service):
        self.client = GigaChat(
            credentials="/MDE5ZTUzY2MtZjEwOC03ZGY4LWIyMDUtNWE1YTg1YjNlYzZjOjgyMGE2ODdhLTQzY2ItNGMyYy1iM2MwLTEzYTQwMGI1YWVjYg==",
            scope="GIGACHAT_API_PERS",
            model="GigaChat",
            verify_ssl_certs=False,
            timeout=30.0
        )
        self.tool_manager = ToolManager(search_service)

    def chat_with_tools(self, user_message: str, user_profile=None, conversation_history=None):
        messages = [
            Messages(role=MessagesRole.SYSTEM, content="""
                Ты — AI-ассистент интернет-магазина одежды Daisyknit. 
                Твоя задача — вызывать функцию search_products для любых запросов о товарах. 
                Никогда не выдумывай товары.
                Если ты получил результат от функции search_products, ты ОБЯЗАН написать КОРОТКОЕ вступление (1 предложение), например: "Вот что я нашёл по вашему запросу:".
                И спроси уточняющие вопросы, по типу "Хотите добавить акссесуары?" или "Хотите посмотреть другие варианты?" 
                Не перечисляй товары в тексте. Не пиши "1. Джинсы Straight – 12800 ₽". Не добавляй ссылки.
                """)
        ]

        if user_profile and user_profile.get('figure'):
            profile_context = f"Пользователь: фигура={user_profile.get('figure')}, цветотип={user_profile.get('color_type')}, типаж={user_profile.get('kibbe_type')}"
            messages.append(Messages(role=MessagesRole.SYSTEM, content=profile_context))

        if conversation_history:
            for msg in conversation_history[-10:]:
                role = MessagesRole.USER if msg['role'] == 'user' else MessagesRole.ASSISTANT
                messages.append(Messages(role=role, content=msg['content']))

        messages.append(Messages(role=MessagesRole.USER, content=user_message))

        # Первый запрос: обязательно вызываем функцию. Модель решает, вызывать ли функцию
        response = self.client.chat(
            Chat(
                messages=messages,
                functions=self._get_functions_specs(),
                function_call="auto"
            )
        )
        choice = response.choices[0]

        # Если модель вызвала функцию
        if choice.finish_reason == "function_call" and choice.message.function_call:
            fc: FunctionCall = choice.message.function_call
            # 1. Выполняем нашу функцию поиска
            result = self.tool_manager.execute_tool_call(fc.name, fc.arguments)

            if not result.success or not result.data.get('items'):
                return {"type": "message", "data": "Извините, по вашему запросу ничего не найдено."}

            # 2. Добавляем в историю сообщение ассистента с ВЫЗОВОМ функции
            messages.append(Messages(
                role=MessagesRole.ASSISTANT,
                content=choice.message.content or "",
                function_call=fc
            ))

            # 3. Добавляем результат выполнения функции
            messages.append(Messages(
                role=MessagesRole.FUNCTION,
                content=json.dumps(result.data, ensure_ascii=False),
                name=fc.name
            ))

            # # 4. Добавляем систему-инструкцию (ВЕРНУЛИ!)
            # messages.append(Messages(role=MessagesRole.SYSTEM,
            #                          content="Перечисли пользователю найденные товары с ценами. Не добавляй ничего от себя."))

            # 5. Второй запрос
            final_response = self.client.chat(
                Chat(
                    messages=messages,
                    functions=self._get_functions_specs(),
                    function_call="auto"
                )
            )
            final_text = final_response.choices[0].message.content

            return {
                "type": "tool_result",
                "data": result.data,
                "message": final_text
            }

        # Если модель не вызвала функцию (обычный диалог)
        else:
            return {"type": "message", "data": choice.message.content}

    def _get_functions_specs(self):
        from gigachat.models import Function, FunctionParameters

        functions = []
        for spec in self.tool_manager.get_functions_specs():
            func_data = spec.get('function', {})
            params_data = func_data.get('parameters', {})

            params = None
            if params_data:
                params = FunctionParameters(
                    type=params_data.get('type', 'object'),
                    properties=params_data.get('properties', {}),
                    required=params_data.get('required', [])
                )

            function = Function(
                name=func_data.get('name', ''),
                description=func_data.get('description', ''),
                parameters=params
            )
            functions.append(function)

        return functions
