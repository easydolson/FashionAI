def get_figure_type(answers_dict):
    """
    answers_dict: {question_order: answer_letter}
    Вопросы:
    1: Соотношение плеч/бёдер (A - плечи шире, B - равны, C - бёдра шире)
    2: Выраженность талии (A - ярко, B - слегка, C - слабо)
    3: Общая форма (A - перев.треугольник, B - песочные часы, C - груша, D - прямоугольник, E - яблоко)
    """
    q1 = answers_dict.get(1)   # вопрос order=1
    q2 = answers_dict.get(2)
    q3 = answers_dict.get(3)

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
    return 'Прямоугольник'  # fallback

def get_color_type(answers_dict):
    """
    Вопросы:
    4: Тон кожи (A - холодный светлый, B - тёплый светлый, C - оливковый/холодный, D - тёплый смуглый)
    5: Цвет волос (A - пепельный/холодный, B - золотистый/тёплый, C - тёмный холодный, D - медный/тёплый)
    6: Цвет глаз (A - холодные, B - тёплые, C - холодные летние, D - тёмные тёплые)
    """
    q4 = answers_dict.get(4)
    q5 = answers_dict.get(5)
    q6 = answers_dict.get(6)

    # Лето
    if q4 in ('A', 'C') and q5 in ('A', 'C') and q6 in ('A', 'C'):
        return 'Лето'
    # Зима
    if q4 in ('A', 'C') and q5 in ('A', 'C') and q6 in ('A', 'C') and q6 != 'B':
        # добавим уточнение: высокий контраст
        return 'Зима'
    # Весна
    if q4 in ('B', 'D') and q5 in ('B', 'D') and q6 in ('B', 'D'):
        return 'Весна'
    # Осень
    if q4 in ('B', 'D') and q5 in ('B', 'D') and q6 in ('B', 'D'):
        return 'Осень'
    return 'Лето'  # по умолчанию

def get_kibbe_type(answers_dict):
    """
    Вопросы:
    7: Костная структура (A-драматик, B-натурал, C-классик, D-романтик, E-гамин)
    8: Форма тела (A-драм, B-натурал, C-классик, D-романтик, E-гамин)
    9: Черты лица (A-драм, B-натурал, C-классик, D-романтик, E-гамин)
    10: Рост (A-высокий, B-средний, C-низкий)
    """
    q7 = answers_dict.get(7)
    q8 = answers_dict.get(8)
    q9 = answers_dict.get(9)
    q10 = answers_dict.get(10)

    # простое большинство (можно усложнить)
    types = [q7, q8, q9]
    # исключаем None
    types = [t for t in types if t]
    if not types:
        return 'Классик'
    from collections import Counter
    counter = Counter(types)
    most_common = counter.most_common(1)[0][0]
    mapping = {'A': 'Драматик', 'B': 'Натурал', 'C': 'Классик', 'D': 'Романтик', 'E': 'Гамин'}
    return mapping.get(most_common, 'Классик')