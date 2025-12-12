from calculator import PotionCalculator
from potion import POTION_IDS
from get_prices import get_prices

# Список доступних міст
CITIES = [
    "Caerleon",
    "Bridgewatch",
    "Lymhurst",
    "Martlock",
    "FortSterling",
    "Thetford",
    "Brecilien"  # ДОДАНО: Бресіліон
]

def select_city(prompt: str) -> str:
    """Вибір міста зі списку"""
    print(f"\n{prompt}")
    for idx, city in enumerate(CITIES, 1):
        print(f"{idx}. {city}")
    
    while True:
        try:
            choice = input("Виберіть номер міста: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(CITIES):
                return CITIES[idx]
            else:
                print("Невірний номер. Спробуйте ще раз.")
        except ValueError:
            print("Введіть число.")

def select_potion():
    """Вибір зілля для крафту"""
    print("\nДоступні зілля:")
    potion_list = list(POTION_IDS.items())
    for idx, (potion_id, potion_name) in enumerate(potion_list, 1):
        print(f"{idx}. {potion_name} ({potion_id})")
    
    while True:
        try:
            choice = input("\nВиберіть номер зілля: ")
            idx = int(choice) - 1
            if 0 <= idx < len(potion_list):
                return potion_list[idx][0]
            else:
                print("Невірний номер. Спробуйте ще раз.")
        except ValueError:
            print("Введіть число.")

def get_user_settings():
    """Отримує налаштування від користувача"""
    print("\n--- Налаштування крафту ---")
    
    craft_city = select_city("Місто для крафту:")
    sell_city = select_city("Місто для продажу:")
    default_return_rate = 24.8 if craft_city == "Brecilien" else 15.2
    
    while True:
        try:
            quantity = int(input("\nКількість зілля для крафту: "))
            if quantity > 0:
                break
            else:
                print("Кількість повинна бути більше 0.")
        except ValueError:
            print("Введіть число.")
    
    while True:
        try:
            machine_cost_input = input("Вартість користування станком за 100 їжі [0]: ").strip() or "0"
            machine_cost = float(machine_cost_input)
            if machine_cost >= 0:
                break
            else:
                print("Вартість не може бути від'ємною.")
        except ValueError:
            print("Введіть число.")
    
    focus_bonus = input("Використовувати фокус? (так/ні) [ні]: ").strip().lower() == 'так'
    extra_bonus = input("Є додатковий бонус? (так/ні) [ні]: ").strip().lower() == 'так'
    extra_bonus_pct = 0.0
    if extra_bonus:
        while True:
            try:
                extra_bonus_pct = float(input("Вкажіть відсоток додаткового бонусу (0-100): ").strip() or "0")
                if 0 <= extra_bonus_pct <= 100:
                    break
                else:
                    print("Відсоток повинен бути від 0 до 100.")
            except ValueError:
                print("Введіть число.")
    premium = input("Преміум акаунт? (так/ні) [ні]: ").strip().lower() == 'так'
    
    while True:
        try:
            prompt = f"Фінальний відсоток повернення ресурсів (як на станку, 0-100) [{default_return_rate}]: "
            return_rate_in = input(prompt).strip() or str(default_return_rate)
            return_rate = float(return_rate_in) / 100.0
            if 0 <= return_rate <= 1:
                break
            else:
                print("Відсоток повинен бути від 0 до 100.")
        except ValueError:
            print("Введіть число.")
    
    return {
        'craft_city': craft_city,
        'sell_city': sell_city,
        'quantity': quantity,
        'machine_cost': machine_cost,  # Тепер це вартість за 100 їжі
        'focus_bonus': focus_bonus,
        'extra_bonus_pct': extra_bonus_pct,
        'return_rate': return_rate,
        'premium': premium
    }

def main():
    """Головна функція"""
    print("="*60)
    print("Albion Online - Калькулятор вартості крафту зілля")
    print("="*60)
    
    # Завантажуємо ціни
    print("\nЗавантаження цін...")
    prices = get_prices()
    
    if not prices:
        print("Помилка: не вдалося завантажити ціни. Перевірте підключення до інтернету.")
        return
    
    # Отримуємо налаштування
    settings = get_user_settings()
    
    # Створюємо калькулятор
    calculator = PotionCalculator(
        prices=prices,
        craft_city=settings['craft_city'],
        sell_city=settings['sell_city']
    )
    
    # Вибір зілля
    potion_id = select_potion()
    
    # Розрахунок
    result = calculator.calculate_craft_cost(
        potion_id=potion_id,
        quantity=settings['quantity'],
        machine_cost_per_100=settings['machine_cost'],  # ЗМІНА: передаємо як вартість за 100 їжі
        focus_bonus=settings['focus_bonus'],
            extra_bonus_pct=settings['extra_bonus_pct'],
            return_rate=settings['return_rate'],
            premium=settings['premium']
    )
    
    # Виведення результату
    calculator.print_calculation_report(result)
    
    # Можливість розрахувати ще одне зілля
    while True:
        again = input("Розрахувати ще одне зілля? (так/ні): ").strip().lower()
        if again == 'так':
            potion_id = select_potion()
            result = calculator.calculate_craft_cost(
                potion_id=potion_id,
                quantity=settings['quantity'],
                machine_cost_per_100=settings['machine_cost'],
                focus_bonus=settings['focus_bonus'],
                extra_bonus_pct=settings['extra_bonus_pct'],
                return_rate=settings['return_rate'],
                premium=settings['premium']
            )
            calculator.print_calculation_report(result)
        elif again == 'ні':
            break
        else:
            print("Введіть 'так' або 'ні'.")

if __name__ == "__main__":
    main()