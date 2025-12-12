from flask import Flask, render_template, request, jsonify, send_from_directory
from calculator import PotionCalculator
from get_prices import get_prices
from potion import POTION_IDS
from materials import MATERIALS_IDS
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__)

# Додаємо фільтр для форматування чисел з пробілами
@app.template_filter('format_number')
def format_number(value):
    """Форматує число з пробілами для розділення тисяч"""
    if value is None:
        return "0"
    try:
        # Форматуємо з 2 знаками після коми
        formatted = f"{float(value):,.0f}"
        # Замінюємо коми на пробіли (для українського формату)
        return formatted.replace(',', ' ').replace('.', ',')
    except (ValueError, TypeError):
        return str(value)

# Список міст
CITIES = [
    "Caerleon",
    "Bridgewatch",
    "Lymhurst",
    "Martlock",
    "FortSterling",
    "Thetford",
    "Brecilien"
]

def get_image_path(item_id, image_type='potion'):
    """
    Перевіряє наявність зображення для предмета
    Повертає шлях до зображення або None
    """
    # Можливі формати файлів
    extensions = ['.png', '.jpg', '.jpeg', '.webp']
    
    # Шляхи для пошуку (підтримуємо різні варіанти назв папок)
    if image_type == 'potion':
        search_paths = [
            f'static/images/potions/{item_id}',      # potions/ (множина)
            f'static/images/potion/{item_id}',       # potion/ (однина)
            f'static/images/{item_id}',              # Без підпапки
            f'albion_icons/{item_id}',               # Стара папка
        ]
    else:  # ingredient/material
        search_paths = [
            f'static/images/materials/{item_id}',     # materials/ (як у вас)
            f'static/images/ingredients/{item_id}',  # ingredients/ (альтернатива)
            f'static/images/ingredient/{item_id}',    # ingredient/ (однина)
            f'static/images/{item_id}',               # Без підпапки
            f'albion_icons/{item_id}',                # Стара папка
        ]
    
    for path in search_paths:
        for ext in extensions:
            full_path = f'{path}{ext}'
            if os.path.exists(full_path):
                # Повертаємо шлях без 'static/' для url_for
                return full_path.replace('static/', '')
    
    return None

def load_theme():
    """Завантажує тему з theme.json"""
    theme_path = 'static/theme.json'
    default_theme = {
        'primary_color': '#4a90e2',
        'secondary_color': '#50c878',
        'danger_color': '#e74c3c',
        'warning_color': '#f39c12',
        'background_gradient_start': '#667eea',
        'background_gradient_end': '#764ba2',
        'card_background': '#ffffff',
        'text_color': '#2c3e50',
        'border_color': '#e1e8ed'
    }
    
    if os.path.exists(theme_path):
        try:
            with open(theme_path, 'r', encoding='utf-8') as f:
                user_theme = json.load(f)
                # Об'єднуємо з дефолтними значеннями
                return {**default_theme, **user_theme}
        except:
            pass
    
    return default_theme

