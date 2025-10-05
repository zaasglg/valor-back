import requests
import os
from django.conf import settings
from .models import Transaction, UserProfile
from datetime import datetime
import random

class TelegramBot:
    def __init__(self):
        self.bot_token = '8468171708:AAFKFJtEGUb-RW2DdiMiU8hNZ_pkffVZSPI'
        self.chat_id = '-1002909289551'
        self.base_url = f'https://api.telegram.org/bot{self.bot_token}'
    
    def send_receipt_notification(self, transaction):
        """Отправляет уведомление о новом чеке в Telegram чат"""
        try:
            # Получаем информацию о пользователе
            user_profile = UserProfile.objects.filter(user_id=transaction.user_id).first()
            user_name = f"{user_profile.nombre} {user_profile.apellido}" if user_profile else "Usuario"
            
            # Формируем сообщение
            message = f"""🆕 Nuevo cheque subido
👤 Usuario: {transaction.user_id}
💰 Monto: {transaction.transacciones_monto} {transaction.currency}
🔢 N° Transacción: №{transaction.transaccion_number}
📅 Fecha: {transaction.transacciones_data.strftime('%d.%m.%Y %H:%M:%S')}
📁 Archivo: {transaction.file_name}
🧩 Chat_id: {transaction.chat_id}

Responde con + para aprobar o - para rechazar"""
            
            # Отправляем сообщение
            url = f'{self.base_url}/sendMessage'
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    # Сохраняем message_id в транзакции
                    transaction.message_id = str(result['result']['message_id'])
                    transaction.save()
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error sending telegram notification: {e}")
            return False
    
    def send_receipt_with_image_from_file(self, transaction, image_file):
        """Отправляет чек с изображением в Telegram чат напрямую из файла (без сохранения в базе)"""
        try:
            # Получаем информацию о пользователе
            user_profile = UserProfile.objects.filter(user_id=transaction.user_id).first()
            user_name = f"{user_profile.nombre} {user_profile.apellido}" if user_profile else "Usuario"
            
            # Формируем сообщение
            caption = f"""🆕 Nuevo cheque subido
👤 Usuario: {transaction.user_id}
💰 Monto: {transaction.transacciones_monto} {transaction.currency}
🔢 N° Transacción: №{transaction.transaccion_number}
📅 Fecha: {transaction.transacciones_data.strftime('%d.%m.%Y %H:%M:%S')}
📁 Archivo: {transaction.file_name}
🧩 Chat_id: {transaction.chat_id}

Responde con + para aprobar o - para rechazar"""
            
            # Отправляем фото с подписью
            url = f'{self.base_url}/sendPhoto'
            
            # Используем файл напрямую, без сохранения на диск
            files = {'photo': image_file}
            data = {
                'chat_id': self.chat_id,
                'caption': caption,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    # Сохраняем message_id в транзакции
                    transaction.message_id = str(result['result']['message_id'])
                    transaction.save()
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error sending telegram photo: {e}")
            return False
    
    def process_approval_response(self, message_id, response_text, user_id):
        """Обрабатывает ответ на одобрение/отклонение платежа"""
        try:
            print(f"🔍 Looking for transaction with message_id: {message_id}")
            
            # Находим транзакцию по message_id
            transaction = Transaction.objects.filter(message_id=str(message_id)).first()
            
            if not transaction:
                print(f"❌ Transaction not found for message_id: {message_id}")
                
                # Попробуем найти последнюю транзакцию в статусе 'esperando'
                transaction = Transaction.objects.filter(estado='esperando').order_by('-created_at').first()
                if transaction:
                    print(f"🔄 Found pending transaction: {transaction.transaccion_number}")
                    # Обновляем message_id для этой транзакции
                    transaction.message_id = str(message_id)
                    transaction.save()
                else:
                    print(f"❌ No pending transactions found")
                    return False
            
            print(f"✅ Found transaction: {transaction.transaccion_number}, status: {transaction.estado}")
            
            # Проверяем, что транзакция еще не обработана
            if transaction.estado != 'esperando':
                print(f"❌ Transaction already processed: {transaction.estado}")
                return False
            
            # Обрабатываем ответ
            if response_text.strip() == '+':
                print(f"✅ Approving transaction: {transaction.transaccion_number}")
                
                # Одобряем платеж
                transaction.estado = 'aprobado'
                transaction.processed_at = datetime.now()
                transaction.processed_by = str(user_id)
                transaction.save()
                
                # Пополняем счет пользователя
                user_profile = UserProfile.objects.filter(user_id=transaction.user_id).first()
                if user_profile:
                    old_balance = user_profile.deposit
                    user_profile.deposit += transaction.transacciones_monto
                    user_profile.save()
                    print(f"💰 Balance updated: {old_balance} -> {user_profile.deposit}")
                else:
                    print(f"❌ User profile not found for user_id: {transaction.user_id}")
                
                # Отправляем подтверждение
                self.send_confirmation_message(transaction, 'approved')
                print(f"📱 Confirmation message sent")
                return True
                
            elif response_text.strip() == '-':
                print(f"❌ Rejecting transaction: {transaction.transaccion_number}")
                
                # Отклоняем платеж
                transaction.estado = 'rechazado'
                transaction.processed_at = datetime.now()
                transaction.processed_by = str(user_id)
                transaction.save()
                
                # Отправляем подтверждение
                self.send_confirmation_message(transaction, 'rejected')
                print(f"📱 Rejection message sent")
                return True
            
            print(f"❌ Invalid response text: '{response_text}'")
            return False
            
        except Exception as e:
            print(f"❌ Error processing approval response: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_confirmation_message(self, transaction, status):
        """Отправляет подтверждение об обработке платежа"""
        try:
            status_text = "✅ APROBADO" if status == 'approved' else "❌ RECHAZADO"
            
            message = f"""{status_text}
👤 Usuario: {transaction.user_id}
💰 Monto: {transaction.transacciones_monto} {transaction.currency}
🔢 N° Transacción: №{transaction.transaccion_number}
📅 Procesado: {transaction.processed_at.strftime('%d.%m.%Y %H:%M:%S')}
👨‍💼 Por: {transaction.processed_by}"""
            
            url = f'{self.base_url}/sendMessage'
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            requests.post(url, data=data)
            
        except Exception as e:
            print(f"Error sending confirmation: {e}")
    
    def generate_transaction_number(self):
        """Генерирует уникальный номер транзакции"""
        while True:
            number = random.randint(100000000, 999999999)
            if not Transaction.objects.filter(transaccion_number=str(number)).exists():
                return str(number)
