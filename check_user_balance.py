"""
Скрипт для проверки баланса пользователя
"""
import os
import django
import sys

# Настройка Django
sys.path.append('/Users/erdaulet/Documents/django')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Transaction, UserProfile

def check_user_balance():
    """Проверяет баланс пользователя из последней транзакции"""
    
    print("=" * 80)
    print("ПРОВЕРКА БАЛАНСА ПОЛЬЗОВАТЕЛЯ")
    print("=" * 80)
    
    # Находим пользователя с ID 120326
    user_id = '120326'
    
    print(f"\n1. Поиск пользователя с ID: {user_id}")
    
    # Попытка 1: поиск как строка
    user = UserProfile.objects.filter(user_id=user_id).first()
    if not user:
        # Попытка 2: поиск как число
        try:
            user = UserProfile.objects.filter(user_id=int(user_id)).first()
        except (ValueError, TypeError):
            pass
    
    if user:
        print(f"   ✅ Пользователь найден!")
        print(f"   Имя: {user.nombre} {user.apellido}")
        print(f"   Email: {user.email}")
        print(f"   User ID: {user.user_id} (тип: {type(user.user_id).__name__})")
        print(f"   💰 Deposit: {user.deposit}")
        print(f"   🎁 Bonificaciones: {user.bonificaciones}")
    else:
        print(f"   ❌ Пользователь не найден!")
        print(f"\n   Доступные пользователи:")
        for u in UserProfile.objects.all()[:10]:
            print(f"      - ID: {u.user_id} ({type(u.user_id).__name__}), Email: {u.email}")
        return
    
    # Находим транзакции пользователя
    print(f"\n2. Поиск транзакций пользователя:")
    transactions = Transaction.objects.filter(user_id=user_id).order_by('-created_at')[:5]
    
    if transactions:
        print(f"   Найдено транзакций: {transactions.count()}")
        for t in transactions:
            print(f"   - №{t.transaccion_number}: {t.transacciones_monto} {t.currency}, статус: {t.estado}")
    else:
        print(f"   ❌ Транзакции не найдены")
        
        # Пробуем найти с числовым ID
        try:
            transactions = Transaction.objects.filter(user_id=int(user_id)).order_by('-created_at')[:5]
            if transactions:
                print(f"   Найдено транзакций (по числовому ID): {transactions.count()}")
                for t in transactions:
                    print(f"   - №{t.transaccion_number}: {t.transacciones_monto} {t.currency}, статус: {t.estado}")
        except (ValueError, TypeError):
            pass
    
    # Находим ожидающие транзакции
    print(f"\n3. Ожидающие транзакции:")
    pending = Transaction.objects.filter(user_id=user_id, estado='esperando').order_by('-created_at')
    
    if pending:
        print(f"   Найдено ожидающих: {pending.count()}")
        for t in pending:
            print(f"   - №{t.transaccion_number}: {t.transacciones_monto} {t.currency}")
            print(f"     Message ID: {t.message_id}")
            print(f"     Создана: {t.created_at}")
    else:
        print(f"   Нет ожидающих транзакций")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    check_user_balance()
