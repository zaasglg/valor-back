"""
Скрипт для тестирования установки флага first_bonus_used при первом пополнении
"""
import os
import django
import sys

# Настройка Django
sys.path.append('/Users/erdaulet/Documents/django')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Transaction, UserProfile
from api.telegram_bot import TelegramBot
from datetime import datetime

def test_first_bonus_flag():
    """Тестирует установку флага first_bonus_used при первом пополнении"""
    
    print("=" * 80)
    print("ТЕСТ УСТАНОВКИ ФЛАГА first_bonus_used")
    print("=" * 80)
    
    # Находим пользователя с first_bonus_used = False или создаём нового
    user = UserProfile.objects.filter(first_bonus_used=False).first()
    
    if not user:
        print("\n❌ Нет пользователей с first_bonus_used = False")
        print("Создайте нового пользователя для теста")
        return
    
    print(f"\n1. Информация о пользователе:")
    print(f"   User ID: {user.user_id}")
    print(f"   Email: {user.email}")
    print(f"   Имя: {user.nombre} {user.apellido}")
    print(f"   Баланс: {user.deposit}")
    print(f"   First bonus used: {user.first_bonus_used}")
    
    # Проверяем количество одобренных транзакций
    approved_count = Transaction.objects.filter(
        user_id=str(user.user_id),
        estado='aprobado'
    ).count()
    print(f"   Одобренных транзакций: {approved_count}")
    
    # Создаём тестовую транзакцию
    print(f"\n2. Создание тестовой транзакции...")
    bot = TelegramBot()
    transaction = Transaction.objects.create(
        user_id=str(user.user_id),
        transacciones_data=datetime.now(),
        transacciones_monto=100.00,
        estado='esperando',
        transaccion_number=bot.generate_transaction_number(),
        metodo_de_pago='Test',
        currency='USD',
        exchange_rate=1.0,
        file_name='test_receipt.jpg',
        chat_id=bot.chat_id,
        message_id='test_message_123'
    )
    print(f"   ✅ Создана транзакция: {transaction.transaccion_number}")
    print(f"   Сумма: {transaction.transacciones_monto} {transaction.currency}")
    
    # Симулируем одобрение
    print(f"\n3. Симуляция одобрения транзакции...")
    old_balance = user.deposit
    old_first_bonus_used = user.first_bonus_used
    
    success = bot.process_approval_response(transaction.message_id, '+', 'test_admin')
    
    if success:
        # Обновляем данные пользователя
        user.refresh_from_db()
        
        print(f"\n4. Результаты:")
        print(f"   ✅ Транзакция одобрена успешно")
        print(f"   Баланс: {old_balance} -> {user.deposit} (+{transaction.transacciones_monto})")
        print(f"   First bonus used: {old_first_bonus_used} -> {user.first_bonus_used}")
        
        # Обновляем данные транзакции
        transaction.refresh_from_db()
        print(f"\n5. Статус транзакции:")
        print(f"   Статус: {transaction.estado}")
        print(f"   Обработано: {transaction.processed_at}")
        print(f"   Кем: {transaction.processed_by}")
        
        # Проверяем логику
        new_approved_count = Transaction.objects.filter(
            user_id=str(user.user_id),
            estado='aprobado'
        ).count()
        print(f"\n6. Проверка логики:")
        print(f"   Было одобренных транзакций: {approved_count}")
        print(f"   Стало одобренных транзакций: {new_approved_count}")
        
        if new_approved_count == 1 and user.first_bonus_used:
            print(f"   ✅ Флаг first_bonus_used установлен правильно!")
        elif new_approved_count > 1 and not user.first_bonus_used:
            print(f"   ⚠️  У пользователя уже были одобренные транзакции, но флаг не был установлен ранее")
        elif new_approved_count > 1 and user.first_bonus_used:
            print(f"   ✅ Флаг уже был установлен ранее (это не первое пополнение)")
    else:
        print(f"   ❌ Не удалось одобрить транзакцию")
    
    print("\n" + "=" * 80)

def show_all_users_status():
    """Показывает статус first_bonus_used для всех пользователей"""
    
    print("=" * 80)
    print("СТАТУС first_bonus_used ДЛЯ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ")
    print("=" * 80)
    
    users = UserProfile.objects.all()
    
    for user in users:
        approved_count = Transaction.objects.filter(
            user_id=str(user.user_id),
            estado='aprobado'
        ).count()
        
        print(f"\nUser ID: {user.user_id}")
        print(f"  Email: {user.email}")
        print(f"  Баланс: {user.deposit}")
        print(f"  First bonus used: {user.first_bonus_used}")
        print(f"  Одобренных транзакций: {approved_count}")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        show_all_users_status()
    else:
        test_first_bonus_flag()
        print("\nДля просмотра статуса всех пользователей выполните:")
        print("python test_first_bonus.py status")
