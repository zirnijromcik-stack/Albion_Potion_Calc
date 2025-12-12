from typing import Dict, Optional, Tuple
from recipes import RECIPES
from potion import POTION_IDS, POTION_ITEM_VALUES
from materials import MATERIALS_IDS
from get_prices import get_prices, get_item_price

# Nutrition per ItemValue. Adjusted to match in-game station fee (e.g. T6 heal in Brecilien).
NUTRITION_RATIO = 0.07125
SALES_TAX_RATE = 0.08     # 8% market sales tax
LISTING_FEE_RATE = 0.025  # 2.5% listing fee when creating sell order

class PotionCalculator:
    """Калькулятор вартості крафту зілля"""
    
    def __init__(self, prices: Optional[Dict] = None, craft_city: str = "Caerleon", sell_city: str = "Caerleon"):
        """
        Ініціалізація калькулятора
        
        Args:
            prices: Словник з цінами (якщо None, завантажить автоматично)
            craft_city: Місто для крафту
            sell_city: Місто для продажу
        """
        self.prices = prices if prices is not None else get_prices()
        self.craft_city = craft_city
        self.sell_city = sell_city
        # Податок і комісія за розміщення ордера на ринку
        self.sales_tax = SALES_TAX_RATE
        self.listing_fee = LISTING_FEE_RATE
        
        # Бонус міста Бресіліон на крафт зілля (+15%)
        self.brecilien_craft_bonus = 0.15 if craft_city == "Brecilien" else 0.0

    def _get_item_value(self, potion_id: str) -> float:
        """
        Returns the ItemValue for a potion. Needed to convert nutrition → silver.
        """
        return float(POTION_ITEM_VALUES.get(potion_id, 0.0))
    
    def calculate_ingredient_cost(self, potion_id: str, use_buy_price: bool = False) -> Tuple[float, Dict]:
        """
        Розраховує вартість інгредієнтів для зілля
        
        Args:
            potion_id: ID зілля
            use_buy_price: Якщо True, використовує ціну покупки, інакше - продажу
        
        Returns:
            Кортеж (загальна вартість, деталізація по інгредієнтах)
        """
        if potion_id not in RECIPES:
            return 0.0, {}
        
        recipe = RECIPES[potion_id]
        total_cost = 0.0
        details = {}
        
        price_type = "buy_price_max" if use_buy_price else "sell_price_min"
        
        for ingredient_id, quantity in recipe['ingredients'].items():
            price = get_item_price(ingredient_id, self.prices, self.craft_city, price_type)
            ingredient_cost = price * quantity
            total_cost += ingredient_cost
            
            details[ingredient_id] = {
                'quantity': quantity,
                'unit_price': price,
                'total_cost': ingredient_cost
            }
        
        return total_cost, details
    
    def calculate_craft_cost(
        self,
        potion_id: str,
        quantity: int = 1,
        machine_cost_per_100: float = 0.0,
        focus_bonus: bool = False,
        extra_bonus_pct: float = 0.0,
        return_rate: float = 0.0,
        use_buy_price: bool = False,
        premium: bool = False
    ) -> Dict:
        """
        Розраховує повну вартість крафту зілля
        
        Args:
            potion_id: ID зілля
            quantity: Кількість зілля для крафту (кількість готових зілля, не крафтів)
            machine_cost_per_100: Вартість користування станком за 100 їжі
            focus_bonus: Чи використовується фокус (зменшує витрати на 20%)
            extra_bonus: Чи є додатковий бонус (зменшує витрати на 10%)
            return_rate: Фінальний відсоток повернення ресурсів (0.0 - 1.0), який користувач бачить на станку
            use_buy_price: Використовувати ціну покупки матеріалів
        
        Returns:
            Словник з детальною інформацією про вартість
        """
        if potion_id not in RECIPES:
            return {
                'error': f'Зілля з ID {potion_id} не знайдено!',
                'total_cost': 0.0
            }
        
        recipe = RECIPES[potion_id]
        potion_yield = recipe.get('yield', 1)  # Кількість зілля з одного крафту (за замовчуванням 1)
        
        # Розраховуємо скільки крафтів потрібно зробити
        crafts_needed = (quantity + potion_yield - 1) // potion_yield  # Округлення вгору
        actual_quantity = crafts_needed * potion_yield  # Фактична кількість зілля (може бути більше запитаної)
        
        # Вартість інгредієнтів для одного крафту (БЕЗ урахування повернення)
        ingredient_cost_per_craft_base, ingredient_details_base = self.calculate_ingredient_cost(potion_id, use_buy_price)
        
        # Застосовуємо повернення ресурсів
        # return_rate - це фінальний відсоток, який користувач бачить на станку
        # Тобто, якщо показано 15%, то фактично використовується 85% від базової кількості
        ingredient_cost_per_craft = ingredient_cost_per_craft_base * (1 - return_rate)
        
        # Оновлюємо деталізацію з урахуванням повернення
        ingredient_details = {}
        for ing_id, details in ingredient_details_base.items():
            required_quantity = details['quantity']  # мінімум на один крафт
            net_quantity = required_quantity * (1 - return_rate)  # фактична витрата після повернення
            required_total_quantity = required_quantity * crafts_needed  # що треба мати на руках
            ingredient_details[ing_id] = {
                'quantity': required_quantity,           # базова потреба на 1 крафт
                'net_quantity': net_quantity,            # фактична витрата на 1 крафт після повернення
                'required_total_quantity': required_total_quantity,
                'unit_price': details['unit_price'],
                'total_cost': details['unit_price'] * net_quantity,
                'required_total_cost': details['unit_price'] * required_total_quantity
            }
        
        # Обчислюємо реальну витрату срібла за станок з урахуванням ItemValue
        item_value = self._get_item_value(potion_id)
        if item_value <= 0:
            return {
                'error': f'ItemValue для {potion_id} не знайдено. Додайте його до POTION_ITEM_VALUES.',
                'total_cost': 0.0
            }
        nutrition_cost = item_value * NUTRITION_RATIO
        machine_cost_per_craft = (nutrition_cost / 100.0) * machine_cost_per_100
        
        # Загальна вартість для одного крафту
        cost_per_craft = ingredient_cost_per_craft + machine_cost_per_craft
        
        # Застосовуємо бонуси (вони зменшують витрати)
        focus_multiplier = 0.8 if focus_bonus else 1.0  # Фокус зменшує витрати на 20%
        # Додатковий бонус: користувач вводить відсоток зменшення витрат
        extra_bonus_multiplier = max(0.0, 1.0 - (extra_bonus_pct / 100.0))
        
        # Бонус міста Бресіліон (+15% до виходу зілля, тобто зменшує витрати на зілля)
        # Це означає, що з одного крафту виходить більше зілля, тому вартість на одне зілля зменшується
        brecilien_multiplier = 1.0 / (1.0 + self.brecilien_craft_bonus) if self.brecilien_craft_bonus > 0 else 1.0
        
        cost_per_craft_with_bonuses = cost_per_craft * focus_multiplier * extra_bonus_multiplier
        
        # Загальна вартість для всіх крафтів
        total_cost = cost_per_craft_with_bonuses * crafts_needed
        
        # Вартість одного зілля
        # Якщо є бонус Бресіліону, то з одного крафту виходить більше зілля
        effective_yield = potion_yield * (1.0 + self.brecilien_craft_bonus) if self.brecilien_craft_bonus > 0 else potion_yield
        effective_quantity = crafts_needed * effective_yield
        cost_per_potion = total_cost / effective_quantity if effective_quantity > 0 else 0.0
        
        # Отримуємо ціну продажу зілля
        sell_price = get_item_price(potion_id, self.prices, self.sell_city, "sell_price_min")
        # Розрахунок ринкових зборів: 2.5% за розміщення + 8% податок (4% з преміум)
        effective_sales_tax = self.sales_tax * (0.5 if premium else 1.0)
        listing_fee_per_potion = sell_price * self.listing_fee
        sales_tax_per_potion = sell_price * effective_sales_tax
        sell_price_after_tax = sell_price - sales_tax_per_potion - listing_fee_per_potion
        
        # Прибуток
        profit_per_potion = sell_price_after_tax - cost_per_potion
        total_profit = profit_per_potion * quantity  # Прибуток тільки з запитаної кількості
        
        return {
            'potion_id': potion_id,
            'potion_name': recipe['name'],
            'quantity': quantity,  # Запитана кількість
            'potion_yield': potion_yield,  # Базовий вихід з одного крафту
            'effective_yield': effective_yield,  # Ефективний вихід з урахуванням бонусів міста
            'crafts_needed': crafts_needed,  # Скільки крафтів потрібно
            'actual_quantity': actual_quantity,  # Фактична кількість зілля (може бути більше запитаної)
            'ingredient_cost': ingredient_cost_per_craft * crafts_needed,
            'machine_cost': machine_cost_per_craft * crafts_needed,
            'nutrition_cost': nutrition_cost,
            'cost_per_craft': cost_per_craft_with_bonuses,
            'total_cost': total_cost,
            'cost_per_potion': cost_per_potion,
            'sell_price': sell_price,
            'sell_price_after_tax': sell_price_after_tax,
            'sales_tax_per_potion': sales_tax_per_potion,
            'listing_fee_per_potion': listing_fee_per_potion,
            'profit_per_potion': profit_per_potion,
            'total_profit': total_profit,
            'roi_percent': (profit_per_potion / cost_per_potion * 100) if cost_per_potion > 0 else 0.0,
            'ingredient_details': ingredient_details,
            'settings': {
                'focus_bonus': focus_bonus,
                'extra_bonus_pct': extra_bonus_pct,
                'return_rate': return_rate,
                'brecilien_bonus': self.brecilien_craft_bonus,
                'market_tax': effective_sales_tax,
                'listing_fee': self.listing_fee,
                'premium': premium,
                'craft_city': self.craft_city,
                'sell_city': self.sell_city
            }
        }
    
    def print_calculation_report(self, result: Dict):
        """Виводить звіт про розрахунок"""
        if 'error' in result:
            print(f"Помилка: {result['error']}")
            return
        
        print("\n" + "="*60)
        print(f"Розрахунок для: {result['potion_name']}")
        print("="*60)
        print(f"\nЗапитана кількість: {result['quantity']} зілля")
        print(f"Базовий вихід з одного крафту: {result.get('potion_yield', 1)} зілля")
        if result.get('effective_yield', result.get('potion_yield', 1)) > result.get('potion_yield', 1):
            print(f"Ефективний вихід (з бонусом міста): {result.get('effective_yield', 1):.1f} зілля")
        print(f"Потрібно крафтів: {result.get('crafts_needed', 1)}")
        if result.get('actual_quantity', result['quantity']) > result['quantity']:
            print(f"Фактична кількість: {result.get('actual_quantity', result['quantity'])} зілля (буде зайве)")
        print(f"\n--- Вартість крафту ---")
        print(f"Інгредієнти: {result['ingredient_cost']:.2f} срібла")
        print(f"Станок: {result['machine_cost']:.2f} срібла")
        print(f"Загальна вартість: {result['total_cost']:.2f} срібла")
        print(f"Вартість одного зілля: {result['cost_per_potion']:.2f} срібла")
        
        print(f"\n--- Деталізація інгредієнтів (на 1 крафт) ---")
        for ing_id, details in result['ingredient_details'].items():
            ing_name = MATERIALS_IDS.get(ing_id, ing_id)
            if 'actual_quantity' in details and details['actual_quantity'] != details['quantity']:
                print(f"  {ing_name}: {details['quantity']} → {details['actual_quantity']:.2f} (з поверненням) x {details['unit_price']:.2f} = {details['total_cost']:.2f} срібла")
            else:
                print(f"  {ing_name}: {details['quantity']} x {details['unit_price']:.2f} = {details['total_cost']:.2f} срібла")
        
        print(f"\n--- Продаж ---")
        print(f"Ціна продажу: {result['sell_price']:.2f} срібла")
        print(f"Після всіх зборів: {result['sell_price_after_tax']:.2f} срібла")
        
        print(f"\n--- Прибуток ---")
        profit_color = "✓" if result['profit_per_potion'] > 0 else "✗"
        print(f"Прибуток з одного зілля: {profit_color} {result['profit_per_potion']:.2f} срібла")
        print(f"Загальний прибуток: {profit_color} {result['total_profit']:.2f} срібла")
        print(f"ROI: {result['roi_percent']:.2f}%")
        
        print(f"\n--- Налаштування ---")
        print(f"Місто крафту: {result['settings']['craft_city']}")
        if result['settings'].get('brecilien_bonus', 0) > 0:
            print(f"  → Бонус міста Бресіліон: +{result['settings']['brecilien_bonus']*100:.0f}% до виходу зілля")
        print(f"Місто продажу: {result['settings']['sell_city']}")
        print(f"Фокус: {'Так' if result['settings']['focus_bonus'] else 'Ні'}")
        print(f"Додатковий бонус: {result['settings']['extra_bonus_pct']:.1f}%")
        print(f"Повернення ресурсів (фінальний відсоток): {result['settings']['return_rate']*100:.1f}%")
        print("="*60 + "\n")