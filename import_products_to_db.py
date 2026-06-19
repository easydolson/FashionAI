import os
import pandas as pd
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from quiz.models import Product


def import_products():
    csv_path = os.path.join('data', 'products_dataset_first.csv')

    if not os.path.exists(csv_path):
        print(f"❌ Файл {csv_path} не найден!")
        return

    df = pd.read_csv(csv_path)
    print(f"📂 Загружено {len(df)} товаров")

    count = 0
    for _, row in df.iterrows():
        sku = str(row.get('sku', ''))
        if not sku:
            continue

        product, created = Product.objects.update_or_create(
            sku=sku,
            defaults={
                'name': row.get('name', ''),
                'price': row.get('price', 0),
                'category': row.get('category', ''),
                'url': row.get('url', ''),
                'image': row.get('image_filename', ''),
                'color': row.get('color', ''),
                'silhouette': row.get('silhouette', ''),
                'suitable_figure': row.get('suitable_figure', ''),
                'suitable_color': row.get('suitable_color', ''),
                'suitable_kibbe': row.get('suitable_kibbe', ''),
            }
        )
        count += 1

    print(f"✅ Импортировано/обновлено {count} товаров")


if __name__ == '__main__':
    import_products()