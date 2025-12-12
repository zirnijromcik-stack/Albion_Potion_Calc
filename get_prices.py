import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

# Albion Data API base URL
ALBION_API_BASE = "https://www.albion-online-data.com/api/v2/stats/prices"
# Основні локації для отримання цін (можна додати більше)
DEFAULT_LOCATIONS = "Caerleon,Bridgewatch,Lymhurst,Martlock,FortSterling,Thetford,Brecilien"  # ДОДАНО: Brecilien
DEFAULT_QUALITY = "1"  # Якість предметів (1 = нормальна)

def fetch_prices_for_items(item_ids: list, locations: str = DEFAULT_LOCATIONS, quality: str = DEFAULT_QUALITY) -> Dict:
    """
    Отримує ціни для списку предметів з API Albion Online
    
    Args:
        item_ids: Список ID предметів (наприклад, ["T4_BAG", "T5_HEAD_PLATE_SET1"])
        locations: Локації для отримання цін (розділені комами)
        quality: Якість предметів (1-5)
    
    Returns:
        Словник з цінами: {item_id: {city: {prices...}}}
    """
    if not item_ids:
        return {}
    
    # Формуємо URL з параметрами
    items_param = ",".join(item_ids)
    url = f"{ALBION_API_BASE}/{items_param}?locations={locations}&qualities={quality}"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # Перетворюємо список у словник для зручності
            prices_dict = {}
            for item_data in data:
                item_id = item_data.get('item_id', '')
                city = item_data.get('city', '')
                if item_id and city:
                    # Створюємо структуру: {item_id: {city: {prices...}}}
                    if item_id not in prices_dict:
                        prices_dict[item_id] = {}
                    
                    prices_dict[item_id][city] = {
                        'buy_price_max': item_data.get('buy_price_max', 0),
                        'sell_price_min': item_data.get('sell_price_min', 0),
                        'buy_price_min': item_data.get('buy_price_min', 0),
                        'sell_price_max': item_data.get('sell_price_max', 0),
                    }
            return prices_dict
        else:
            print(f"Помилка API: статус код {response.status_code}")
            return {}
    except requests.exceptions.RequestException as e:
        print(f"Помилка при запиті до API: {e}")
        return {}

def get_all_items_from_modules() -> list:
    """
    Збирає всі ID предметів з potion.py та materials.py
    """
    from potion import POTION_IDS
    from materials import MATERIALS_IDS
    
    all_items = list(POTION_IDS.keys()) + list(MATERIALS_IDS.keys())
    return all_items

