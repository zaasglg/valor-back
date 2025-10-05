#!/usr/bin/env python3
"""
Скрипт для настройки webhook Telegram бота
"""

import requests
import os

# Конфигурация бота
BOT_TOKEN = '8468171708:AAFKFJtEGUb-RW2DdiMiU8hNZ_pkffVZSPI'
WEBHOOK_URL = 'https://your-domain.com/api/telegram-webhook/'  # Замените на ваш домен

def set_webhook():
    """Устанавливает webhook для Telegram бота"""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook'
    
    data = {
        'url': WEBHOOK_URL
    }
    
    try:
        response = requests.post(url, data=data)
        result = response.json()
        
        if result.get('ok'):
            print("✅ Webhook установлен успешно!")
            print(f"URL: {WEBHOOK_URL}")
        else:
            print("❌ Ошибка при установке webhook:")
            print(result.get('description', 'Неизвестная ошибка'))
            
    except Exception as e:
        print(f"❌ Ошибка при установке webhook: {e}")

def get_webhook_info():
    """Получает информацию о текущем webhook"""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo'
    
    try:
        response = requests.get(url)
        result = response.json()
        
        if result.get('ok'):
            webhook_info = result.get('result', {})
            print("📋 Информация о webhook:")
            print(f"URL: {webhook_info.get('url', 'Не установлен')}")
            print(f"Pending updates: {webhook_info.get('pending_update_count', 0)}")
            print(f"Last error: {webhook_info.get('last_error_message', 'Нет ошибок')}")
        else:
            print("❌ Ошибка при получении информации о webhook")
            
    except Exception as e:
        print(f"❌ Ошибка при получении информации о webhook: {e}")

def delete_webhook():
    """Удаляет webhook"""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook'
    
    try:
        response = requests.post(url)
        result = response.json()
        
        if result.get('ok'):
            print("✅ Webhook удален успешно!")
        else:
            print("❌ Ошибка при удалении webhook")
            
    except Exception as e:
        print(f"❌ Ошибка при удалении webhook: {e}")

if __name__ == "__main__":
    print("🤖 Настройка Telegram Webhook")
    print("=" * 40)
    
    while True:
        print("\nВыберите действие:")
        print("1. Установить webhook")
        print("2. Получить информацию о webhook")
        print("3. Удалить webhook")
        print("4. Выход")
        
        choice = input("\nВведите номер (1-4): ").strip()
        
        if choice == '1':
            set_webhook()
        elif choice == '2':
            get_webhook_info()
        elif choice == '3':
            delete_webhook()
        elif choice == '4':
            print("👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор. Попробуйте снова.")
