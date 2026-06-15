import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time


def get_product_links_from_category(page_url, category_name, base_domain='https://daisyknit.ru'):
    """Собирает все ссылки на товары с одной страницы категории."""
    links = []
    try:
        response = requests.get(page_url, timeout=15)
        # Если страница не найдена (404), возвращаем None как сигнал для остановки
        if response.status_code == 404:
            return None

        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Поиск всех ссылок, ведущих на страницы товаров
        for a in soup.find_all('a', class_='href_to_page'):
            href = a.get('href')
            if href:
                full_url = urljoin(base_domain, href)
                # Очищаем от якорей и лишних параметров
                if '#' in full_url:
                    full_url = full_url.split('#')[0]
                links.append((full_url, category_name))

    except Exception as e:
        print(f"Ошибка при загрузке {page_url}: {e}")
    return links


def collect_links_for_category(category_base_url, category_name):
    """Для одной категории перебирает страницы пагинации и собирает ссылки."""
    all_category_links = []
    page_num = 1
    while True:
        if page_num == 1:
            page_url = category_base_url
        else:
            page_url = f"{category_base_url}?PAGEN_1={page_num}"

        print(f"  Обработка страницы {page_num}: {page_url}")
        page_links = get_product_links_from_category(page_url, category_name)

        # Если сервер вернул 404, значит страниц больше нет
        if page_links is None:
            print(f"  Страница {page_num} не найдена (404). Останавливаемся.")
            break
        if not page_links:
            print(f"  На странице {page_num} не найдено ссылок.")
            # Иногда на последней странице может не быть товаров, но код 200.
            # На всякий случай, если нет ссылок на первой странице - точно что-то не так.
            if page_num == 1:
                print("  На первой странице нет товаров. Проверьте URL категории.")
                break
            else:
                # Если на последующих нет товаров, считаем, что дальше пусто
                break

        print(f"  Найдено {len(page_links)} ссылок на товары")
        all_category_links.extend(page_links)
        page_num += 1
        time.sleep(1)  # Задержка между запросами страниц
    return all_category_links


def collect_all_links():
    """Собирает ссылки со всех нужных страниц каталога."""
    all_links = []
    seen_skus = set()

    #  URL-адреса страниц, которые спарсить
    category_pages = [
        ('https://daisyknit.ru/catalog/platya_1/', 'Платья'),
        ('https://daisyknit.ru/catalog/zhakety_i_zhilety/', 'Жакеты и жилеты'),
        ('https://daisyknit.ru/catalog/rubashki_i_bluzy/', 'Рубашки и блузы'),
        ('https://daisyknit.ru/catalog/bryuki_i_shorty/', 'Брюки и шорты'),
        ('https://daisyknit.ru/catalog/yubki_1/', 'Юбки'),
        ('https://daisyknit.ru/catalog/dzhinsy_i_denim/', 'Джинсы и деним'),
        ('https://daisyknit.ru/catalog/topy/', 'Топы'),
        ('https://daisyknit.ru/catalog/futbolki_i_tonkiy_trikotazh/', 'Футболки'),
        ('https://daisyknit.ru/catalog/svitery_i_dzhempery/', 'Свитеры и джемперы'),
        ('https://daisyknit.ru/catalog/tonkiy_trikotazh_1/', 'Тонкий трикотаж'),
        ('https://daisyknit.ru/catalog/verkhnyaya_odezhda_1/', 'Верхняя одежда'),
        ('https://daisyknit.ru/catalog/vyazanyy_trikotazh/', 'Вязаный трикотаж'),
        ('https://daisyknit.ru/catalog/sumki_i_aksessuary/', 'Сумки и аксессуары'),
        ('https://daisyknit.ru/catalog/obuv_2/', 'Обувь'),
        ('https://daisyknit.ru/catalog/kostyumy_i_komplekty/', 'Костюмы и комплекты'),
    ]

    for cat_url, cat_name in category_pages:
        print(f"\nОбработка категории: {cat_name}")
        links = collect_links_for_category(cat_url, cat_name)

        for url, cat in links:
            sku = extract_sku(url)
            if sku and sku not in seen_skus:
                seen_skus.add(sku)
                all_links.append((url, cat))
            elif sku:
                print(f"  Пропущен дубликат: {cat} - {url}")

        # if links:
        #     for link in links:
        #         all_links.add(link) # добавляем кортежи в set
        #     print(f"Всего для категории {cat_url} собрано {len(links)} уникальных ссылок")

        time.sleep(2)  # Небольшая пауза между категориями

    # for page_url in category_pages:
    #     print(f"Обработка категории: {page_url}")
    #     links = get_product_links_from_category(page_url)
    #     if links:
    #         all_links.update(links)
    #         print(f"  Найдено {len(links)} ссылок на товары")
    #     time.sleep(1)  # Задержка между запросами страниц категорий
    return all_links


def extract_sku(url):
    """Извлекает sku из URL (параметр sku=XXXXX)"""
    import re
    match = re.search(r'sku=(\d+)', url)
    return match.group(1) if match else None


def scrape_links():
    all_product_links = collect_all_links()

    if all_product_links:
        with open('product_links.txt', 'w', encoding='utf-8') as f:
            # for url, category in all_product_links:
            #     f.write(f"{category}|{url}\n")
            for url, category in sorted(all_product_links, key=lambda x: x[1]):
                f.write(f"{category}|{url}\n")
        print(f"\nГотово! Собрано {len(all_product_links)} ссылок. Сохранено в 'product_links.txt'")
    else:
        print("Не удалось найти ссылки на товары. Проверьте селекторы или структуру сайта.")


if __name__ == '__main__':
    scrape_links()
