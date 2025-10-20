#!/usr/bin/env python3
"""
Менеджер Telegram Webhook - упрощенная утилита для управления webhook
"""

import requests
import sys
from colorama import init, Fore, Style

# Инициализация colorama для цветного вывода
init(autoreset=True)

# Конфигурация
BOT_TOKEN = '8468171708:AAFKFJtEGUb-RW2DdiMiU8hNZ_pkffVZSPI'
WEBHOOK_URL = 'https://api.valor-games.co/api/telegram-webhook/'
BASE_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'


def print_success(message):
    """Выводит сообщение об успехе"""
    print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")


def print_error(message):
    """Выводит сообщение об ошибке"""
    print(f"{Fore.RED}❌ {message}{Style.RESET_ALL}")


def print_info(message):
    """Выводит информационное сообщение"""
    print(f"{Fore.CYAN}ℹ️  {message}{Style.RESET_ALL}")


def print_warning(message):
    """Выводит предупреждение"""
    print(f"{Fore.YELLOW}⚠️  {message}{Style.RESET_ALL}")


def get_webhook_info():
    """Получает и отображает информацию о webhook"""
    try:
        response = requests.get(f'{BASE_URL}/getWebhookInfo')
        result = response.json()
        
        if result.get('ok'):
            webhook_info = result.get('result', {})
            
            print("\n" + "="*60)
            print(f"{Fore.CYAN}📋 ИНФОРМАЦИЯ О WEBHOOK{Style.RESET_ALL}")
            print("="*60)
            
            url = webhook_info.get('url', 'Не установлен')
            if url:
                print_success(f"URL: {url}")
            else:
                print_error("URL: Не установлен")
            
            pending = webhook_info.get('pending_update_count', 0)
            if pending > 0:
                print_warning(f"Ожидающие обновления: {pending}")
            else:
                print_success(f"Ожидающие обновления: {pending}")
            
            last_error = webhook_info.get('last_error_message')
            if last_error:
                print_error(f"Последняя ошибка: {last_error}")
                last_error_date = webhook_info.get('last_error_date')
                if last_error_date:
                    from datetime import datetime
                    error_time = datetime.fromtimestamp(last_error_date)
                    print_info(f"Время ошибки: {error_time.strftime('%d.%m.%Y %H:%M:%S')}")
            else:
                print_success("Ошибок нет")
            
            print_info(f"Max connections: {webhook_info.get('max_connections', 40)}")
            
            ip_address = webhook_info.get('ip_address')
            if ip_address:
                print_info(f"IP адрес: {ip_address}")
            
            print("="*60 + "\n")
            return True
        else:
            print_error("Не удалось получить информацию о webhook")
            return False
            
    except Exception as e:
        print_error(f"Ошибка при получении информации: {e}")
        return False


def set_webhook(drop_pending=False):
    """Устанавливает webhook"""
    try:
        params = {'url': WEBHOOK_URL}
        if drop_pending:
            params['drop_pending_updates'] = 'true'
        
        response = requests.post(f'{BASE_URL}/setWebhook', data=params)
        result = response.json()
        
        if result.get('ok'):
            print_success("Webhook установлен успешно!")
            print_info(f"URL: {WEBHOOK_URL}")
            if drop_pending:
                print_info("Ожидающие обновления очищены")
            return True
        else:
            print_error("Ошибка при установке webhook:")
            print_error(result.get('description', 'Неизвестная ошибка'))
            return False
            
    except Exception as e:
        print_error(f"Ошибка при установке webhook: {e}")
        return False


def delete_webhook(drop_pending=False):
    """Удаляет webhook"""
    try:
        params = {}
        if drop_pending:
            params['drop_pending_updates'] = 'true'
        
        response = requests.post(f'{BASE_URL}/deleteWebhook', data=params)
        result = response.json()
        
        if result.get('ok'):
            print_success("Webhook удален успешно!")
            if drop_pending:
                print_info("Ожидающие обновления очищены")
            return True
        else:
            print_error("Ошибка при удалении webhook")
            return False
            
    except Exception as e:
        print_error(f"Ошибка при удалении webhook: {e}")
        return False