def save_prices_to_cache(prices: Dict, cache_file: str = "prices_cache.json"):
    """Зберігає ціни в кеш"""
    cache_data = {
        'prices': prices,
        'timestamp': datetime.now().isoformat()
    }
    with open(cache_file, "w", encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    # Оновлюємо час останнього оновлення
    with open("last_update.txt", "w") as time_file:
        time_file.write(datetime.now().isoformat())

def load_cached_prices(cache_file: str = "prices_cache.json", max_age_hours: int = 6) -> Optional[Dict]:
    """
    Завантажує ціни з кешу, якщо вони не застарілі
    
    Args:
        cache_file: Шлях до файлу кешу
        max_age_hours: Максимальний вік кешу в годинах
    
    Returns:
        Словник з цінами або None, якщо кеш застарів/не існує
    """
    if not os.path.exists(cache_file):
        return None
    
    if not os.path.exists("last_update.txt"):
        return None
    
    try:
        with open("last_update.txt", "r") as time_file:
            last_update_str = time_file.read().strip()
            last_update_time = datetime.fromisoformat(last_update_str)
        
        # Перевіряємо, чи не минув час для оновлення кешу
        if datetime.now() - last_update_time < timedelta(hours=max_age_hours):
            with open(cache_file, "r", encoding='utf-8') as f:
                cache_data = json.load(f)
                return cache_data.get('prices', {})
    except (ValueError, json.JSONDecodeError, IOError) as e:
        print(f"Помилка при завантаженні кешу: {e}")
        return None
    
    return None

def get_prices(force_refresh: bool = False, locations: str = DEFAULT_LOCATIONS, auto_refresh: bool = True) -> Dict:
    """
    Отримує ціни - спочатку з кешу, якщо він актуальний, інакше з API
    
    Args:
        force_refresh: Якщо True, примусово оновлює ціни з API
        locations: Локації для отримання цін
        auto_refresh: Якщо True, автоматично оновлює ціни, якщо вони застарілі (старші 6 годин)
    
    Returns:
        Словник з цінами
    """
    # Перевіряємо актуальність кешу
    if not force_refresh and auto_refresh:
        cached_prices = load_cached_prices(max_age_hours=6)
        if cached_prices:
            # Перевіряємо, чи потрібно оновлення
            if os.path.exists("last_update.txt"):
                try:
                    with open("last_update.txt", "r") as time_file:
                        last_update_str = time_file.read().strip()
                        last_update_time = datetime.fromisoformat(last_update_str)
                        time_since_update = datetime.now() - last_update_time
                        
                        if time_since_update >= timedelta(hours=6):
                            print(f"Кеш застарів ({time_since_update.seconds // 3600} годин тому). Оновлюємо...")
                            force_refresh = True  # Автоматично оновлюємо
                        else:
                            hours_left = 6 - (time_since_update.seconds // 3600)
                            print(f"Використовуємо кешовані дані (оновлено {time_since_update.seconds // 3600} год тому, залишилось ~{hours_left} год до оновлення).")
                            return cached_prices
                except (ValueError, IOError):
                    pass
    
    if not force_refresh:
        cached_prices = load_cached_prices()
        if cached_prices:
            print("Використовуємо кешовані дані.")
            return cached_prices
    
    print("Оновлюємо ціни з API...")
    all_items = get_all_items_from_modules()
    
    # API має обмеження на кількість предметів в одному запиті (зазвичай ~100)
    # Розбиваємо на батчі
    batch_size = 50
    all_prices = {}
    
    for i in range(0, len(all_items), batch_size):
        batch = all_items[i:i + batch_size]
        print(f"Завантаження цін для предметів {i+1}-{min(i+batch_size, len(all_items))} з {len(all_items)}...")
        batch_prices = fetch_prices_for_items(batch, locations)
        all_prices.update(batch_prices)
        # Невелика затримка між запитами, щоб не перевантажити API
        import time
        if i + batch_size < len(all_items):
            time.sleep(0.5)
    
    if all_prices:
        save_prices_to_cache(all_prices)
        print(f"Оновлено ціни для {len(all_prices)} предметів.")
    else:
        print("Попередження: не вдалося отримати ціни з API.")
        # Спробуємо завантажити старі дані з кешу
        cached_prices = load_cached_prices(max_age_hours=999999)  # Беремо навіть старі дані
        if cached_prices:
            print("Використовуємо застарілі дані з кешу.")
            return cached_prices
    
    return all_prices

def get_item_price(item_id: str, prices: Dict, city: str = "Caerleon", price_type: str = "sell_price_min") -> float:
    """
    Отримує ціну конкретного предмета
    
    Args:
        item_id: ID предмета
        prices: Словник з усіма цінами
        city: Місто для отримання ціни
        price_type: Тип ціни ('sell_price_min', 'buy_price_max', тощо)
    
    Returns:
        Ціна предмета або 0, якщо не знайдено
    """
    if item_id not in prices:
        print(f"Попередження: предмет {item_id} не знайдено в цінах")
        return 0.0
    
    item_data = prices[item_id]
    
    # Якщо дані зберігаються по містах
    if isinstance(item_data, dict):
        # Спочатку шукаємо в обраному місті
        if city in item_data:
            city_data = item_data[city]
            if isinstance(city_data, dict):
                price = city_data.get(price_type, 0)
                if price > 0:
                    return float(price)
        
        # Якщо в обраному місті немає ціни або вона 0, шукаємо в інших містах
        # Пріоритет: Caerleon > Thetford > інші
        priority_cities = ["Caerleon", "Thetford", "Bridgewatch", "Lymhurst", "Martlock", "FortSterling", "Brecilien"]
        
        for priority_city in priority_cities:
            if priority_city in item_data and priority_city != city:
                city_data = item_data[priority_city]
                if isinstance(city_data, dict):
                    price = city_data.get(price_type, 0)
                    if price > 0:
                        print(f"Попередження: для {item_id} в {city} немає ціни (або 0), використовуємо {priority_city}: {price}")
                        return float(price)
        
        # Якщо не знайшли в пріоритетних, шукаємо в будь-якому місті
        for other_city, city_data in item_data.items():
            if isinstance(city_data, dict) and other_city != city:
                price = city_data.get(price_type, 0)
                if price > 0:
                    print(f"Попередження: для {item_id} в {city} немає даних, використовуємо {other_city}: {price}")
                    return float(price)
    
    return 0.0

# Приклад використання
if __name__ == "__main__":
    prices = get_prices()
    print(f"Завантажено цін: {len(prices)}")
    # Приклад отримання ціни
    if prices:
        first_item = list(prices.keys())[0]
        print(f"Приклад: {first_item} = {prices[first_item]}")