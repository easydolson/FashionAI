# test_scenarios.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from quiz.models import Look

# Сценарии: (фигура, цветотип, кибби, ожидаемые образы)
SCENARIOS = [
    ('Груша', 'Лето', 'Драматик', ['118900', '118896']),
    ('Песочные часы', 'Осень', 'Романтик', ['118783', '118775']),
    ('Прямоугольник', 'Зима', 'Классик', ['118785', '118780']),
    ('Яблоко', 'Весна', 'Гамин', ['118778']),
    ('Перевёрнутый треугольник', 'Весна', 'Натурал', ['118779']),
]


def test_scenario(figure, color, kibbe, expected):
    suitable_looks = []
    for look in Look.objects.all():
        figure_ok = (look.suitable_figure == 'Все' or figure in look.suitable_figure.split(', '))
        color_ok = (look.suitable_color == 'Все' or color in look.suitable_color.split(', '))
        kibbe_ok = (look.suitable_kibbe == 'Все' or kibbe in look.suitable_kibbe.split(', '))

        if figure_ok and color_ok and kibbe_ok:
            suitable_looks.append(look.obraz_id)

    found = suitable_looks
    passed = set(expected).issubset(set(found))
    print(f"{'✅' if passed else '❌'} {figure} + {color} + {kibbe}")
    #print(f"   Ожидалось: {expected}")
    print(f"   Найдено: {found}\n")
    return passed

if __name__ == '__main__':
    for figure, color, kibbe, expected in SCENARIOS:
        test_scenario(figure, color, kibbe, expected)