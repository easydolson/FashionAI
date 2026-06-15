import requests
from bs4 import BeautifulSoup
import json
import csv

def clean_sku(sku):
    return str(sku).strip() if sku else None

def parse_all_obrasy(max_pages=5):
    all_products = {}
    temp_looks = {}  # временное хранилище {skus_key: данные}
    
    for page in range(1, max_pages + 1):
        url = 'https://daisyknit.ru/obrazy/'
        if page > 1:
            url = f'https://daisyknit.ru/obrazy/?PAGEN_2={page}'
        
        print(f'Страница {page}')
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        blocks = soup.find_all('div', class_='element', attrs={'id': True})
        
        for block in blocks:
            obraz_id = block.get('id', '').replace('obraz-', '')

            # ТОЛЬКО фото образа (из блока images-img)
            photos = []
            img_block = block.find('div', class_='images-img')
            if img_block:
                img = img_block.find('img')
                if img and img.get('src'):
                    img_src = img.get('src')
                    # Добавляем https://daisyknit.ru в начало, если ссылка относительная
                    if img_src.startswith('/'):
                        img_src = f'https://daisyknit.ru{img_src}'
                    photos.append(img_src)
            
            # Товары образа
            skus = []
            for link in block.find_all('a', class_='images-element'):
                data = link.get('data-ecomm')
                if data:
                    try:
                        product = json.loads(data)
                        sku = clean_sku(product.get('item_id'))
                        if sku:
                            skus.append(sku)
                            
                            if sku not in all_products:
                                all_products[sku] = {
                                    'sku': sku,
                                    'name': product.get('item_name'),
                                    'price': product.get('price'),
                                    'category': product.get('item_category'),
                                    'url': f"https://daisyknit.ru{link.get('href', '')}",
                                }
                    except:
                        pass
            
            if len(skus) >= 2:
                # Группируем по составу товаров
                skus_key = ','.join(sorted(skus))
                
                if skus_key not in temp_looks:
                    temp_looks[skus_key] = {
                        'skus': skus,
                        'photos': [],
                        'obraz_ids': []
                    }
                
                # Добавляем фото (из конкретного блока)
                if photos:
                    temp_looks[skus_key]['photos'].extend(photos)
                if obraz_id not in temp_looks[skus_key]['obraz_ids']:
                    temp_looks[skus_key]['obraz_ids'].append(obraz_id)
    
    # Убираем дубликаты фото
    for look in temp_looks.values():
        look['photos'] = list(dict.fromkeys(look['photos']))  # сохраняем порядок
    
    return all_products, temp_looks


if __name__ == '__main__':
    products, looks = parse_all_obrasy(max_pages=5)
    
    print(f'Уникальных товаров: {len(products)}')
    print(f'Уникальных образов (2+ товаров): {len(looks)}')
    
    # Сохраняем товары
    with open('products.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['sku', 'name', 'price', 'category', 'url'])
        writer.writeheader()
        for p in products.values():
            writer.writerow(p)
    
    with open('looks_with_photos.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['obraz_id', 'skus', 'photos_count', 'photos'])
        for look_data in looks.values():
            first_obraz_id = look_data['obraz_ids'][0]
            writer.writerow([
                first_obraz_id,
                ','.join(look_data['skus']),
                len(look_data['photos']),
                ';'.join(look_data['photos'])
            ])
                
    print('Сохранено в products.csv и looks_with_photos.csv')