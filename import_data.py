import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

import csv
from quiz.models import Product, Look, LookPhoto


def import_products(csv_file='products.csv'):
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            price = row.get('price', 0)
            if price == '' or price is None:
                price = 0
            else:
                try:
                    price = float(price)
                except:
                    price = 0

            Product.objects.update_or_create(
                sku=row['sku'],
                defaults={
                    'name': row['name'],
                    'price': price,
                    'category': row.get('category', ''),
                    'url': row.get('url', ''),
                    'image': row.get('image', ''),
                    'color': row.get('color', ''),
                    'silhouette': row.get('silhouette', ''),
                    'suitable_figure': row.get('suitable_figure', ''),
                    'suitable_color': row.get('suitable_color', ''),
                    'suitable_kibbe': row.get('suitable_kibbe', ''),
                }
            )
    print(f"Импортировано продуктов: {Product.objects.count()}")

def import_looks(csv_file='NEWlooks.csv'):
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            look, created = Look.objects.update_or_create(
                obraz_id=row['obraz_id'],
                defaults={
                    'skus': row['skus'],
                    'obraz_ids_all': row.get('obraz_ids_all', row['obraz_id']),
                    'suitable_figure': row.get('suitable_figure', ''),
                    'suitable_color': row.get('suitable_color', ''),
                    'suitable_kibbe': row.get('suitable_kibbe', ''),
                    'name': row.get('name', ''),
                }
            )
    print(f"Импортировано образов: {Look.objects.count()}")

def import_photos(csv_file='look_photos.csv'):
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            look = Look.objects.filter(obraz_id=row['obraz_id']).first()
            if look:
                LookPhoto.objects.update_or_create(
                    look=look,
                    order=row.get('order', 0),
                    defaults={
                        'photo_url': row['photo_url'],
                    }
                )
    print(f"Импортировано фото: {LookPhoto.objects.count()}")

if __name__ == '__main__':
    import_products()
    import_looks()
    import_photos()