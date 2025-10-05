#!/usr/bin/env python
"""
Скрипт для тестирования обновления баланса пользователя
"""
import os
import django
import sys

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import UserProfile, Transaction
from decimal import Decimal

def test_balance_update():
    print("=" * 60)
    print("ТЕСТ ОБНОВЛЕНИЯ БАЛАНСА ПОЛЬЗОВАТЕЛЯ")
    print("=" * 60)
    
    # Проверяем последнюю транзакцию
    transaction = Transaction.objects.filter(estado='esperando').order_by('-created_at').first()
    
    if not transaction:
        print("❌ Нет ожидающих транзакций")
        return
    
    print(f"\n📋 Транзакция:")
    print(f"   ID: {transaction.id}")
    print(f"   User ID: {transaction.user_id}")
    print(f"   Сумма: {transaction.transacciones_monto} {transaction.currency}")
    print(f"   Номер: {transaction.transaccion_number}")
    print(f"   Статус: {transaction.estado}")
    print(f"   Message ID: {transaction.message_id}")
    
    # Проверяем пользователя
    user_profile = UserProfile.objects.filter(user_id=transaction.user_id).first()
    
    if not user_profile:
        print(f"\n❌ Пользователь с ID {transaction.user_id} не найден!")
        print("\n🔍 Давайте поищем пользователя другими способами:")
        
        # Попробуем найти по похожему ID
        similar_users = UserProfile.objects.filter(
            user_id__icontains=str(transaction.user_id)[:3]
        )[:5]
        
        if similar_users:
            print(f"\n📋 Найдены похожие пользователи:")
            for u in similar_users:
                print(f"   ID: {u.user_id}, Email: {u.email}, Имя: {u.nombre} {u.apellido}")
        
        return
    
    print(f"\n👤 Пользователь найден:")
    print(f"   ID: {user_profile.user_id}")
    print(f"   Email: {user_profile.email}")
    print(f"   Имя: {user_profile.nombre} {user_profile.apellido}")
    print(f"   Текущий deposit: {user_profile.deposit}")
    print(f"   Текущий bonificaciones: {user_profile.bonificaciones}")
    
    # Симулируем обновление баланса
    print(f"\n💰 Симуляция пополнения баланса:")
    new_deposit = user_profile.deposit + transaction.transacciones_monto
    print(f"   Deposit: {user_profile.deposit} + {transaction.transacciones_monto} = {new_deposit}")
    
    answer = input("\n❓ Хотите реально обновить баланс? (yes/no): ")
    
    if answer.lower() == 'yes':
        old_deposit = user_profile.deposit
        user_profile.deposit += transaction.transacciones_monto
        user_profile.save()
        
        print(f"\n✅ Баланс обновлен!")
        print(f"   Было: {old_deposit}")
        print(f"   Стало: {user_profile.deposit}")
        
        # Обновляем статус транзакции
        transaction.estado = 'aprobado'
        transaction.save()
        print(f"\n✅ Статус транзакции изменен на 'aprobado'")
    else:
        print("\n⏭️  Пропущено")

if __name__ == '__main__':
    test_balance_update()
