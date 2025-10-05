"""
Скрипт для тестирования обработки одобрения платежей через Telegram webhook
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

def test_approval_process():
    """Тестирует процесс одобрения платежа"""
    
    print("=" * 80)
    print("ТЕСТ ПРОЦЕССА ОДОБРЕНИЯ ПЛАТЕЖА")
    print("=" * 80)
    
    # 1. Находим ожидающую транзакцию
    print("\n1. Поиск ожидающих транзакций...")
    pending_transactions = Transaction.objects.filter(estado='esperando').order_by('-created_at')
    
    if not pending_transactions.exists():
        print("   ❌ Нет ожидающих транзакций")
        print("\n   Создаём тестовую транзакцию...")
        
        # Находим пользователя или создаём тестового
        user = UserProfile.objects.first()
        if not user:
            print("   ❌ Нет пользователей в базе")
            return
        
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
            message_id='12345'
        )
        print(f"   ✅ Создана тестовая транзакция: {transaction.transaccion_number}")
    else:
        transaction = pending_transactions.first()
        print(f"   ✅ Найдена транзакция: {transaction.transaccion_number}")
    
    # 2. Получаем информацию о пользователе
    print(f"\n2. Информация о транзакции:")
    print(f"   User ID: {transaction.user_id}")
    print(f"   Сумма: {transaction.transacciones_monto} {transaction.currency}")
    print(f"   Статус: {transaction.estado}")
    print(f"   Message ID: {transaction.message_id}")
    
    user = UserProfile.objects.filter(user_id=transaction.user_id).first()
    if user:
        print(f"\n3. Информация о пользователе:")
        print(f"   Имя: {user.nombre} {user.apellido}")
        print(f"   Email: {user.email}")
        print(f"   Баланс ДО: {user.deposit}")
    else:
        print(f"\n3. ❌ Пользователь не найден!")
        return
    
    # 4. Симулируем одобрение
    print(f"\n4. Симуляция одобрения транзакции...")
    bot = TelegramBot()
    
    # Тест с message_id
    print(f"   Тест 1: Одобрение с message_id = {transaction.message_id}")
    success = bot.process_approval_response(transaction.message_id, '+', 'test_admin')
    
    if success:
        print(f"   ✅ Транзакция одобрена успешно")
        
        # Обновляем данные пользователя
        user.refresh_from_db()
        print(f"   Баланс ПОСЛЕ: {user.deposit}")
        print(f"   Изменение: +{transaction.transacciones_monto}")
        
        # Обновляем данные транзакции
        transaction.refresh_from_db()
        print(f"   Статус транзакции: {transaction.estado}")
        print(f"   Обработано: {transaction.processed_at}")
        print(f"   Кем обработано: {transaction.processed_by}")
    else:
        print(f"   ❌ Не удалось одобрить транзакцию")
    
    print("\n" + "=" * 80)

def test_approval_without_reply():
    """Тестирует одобрение без reply_to_message (просто отправка +)"""
    
    print("=" * 80)
    print("ТЕСТ ОДОБРЕНИЯ БЕЗ REPLY (ПРОСТО +)")
    print("=" * 80)
    
    # Создаём новую тестовую транзакцию
    user = UserProfile.objects.first()
    if not user:
        print("❌ Нет пользователей в базе")
        return
    
    bot = TelegramBot()
    transaction = Transaction.objects.create(
        user_id=str(user.user_id),
        transacciones_data=datetime.now(),
        transacciones_monto=50.00,
        estado='esperando',
        transaccion_number=bot.generate_transaction_number(),
        metodo_de_pago='Test',
        currency='USD',
        exchange_rate=1.0,
        file_name='test_receipt2.jpg',
        chat_id=bot.chat_id,
        message_id='67890'
    )
    
    print(f"\n1. Создана тестовая транзакция: {transaction.transaccion_number}")
    print(f"   User ID: {transaction.user_id}")
    print(f"   Сумма: {transaction.transacciones_monto} {transaction.currency}")
    
    old_balance = user.deposit
    print(f"   Баланс ДО: {old_balance}")
    
    # Тестируем одобрение БЕЗ message_id (симуляция, когда админ просто отправляет +)
    print(f"\n2. Симуляция одобрения БЕЗ message_id (как если бы админ просто написал +)")
    success = bot.process_approval_response(None, '+', 'test_admin')
    
    if success:
        print(f"   ✅ Транзакция одобрена успешно")
        
        user.refresh_from_db()
        print(f"   Баланс ПОСЛЕ: {user.deposit}")
        print(f"   Изменение: +{user.deposit - old_balance}")
        
        transaction.refresh_from_db()
        print(f"   Статус: {transaction.estado}")
    else:
        print(f"   ❌ Не удалось одобрить транзакцию")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'without-reply':
        test_approval_without_reply()
    else:
        test_approval_process()
        print("\n\nДля теста без reply выполните: python test_telegram_approval.py without-reply")
