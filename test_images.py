import os

def test_image_paths():
    """Тестова функція для перевірки шляхів до зображень"""
    item_id = "T8_POTION_CLEANSE"
    image_type = "potion"
    
    extensions = ['.png', '.jpg', '.jpeg', '.webp']
    search_paths = [
        f'static/images/{image_type}s/{item_id}',  # potions/
        f'static/images/{image_type}/{item_id}',     # potion/
        f'static/images/{item_id}',                  # Без підпапки
        f'albion_icons/{item_id}',                   # Стара папка
    ]
    
    print(f"Шукаємо зображення для: {item_id}")
    print("=" * 50)
    
    found = False
    for path in search_paths:
        for ext in extensions:
            full_path = f'{path}{ext}'
            exists = os.path.exists(full_path)
            print(f"{'✓' if exists else '✗'} {full_path}")
            if exists:
                found = True
                print(f"  → Знайдено! Повний шлях: {os.path.abspath(full_path)}")
    
    if not found:
        print("\n❌ Зображення не знайдено!")
        print("\nПеревірте:")
        print(f"1. Чи існує файл: static/images/potion/{item_id}.png")
        print(f"2. Чи правильна назва файлу (має бути точно: {item_id}.png)")
        print(f"3. Чи правильна папка (має бути: static/images/potion/)")
    else:
        print("\n✅ Зображення знайдено!")

if __name__ == '__main__':
    test_image_paths()