def reset_webhook():
    """Полная переустановка webhook с очисткой ошибок"""
    print_info("Начинаем переустановку webhook...")
    
    # Удаляем старый webhook с очисткой
    if delete_webhook(drop_pending=True):
        print_info("Пауза 2 секунды...")
        import time
        time.sleep(2)
        
        # Устанавливаем новый webhook
        if set_webhook(drop_pending=True):
            print_success("Webhook успешно переустановлен!")
            print_info("Проверяем статус...")
            time.sleep(1)
            get_webhook_info()
            return True
    
    print_error("Не удалось переустановить webhook")
    return False


def test_webhook():
    """Отправляет тестовое сообщение для проверки webhook"""
    try:
        # Получаем информацию о боте
        response = requests.get(f'{BASE_URL}/getMe')
        result = response.json()
        
        if result.get('ok'):
            bot_info = result.get('result', {})
            print_success(f"Бот: @{bot_info.get('username', 'N/A')}")
            print_info(f"ID: {bot_info.get('id', 'N/A')}")
            print_info(f"Имя: {bot_info.get('first_name', 'N/A')}")
            return True
        else:
            print_error("Не удалось получить информацию о боте")
            return False
            
    except Exception as e:
        print_error(f"Ошибка при тестировании: {e}")
        return False


def main():
    """Главная функция"""
    print(f"\n{Fore.BLUE}{'='*60}")
    print(f"{Fore.BLUE}🤖 TELEGRAM WEBHOOK MANAGER")
    print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}\n")
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'info':
            get_webhook_info()
        elif command == 'set':
            set_webhook()
        elif command == 'delete':
            delete_webhook()
        elif command == 'reset':
            reset_webhook()
        elif command == 'test':
            test_webhook()
        else:
            print_error(f"Неизвестная команда: {command}")
            print_usage()
    else:
        # Интерактивный режим
        while True:
            print("\n" + "="*60)
            print(f"{Fore.CYAN}Выберите действие:{Style.RESET_ALL}")
            print("1. 📋 Получить информацию о webhook")
            print("2. ✅ Установить webhook")
            print("3. 🔄 Переустановить webhook (рекомендуется)")
            print("4. ❌ Удалить webhook")
            print("5. 🧪 Тест бота")
            print("6. 🚪 Выход")
            print("="*60)
            
            choice = input(f"\n{Fore.YELLOW}Введите номер (1-6): {Style.RESET_ALL}").strip()
            
            if choice == '1':
                get_webhook_info()
            elif choice == '2':
                set_webhook()
            elif choice == '3':
                reset_webhook()
            elif choice == '4':
                delete_webhook()
            elif choice == '5':
                test_webhook()
            elif choice == '6':
                print_success("До свидания!")
                break
            else:
                print_error("Неверный выбор. Попробуйте снова.")


def print_usage():
    """Выводит справку по использованию"""
    print(f"""
{Fore.CYAN}Использование:{Style.RESET_ALL}
    python webhook_manager.py [command]

{Fore.CYAN}Команды:{Style.RESET_ALL}
    info    - Получить информацию о webhook
    set     - Установить webhook
    reset   - Переустановить webhook (с очисткой)
    delete  - Удалить webhook
    test    - Тест бота
    
{Fore.CYAN}Примеры:{Style.RESET_ALL}
    python webhook_manager.py info
    python webhook_manager.py reset
    python webhook_manager.py
    """)


if __name__ == "__main__":
    try:
        # Проверяем установлен ли colorama
        try:
            from colorama import init, Fore, Style
        except ImportError:
            print("⚠️  Для цветного вывода установите colorama: pip install colorama")
            print("Продолжаем без цветов...\n")
            # Создаем заглушки
            class DummyColor:
                def __getattr__(self, name):
                    return ''
            Fore = Style = DummyColor()
        
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}⚠️  Прервано пользователем{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}❌ Критическая ошибка: {e}{Style.RESET_ALL}")
        sys.exit(1)