def load_config():
    """Завантажує конфігурацію з config.json"""
    config_path = 'config.json'
    default_config = {
        'default_return_rate': 15.2  # Базовий відсоток повернення ресурсів (звичайні міста)
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                return {**default_config, **user_config}
        except:
            pass
    
    return default_config

@app.route('/')
def index():
    """Головна сторінка з формою"""
    potions = POTION_IDS
    cities = CITIES
    cache_status = get_cache_status()
    theme = load_theme()
    config = load_config()  # Завантажуємо конфігурацію
    
    # Додаємо шляхи до зображень для зілля
    potions_with_images = {}
    for potion_id, potion_name in potions.items():
        potions_with_images[potion_id] = {
            'name': potion_name,
            'image': get_image_path(potion_id, 'potion')
        }
    
    return render_template('index.html', 
                         potions=potions_with_images, 
                         cities=cities, 
                         cache_status=cache_status,
                         theme=theme,
                         default_return_rate=config['default_return_rate'])

@app.route('/calculate', methods=['POST'])
def calculate():
    """Обробка розрахунку"""
    try:
        potion_id = request.form.get('potion_id')
        craft_city = request.form.get('craft_city')
        sell_city = request.form.get('sell_city')
        quantity = int(request.form.get('quantity', 1))
        machine_cost = float(request.form.get('machine_cost', 0))
        focus_bonus = request.form.get('focus_bonus') == 'on'
        extra_bonus_enabled = request.form.get('extra_bonus') == 'on'
        extra_bonus_pct = float(request.form.get('extra_bonus_pct', 0) or 0)
        if not extra_bonus_enabled:
            extra_bonus_pct = 0.0
        premium = request.form.get('premium') == 'on'
        
        # Обробка відсотка повернення ресурсів
        use_custom_return_rate = request.form.get('use_custom_return_rate') == 'on'
        config = load_config()
        
        if use_custom_return_rate:
            # Використовуємо власний відсоток користувача
            return_rate = float(request.form.get('return_rate', 0)) / 100.0
        else:
            # Використовуємо базовий відсоток станку за містом
            return_rate = 0.248 if craft_city == "Brecilien" else 0.152
        
        if not potion_id or not craft_city or not sell_city:
            return render_template('error.html', error="Будь ласка, заповніть всі обов'язкові поля")
        
        if quantity <= 0:
            return render_template('error.html', error="Кількість повинна бути більше 0")
        
        prices = get_prices()
        if not prices:
            return render_template('error.html', error="Не вдалося завантажити ціни. Спробуйте пізніше.")
        
        calculator = PotionCalculator(
            prices=prices,
            craft_city=craft_city,
            sell_city=sell_city
        )
        
        result = calculator.calculate_craft_cost(
            potion_id=potion_id,
            quantity=quantity,
            machine_cost_per_100=machine_cost,
            focus_bonus=focus_bonus,
            extra_bonus_pct=extra_bonus_pct,
            return_rate=return_rate,
            premium=premium
        )
        
        if 'error' in result:
            return render_template('error.html', error=result['error'])
        
        # Додаємо зображення до результату
        result['potion_image'] = get_image_path(potion_id, 'potion')
        
        # Додаємо інформацію про використаний відсоток повернення
        result['used_return_rate'] = return_rate * 100
        result['is_custom_return_rate'] = use_custom_return_rate
        
        # Додаємо зображення та назви для інгредієнтів
        ingredients_with_images = {}
        for ing_id, details in result.get('ingredient_details', {}).items():
            ingredient_name = MATERIALS_IDS.get(ing_id, ing_id)
            
            ingredients_with_images[ing_id] = {
                **details,
                'name': ingredient_name,
                'image': get_image_path(ing_id, 'ingredient')
            }
        result['ingredient_details'] = ingredients_with_images
        
        theme = load_theme()
        return render_template('result.html', result=result, theme=theme)
    
    except Exception as e:
        return render_template('error.html', error=f"Помилка: {str(e)}")

@app.route('/refresh_prices', methods=['POST'])
def refresh_prices():
    """Примусове оновлення цін"""
    try:
        prices = get_prices(force_refresh=True)
        if prices:
            return jsonify({'success': True, 'message': f'Оновлено ціни для {len(prices)} предметів'})
        else:
            return jsonify({'success': False, 'message': 'Не вдалося оновити ціни'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/images/<path:filename>')
def images(filename):
    """Сервірування зображень"""
    return send_from_directory('static/images', filename)

def get_cache_status():
    """Отримує інформацію про статус кешу"""
    if not os.path.exists('last_update.txt'):
        return {'status': 'no_cache', 'message': 'Кеш відсутній'}
    
    try:
        with open('last_update.txt', 'r') as f:
            last_update_str = f.read().strip()
            last_update_time = datetime.fromisoformat(last_update_str)
            time_since_update = datetime.now() - last_update_time
        
        if time_since_update >= timedelta(hours=6):
            return {
                'status': 'expired',
                'message': f'Кеш застарів ({int(time_since_update.total_seconds() / 3600)} год тому)',
                'last_update': last_update_time
            }
        else:
            hours_left = 6 - (time_since_update.total_seconds() / 3600)
            return {
                'status': 'fresh',
                'message': f'Оновлено {int(time_since_update.total_seconds() / 3600)} год тому (залишилось ~{int(hours_left)} год)',
                'last_update': last_update_time
            }
    except Exception:
        return {'status': 'unknown', 'message': 'Невідомий статус кешу'}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
