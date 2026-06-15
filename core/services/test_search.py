import os
import sys
import django

# Настройка Django окружения
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from search_service import SearchService

# Тестируем
ss = SearchService()

test_queries = [
    "легкое летнее платье",
    "широкие брюки со складками",
    "обувь на осень"
]

for q in test_queries:
    print(f"\n{'=' * 50}")
    print(f"Запрос: {q}")
    print('=' * 50)
    results = ss.hybrid_search(q, top_k=3)

    for idx, row in results.iterrows():
        print(f"  • {row['name']} | {row['price']} ₽ | {row['category']}")