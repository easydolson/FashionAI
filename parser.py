import requests
from bs4 import BeautifulSoup
import json
import csv
from collections import OrderedDict

def clean_sku(sku):
    return str(sku).strip() if sku else None

def parse_all_obrasy(max_pages=5):
    all_products = {}
    looks = OrderedDict()  # {look_key: данные}
    look_photos = []       # список для фото
    
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
            
            # Фото образа (только из images-img)
            photo_url = None
            img_block = block.find('div', class_='images-img')
            if img_block:
                img = img_block.find('img')
                if img and img.get('src'):
                    photo_url = img.get('src')
                    if photo_url.startswith('/'):
                        photo_url = f'https://daisyknit.ru{photo_url}'
            
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
                                # Извлекаем фото товара из img внутри ссылки
                                product_img = None
                                img_tag = link.find('img')
                                if img_tag and img_tag.get('src'):
                                    product_img = img_tag.get('src')
                                    if product_img.startswith('/'):
                                        product_img = f'https://daisyknit.ru{product_img}'

                                all_products[sku] = {
                                    'sku': sku,
                                    'name': product.get('item_name'),
                                    'price': product.get('price'),
                                    'category': product.get('item_category'),
                                    'url': f"https://daisyknit.ru{link.get('href', '')}",
                                    'image': product_img,
                                }
                    except:
                        pass
            
            if len(skus) >= 2:
                skus_key = ','.join(sorted(skus))
                
                if skus_key not in looks:
                    looks[skus_key] = {
                        'main_obraz_id': obraz_id,  # первый попавшийся
                        'skus': skus,
                        'obraz_ids_all': [obraz_id]
                    }
                else:
                    # Добавляем дополнительные obraz_id
                    if obraz_id not in looks[skus_key]['obraz_ids_all']:
                        looks[skus_key]['obraz_ids_all'].append(obraz_id)
                
                # Добавляем фото в отдельный список
                if photo_url:
                    look_photos.append({
                        'look_key': skus_key,
                        'photo_url': photo_url,
                        'obraz_id': obraz_id,
                        'order': len([p for p in look_photos if p['look_key'] == skus_key]) + 1
                    })
    
    return all_products, looks, look_photos

def save_to_csv(products, looks, look_photos):
    # Сохраняем товары
    with open('products.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['sku', 'name', 'price', 'category', 'url', 'image'])
        writer.writeheader()
        for p in products.values():
            writer.writerow(p)
    
    # Сохраняем образы
    with open('looks.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['obraz_id', 'skus', 'obraz_ids_all'])
        for look in looks.values():
            writer.writerow([
                look['main_obraz_id'],
                ','.join(look['skus']),
                ';'.join(look['obraz_ids_all'])
            ])
        
    # Сохраняем фото отдельно
    with open('look_photos.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['look_key', 'obraz_id', 'order', 'photo_url'])
        for photo in look_photos:
            writer.writerow([
                photo['look_key'],
                photo['obraz_id'],
                photo['order'],
                photo['photo_url']
            ])

if __name__ == '__main__':
    products, looks, look_photos = parse_all_obrasy(max_pages=5)
    
    print(f'Уникальных товаров: {len(products)}')
    print(f'Уникальных образов: {len(looks)}')
    print(f'Фото: {len(look_photos)}')
    
    save_to_csv(products, looks, look_photos)
    print('Сохранено в products.csv, looks.csv, look_photos.csv')