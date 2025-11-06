from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from .models import UserProfile, HistorialPagos, Transaction
from .serializers import UserRegisterSerializer, CountrySerializer, TransactionSerializer, UserProfileUpdateSerializer, HistorialPagosSerializer, DepositUpdateSerializer, UserLookupSerializer
from .telegram_bot import TelegramBot
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import os
import decimal
import requests
# API: List historial pagos for authenticated user only
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def historial_pagos_list(request):
	# Get user profile to access user_id
	try:
		user_profile = UserProfile.objects.get(django_user=request.user)
		user_id = str(user_profile.user_id)
	except UserProfile.DoesNotExist:
		return Response({"error": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)
	
	# Filter pagos by user_id
	pagos = HistorialPagos.objects.filter(user_id=user_id).order_by('-transacciones_data')
	serializer = HistorialPagosSerializer(pagos, many=True)
	return Response(serializer.data)

# API: Create historial pago
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def historial_pagos_create(request):
	# Get user profile to access user_id
	try:
		user_profile = UserProfile.objects.get(django_user=request.user)
		user_id = str(user_profile.user_id)
	except UserProfile.DoesNotExist:
		return Response({"error": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)
	
	# Get withdrawal amount from request
	withdrawal_amount = request.data.get('transacciones_monto')
	if not withdrawal_amount:
		return Response({"error": "Withdrawal amount is required."}, status=status.HTTP_400_BAD_REQUEST)
	
	try:
		from decimal import Decimal
		withdrawal_amount = Decimal(str(withdrawal_amount))
		if withdrawal_amount <= 0:
			return Response({"error": "Withdrawal amount must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)
	except (ValueError, TypeError, decimal.InvalidOperation):
		return Response({"error": "Invalid withdrawal amount format."}, status=status.HTTP_400_BAD_REQUEST)
	
	if user_profile.deposit < withdrawal_amount:
		return Response({
			"error": "Insufficient balance",
			"message": f"Your current balance is ${user_profile.deposit}. You cannot withdraw ${withdrawal_amount}."
		}, status=status.HTTP_400_BAD_REQUEST)
	
	# Add user_id to request data
	data = request.data.copy()
	data['user_id'] = user_id
	
	serializer = HistorialPagosSerializer(data=data)
	if serializer.is_valid():
		# Save the withdrawal record. If client didn't provide transacciones_data,
		# set it to now so we can expire requests after 1 minute.
		from datetime import datetime
		if not data.get('transacciones_data'):
			historial_pago = serializer.save(transacciones_data=datetime.now())
		else:
			historial_pago = serializer.save()
		
		# Deduct amount from user's deposit
		user_profile.deposit -= withdrawal_amount
		user_profile.save()
		
		# Return response with updated balance
		response_data = serializer.data.copy()
		response_data['previous_balance'] = str(user_profile.deposit + withdrawal_amount)
		response_data['new_balance'] = str(user_profile.deposit)
		response_data['withdrawal_amount'] = str(withdrawal_amount)
		
		return Response(response_data, status=status.HTTP_201_CREATED)
	return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# API endpoint to update user profile (authenticated user updates their own profile)
@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_profile(request):
	user = request.user
	try:
		profile = UserProfile.objects.get(django_user=user)
	except UserProfile.DoesNotExist:
		return Response({"error": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)

	serializer = UserProfileUpdateSerializer(profile, data=request.data, partial=True)
	if serializer.is_valid():
		serializer.save()
		return Response(serializer.data)
	return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
from rest_framework.permissions import AllowAny
from rest_framework import status
from .models import UserProfile
from .serializers import UserRegisterSerializer, CountrySerializer, TransactionSerializer
# ...existing code...

from .models import Transaction

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def transactions_list(request):
	# Get user profile to access user_id
	try:
		user_profile = UserProfile.objects.get(django_user=request.user)
		user_id = str(user_profile.user_id)
	except UserProfile.DoesNotExist:
		return Response({"error": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)
	
	# Filter transactions by user_id
	transactions = Transaction.objects.filter(user_id=user_id).order_by('-created_at')
	serializer = TransactionSerializer(transactions, many=True)
	return Response(serializer.data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def transaction_create(request):
	"""Создает транзакцию с возможностью загрузки чека и отправки в Telegram"""
	# Get user profile to access user_id
	try:
		user_profile = UserProfile.objects.get(django_user=request.user)
		user_id = str(user_profile.user_id)
	except UserProfile.DoesNotExist:
		return Response({"error": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)
	
	# Проверяем, есть ли файл чека
	receipt_image = request.FILES.get('receipt_image')
	
	if receipt_image:
		# Если есть чек, создаем транзакцию с чеком и отправляем в Telegram
		transacciones_monto = request.data.get('transacciones_monto')
		currency = request.data.get('currency', 'COP')
		metodo_de_pago = request.data.get('metodo_de_pago', '')
		amount_usd = request.data.get('amount_usd')
		exchange_rate = request.data.get('exchange_rate', 1.0)
		
		if not transacciones_monto:
			return Response({"error": "transacciones_monto is required when uploading receipt."}, status=status.HTTP_400_BAD_REQUEST)
		
		try:
			from decimal import Decimal
			transacciones_monto = Decimal(str(transacciones_monto))
			if transacciones_monto <= 0:
				return Response({"error": "Amount must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)
		except (ValueError, TypeError, decimal.InvalidOperation):
			return Response({"error": "Invalid amount format."}, status=status.HTTP_400_BAD_REQUEST)
		
		# Создаем транзакцию с чеком
		bot = TelegramBot()
		transaction_number = bot.generate_transaction_number()
		
		# Генерируем имя файла
		from datetime import datetime
		timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3] + 'Z'
		file_extension = os.path.splitext(receipt_image.name)[1]
		file_name = f"{user_id}_{timestamp}{file_extension}"
		
		# Создаем транзакцию (БЕЗ сохранения изображения в базе)
		transaction = Transaction.objects.create(
			user_id=user_id,
			transacciones_data=datetime.now(),
			transacciones_monto=transacciones_monto,
			estado='esperando',
			transaccion_number=transaction_number,
			metodo_de_pago=metodo_de_pago,
			amount_usd=amount_usd,
			currency=currency,
			exchange_rate=exchange_rate,
			file_name=file_name,
			chat_id=bot.chat_id
		)
		
		# Отправляем изображение в Telegram (без сохранения в базе)
		success = bot.send_receipt_with_image_from_file(transaction, receipt_image)
		
		if success:
			serializer = TransactionSerializer(transaction)
			response_data = serializer.data.copy()
			response_data['telegram_sent'] = True
			response_data['message'] = 'Receipt uploaded and sent to Telegram successfully'
			return Response(response_data, status=status.HTTP_201_CREATED)
		else:
			# Если не удалось отправить в Telegram, удаляем транзакцию
			transaction.delete()
			return Response({
				"error": "Failed to send receipt to Telegram"
			}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
	
	else:
		# Обычное создание транзакции без чека - используем старые параметры
		data = request.data.copy()
		data['user_id'] = user_id
		
		serializer = TransactionSerializer(data=data)
		if serializer.is_valid():
			transaction = serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@api_view(["POST"])
@permission_classes([AllowAny])
def telegram_webhook(request):
	"""Webhook для обработки ответов из Telegram"""
	try:
		data = request.data
		print(f"📨 Telegram webhook received: {data}")
		
		# Проверяем, что это ответ на сообщение
		if 'message' not in data:
			print("❌ No message in data")
			return Response({"status": "ok"})
		
		message = data['message']
		message_id = message.get('message_id')
		text = message.get('text', '').strip()
		user_id = message.get('from', {}).get('id')
		chat_id = message.get('chat', {}).get('id')
		
		print(f"📋 Message details: message_id={message_id}, text='{text}', user_id={user_id}, chat_id={chat_id}")
		
		# Проверяем, что это ответ в нужном чате
		if str(chat_id) != '-1002909289551':
			print(f"❌ Wrong chat_id: {chat_id}")
			return Response({"status": "ok"})
		
		# Проверяем, что это ответ на сообщение с чеком
		if text in ['+', '-']:
			print(f"✅ Processing approval response: '{text}' for message_id: {message_id}")
			
			# Проверяем, есть ли reply_to_message (ответ на сообщение с чеком)
			reply_to_message = message.get('reply_to_message')
			target_message_id = None
			
			if reply_to_message:
				target_message_id = reply_to_message.get('message_id')
				print(f"📎 This is a reply to message_id: {target_message_id}")
			else:
				print(f"⚠️ No reply_to_message found, will search for latest pending transaction")
			
			bot = TelegramBot()
			success = bot.process_approval_response(target_message_id, text, user_id)
			
			if success:
				print(f"✅ Successfully processed response: '{text}'")
				return Response({"status": "processed"})
			else:
				print(f"❌ Failed to process response: '{text}'")
				return Response({"status": "error", "message": "Failed to process response"})
		
		print(f"ℹ️ Text '{text}' is not + or -, ignoring")
		return Response({"status": "ok"})
		
	except Exception as e:
		print(f"❌ Error processing telegram webhook: {e}")
		import traceback
		traceback.print_exc()
		return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
@permission_classes([AllowAny])
def test_webhook(request):
	"""Тестовый endpoint для проверки webhook"""
	try:
		from .models import Transaction
		from .telegram_bot import TelegramBot
		
		# Находим последнюю транзакцию в статусе esperando
		transaction = Transaction.objects.filter(estado='esperando').order_by('-created_at').first()
		
		if not transaction:
			return Response({"error": "No pending transactions found"}, status=404)
		
		# Тестируем обработку ответа
		bot = TelegramBot()
		success = bot.process_approval_response("12345", "+", "test_user")
		
		return Response({
			"transaction": {
				"id": transaction.id,
				"number": transaction.transaccion_number,
				"status": transaction.estado,
				"user_id": transaction.user_id,
				"amount": str(transaction.transacciones_monto),
				"message_id": transaction.message_id
			},
			"test_result": success
		})
		
	except Exception as e:
		return Response({"error": str(e)}, status=500)

# ...existing code...

@api_view(["GET"])
@permission_classes([AllowAny])
def get_countries(request):
	from .models import Country
	countries = Country.objects.all()
	serializer = CountrySerializer(countries, many=True)
	return Response(serializer.data)
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken

@api_view(["GET"])
def hello_world(request):
	return Response({"message": "Hello, world!"})


from rest_framework_simplejwt.tokens import RefreshToken

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
	serializer = UserRegisterSerializer(data=request.data)
	if serializer.is_valid():
		user_profile = serializer.save()
		# Create Django User for JWT
		from django.contrib.auth.models import User
		django_user = User.objects.create_user(
			username=user_profile.email,
			email=user_profile.email,
			password=request.data.get('password')
		)
		# Link UserProfile to Django User
		user_profile.django_user = django_user
		user_profile.save()
		
		# Отправляем уведомление о регистрации в Telegram
		try:
			bot = TelegramBot()
			bot.send_registration_notification(
				user_id=user_profile.user_id,
				country=user_profile.country,
				ref=user_profile.ref or 'N/A'
			)
		except Exception as e:
			print(f"❌ Error sending registration notification: {e}")
			# Не прерываем регистрацию, если не удалось отправить уведомление
		
		# Generate JWT token
		refresh = RefreshToken.for_user(django_user)
		data = serializer.data.copy()
		data["refresh"] = str(refresh)
		data["access"] = str(refresh.access_token)
		return Response(data, status=status.HTTP_201_CREATED)
	return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_stage(request):
	"""Change the `stage` field of a UserProfile.

	- Admins (is_staff) can change any user's stage by providing `user_id`.
	- Regular users can change only their own stage.

	Request JSON:
	{
		"stage": "verif",
		"user_id": "17958522"  # optional for admins
	}
	"""
	user = request.user

	# Validate stage
	stage = request.data.get('stage')
	if not stage:
		return Response({"error": "stage is required"}, status=status.HTTP_400_BAD_REQUEST)

	allowed = ['normal', 'verif', 'verif2', 'supp', 'meet']
	if stage not in allowed:
		return Response({"error": f"Invalid stage. Allowed: {allowed}"}, status=status.HTTP_400_BAD_REQUEST)

	# Determine target user profile
	target_profile = None
	if user.is_staff:
		# admin may pass user_id (either int or str) or django_user id
		user_id = request.data.get('user_id')
		if not user_id:
			return Response({"error": "user_id is required for admin requests"}, status=status.HTTP_400_BAD_REQUEST)

		# Try to find by user_id in UserProfile
		try:
			target_profile = UserProfile.objects.filter(user_id=str(user_id)).first()
			if not target_profile:
				target_profile = UserProfile.objects.filter(user_id=int(user_id)).first()
		except (ValueError, TypeError):
			target_profile = UserProfile.objects.filter(user_id=str(user_id)).first()
	else:
		try:
			target_profile = UserProfile.objects.get(django_user=user)
		except UserProfile.DoesNotExist:
			return Response({"error": "UserProfile not found for current user"}, status=status.HTTP_404_NOT_FOUND)

	if not target_profile:
		return Response({"error": "Target user profile not found"}, status=status.HTTP_404_NOT_FOUND)

	# Update stage
	target_profile.stage = stage
	try:
		target_profile.save()
	except Exception as e:
		return Response({"error": "Failed to save stage", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

	from .serializers import UserProfileUpdateSerializer
	serializer = UserProfileUpdateSerializer(target_profile)
	return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
	email = request.data.get("email")
	password = request.data.get("password")
	try:
		from django.contrib.auth.models import User
		django_user = User.objects.get(email=email)
		if django_user.check_password(password):
			refresh = RefreshToken.for_user(django_user)
			return Response({
				"refresh": str(refresh),
				"access": str(refresh.access_token),
			})
		else:
			return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
	except User.DoesNotExist:
		return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_token(request):
	refresh_token = request.data.get("refresh")
	if not refresh_token:
		return Response({"error": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)
	
	try:
		refresh = RefreshToken(refresh_token)
		return Response({
			"access": str(refresh.access_token),
		})
	except Exception as e:
		return Response({"error": "Invalid refresh token"}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_info(request):
	print(f"Authenticated user: {request.user}")
	print(f"User email: {request.user.email}")
	print(f"User ID: {request.user.id}")
	
	try:
		user = UserProfile.objects.get(django_user=request.user)
		
		# Получаем информацию о стране и валюте
		country_info = None
		if user.country:
			try:
				from .models import Country
				country_obj = Country.objects.get(name=user.country)
				country_info = {
					'name': country_obj.name,
					'currency': country_obj.currency
				}
			except Country.DoesNotExist:
				country_info = {
					'name': user.country,
					'currency': None
				}
		
		# Возвращаем все поля модели
		data = {
			'user_id': user.user_id,
			'email': user.email,
			'deposit': user.deposit,
			'country': user.country,
			'country_info': country_info,  # Добавляем информацию о стране и валюте
			'ref': user.ref,
			'nombre': user.nombre,
			'apellido': user.apellido,
			'cumpleanos': user.cumpleanos,
			'sexo': user.sexo,
			'ciudad': user.ciudad,
			'direccion': user.direccion,
			'numero_de_telefono': user.numero_de_telefono,
			'bonificaciones': user.bonificaciones,
			'registration_date': user.registration_date,
			'status': user.status,
			'positions_mine': user.positions_mine,
			'col_deposit': user.col_deposit,
			'user_status': user.user_status,
			'stage': user.stage,
			'stage_balance': user.stage_balance,
			'verification_start_date': user.verification_start_date,
			'chicken_trap_coefficient': user.chicken_trap_coefficient,
			'first_bonus_used': user.first_bonus_used
		}
		return Response(data)
	except UserProfile.DoesNotExist:
		print(f"UserProfile not found for user: {request.user.id}")
		return Response({"error": "User not found.", "debug": {"user_id": request.user.id}}, status=status.HTTP_404_NOT_FOUND)

# API: Use first bonus
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def use_first_bonus(request):
	"""
	API endpoint для использования первого бонуса пользователем.
	Пользователь может использовать первый бонус только один раз.
	"""
	try:
		user_profile = UserProfile.objects.get(django_user=request.user)
		
		# Проверяем, не использовал ли пользователь уже первый бонус
		if user_profile.first_bonus_used:
			return Response({
				"error": "First bonus already used",
				"message": "You have already used your first bonus"
			}, status=status.HTTP_400_BAD_REQUEST)
		
		# Получаем сумму бонуса из запроса
		bonus_amount = request.data.get('bonus_amount', 0)
		if not bonus_amount or bonus_amount <= 0:
			return Response({
				"error": "Invalid bonus amount",
				"message": "Bonus amount must be greater than 0"
			}, status=status.HTTP_400_BAD_REQUEST)
		
		# Добавляем бонус к текущим бонусам пользователя
		user_profile.bonificaciones += bonus_amount
		user_profile.first_bonus_used = True
		user_profile.save()
		
		return Response({
			"success": True,
			"message": "First bonus applied successfully",
			"bonus_amount": str(bonus_amount),
			"total_bonuses": str(user_profile.bonificaciones),
			"first_bonus_used": user_profile.first_bonus_used
		}, status=status.HTTP_200_OK)
		
	except UserProfile.DoesNotExist:
		return Response({
			"error": "User profile not found"
		}, status=status.HTTP_404_NOT_FOUND)
	except Exception as e:
		return Response({
			"error": "Internal server error",
			"message": str(e)
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# API: Lookup user by user_id
@api_view(["GET"])
@permission_classes([AllowAny])
def lookup_user_by_id(request, user_id):
	"""
	API endpoint для поиска пользователя по user_id.
	Возвращает данные пользователя если найден, иначе null.
	"""
	try:
		# Преобразуем user_id в BigInteger для поиска
		user_id_int = int(user_id)
		
		# Ищем пользователя по user_id
		user_profile = UserProfile.objects.get(user_id=user_id_int)
		
		# Сериализуем данные пользователя
		serializer = UserLookupSerializer(user_profile)
		
		return Response({
			"success": True,
			"user": serializer.data
		}, status=status.HTTP_200_OK)
		
	except ValueError:
		# Неверный формат user_id
		return Response({
			"success": False,
			"user": None,
			"error": "Invalid user_id format. Must be a number."
		}, status=status.HTTP_400_BAD_REQUEST)
		
	except UserProfile.DoesNotExist:
		# Пользователь не найден
		return Response({
			"success": False,
			"user": None,
			"message": "User not found"
		}, status=status.HTTP_200_OK)  # Возвращаем 200 с null, как запрошено
		
	except Exception as e:
		return Response({
			"success": False,
			"user": None,
			"error": "Internal server error",
			"message": str(e)
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([AllowAny])
def payment_callback(request):
 """
 Callback endpoint для обработки платежей от платежной системы.
 
 Принимает POST запрос с данными:
 - orderid: ID платежа (номер транзакции)
 - status: статус платежа (finished/failed/cancelled/etc)
 - amount: сумма платежа
 - currency: валюта платежа
 - time: время платежа в UTC (timestamp в миллисекундах)
 - sign: подпись с ключом мерчанта (игнорируется)
 """
 from decimal import Decimal
 from datetime import datetime
 
 try:
  data = request.data.copy()
  
  print(f"📨 Payment callback received: {data}")
  
  # Проверяем обязательные поля
  required_fields = ['orderid', 'status', 'amount']
  for field in required_fields:
   if field not in data:
    return Response({
     "error": f"Missing required field: {field}"
    }, status=status.HTTP_400_BAD_REQUEST)
  
  # Получаем данные платежа
  order_id = data['orderid']
  payment_status = data['status']
  amount = Decimal(str(data['amount']))
  currency = data.get('currency', 'USD')
  payment_time = int(data.get('time', datetime.now().timestamp() * 1000))
  
  # Ищем транзакцию по номеру (order_id = transaccion_number)
  print(f"🔍 Searching for transaction with number: {order_id}")
  
  try:
   # Сначала пробуем точное совпадение
   transaction = Transaction.objects.get(transaccion_number=order_id)
   print(f"📋 Found transaction: {transaction.transaccion_number} (ID: {transaction.id})")
   print(f"   User ID: {transaction.user_id}")
   print(f"   Amount: {transaction.transacciones_monto} {transaction.currency}")
   print(f"   Current status: {transaction.estado}")
   
  except Transaction.DoesNotExist:
   # Если не найдено, попробуем найти по частичному совпадению или другим вариантам
   print(f"❌ Transaction not found with exact match: {order_id}")
   
   # Попробуем найти похожие транзакции для отладки
   similar_transactions = Transaction.objects.filter(
    transaccion_number__icontains=str(order_id)
   )[:5]
   
   if similar_transactions:
    print(f"🔍 Found {similar_transactions.count()} similar transactions:")
    for t in similar_transactions:
     print(f"   - {t.transaccion_number} (ID: {t.id}, Status: {t.estado})")
   
   # Также покажем последние транзакции для отладки
   recent_transactions = Transaction.objects.all().order_by('-created_at')[:5]
   print(f"📊 Last 5 transactions in database:")
   for t in recent_transactions:
    print(f"   - {t.transaccion_number} (ID: {t.id}, User: {t.user_id}, Status: {t.estado})")
   
   return Response({
    "error": "Transaction not found",
    "order_id": order_id,
    "message": f"No transaction found with number: {order_id}"
   }, status=status.HTTP_404_NOT_FOUND)
  
  except Transaction.MultipleObjectsReturned:
   print(f"⚠️ Multiple transactions found with number: {order_id}")
   transactions = Transaction.objects.filter(transaccion_number=order_id)
   print(f"   Found {transactions.count()} transactions:")
   for t in transactions:
    print(f"   - ID: {t.id}, User: {t.user_id}, Status: {t.estado}, Created: {t.created_at}")
   
   # Берем самую последнюю транзакцию
   transaction = transactions.order_by('-created_at').first()
   print(f"📋 Using latest transaction: {transaction.id}")
  
  except Exception as e:
   print(f"❌ Unexpected error searching for transaction: {e}")
   return Response({
    "error": "Database error",
    "order_id": order_id,
    "message": str(e)
   }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
  
  # Проверяем статус транзакции
  print(f"📊 Transaction status check:")
  print(f"   Current status: {transaction.estado}")
  print(f"   Payment status from callback: {payment_status}")
  print(f"   Transaction amount: {transaction.transacciones_monto}")
  print(f"   Callback amount: {amount}")
  
  if transaction.estado in ['aprobado', 'rechazado']:
   print(f"⚠️ Transaction already processed: {transaction.estado}")
   return Response({
    "message": "Transaction already processed",
    "status": transaction.estado,
    "transaction_id": transaction.id,
    "processed_at": transaction.processed_at
   }, status=status.HTTP_200_OK)
  
  # Дополнительная валидация суммы (опционально)
  if abs(float(transaction.transacciones_monto) - float(amount)) > 0.01:
   print(f"⚠️ Amount mismatch - Transaction: {transaction.transacciones_monto}, Callback: {amount}")
   # Не блокируем, но логируем для отладки
  
  # Обрабатываем платеж в зависимости от статуса
  if payment_status.lower() in ['finished', 'completed', 'success', 'approved']:
   # Успешный платеж
   print(f"✅ Processing successful payment: {payment_status}")
   transaction.estado = 'aprobado'
   transaction.order_id = order_id  # Сохраняем order_id от платежной системы
   transaction.processed_at = datetime.fromtimestamp(payment_time / 1000)
   transaction.processed_by = 'payment_system'
   transaction.notes = f'Payment {payment_status} by payment system. Currency: {currency}'
   transaction.save()
   
  elif payment_status.lower() in ['failed', 'cancelled', 'rejected', 'declined', 'error']:
   # Неуспешный платеж
   print(f"❌ Processing failed payment: {payment_status}")
   transaction.estado = 'rechazado'
   transaction.order_id = order_id  # Сохраняем order_id от платежной системы
   transaction.processed_at = datetime.fromtimestamp(payment_time / 1000)
   transaction.processed_by = 'payment_system'
   transaction.notes = f'Payment {payment_status} by payment system'
   transaction.save()
   
   # Отправляем уведомление об отклонении и завершаем
   try:
    payment_bot_token = '8316441003:AAFOD-t0lCMajM3ksb6EvoEGXgcuARyO2HM'
    payment_chat_id = '-1003257581324'
    
    message = f"""❌ <b>¡Pago rechazado!</b>

👤 ID de usuario: <code>{transaction.user_id}</code>
💵 Monto: <b>{amount} {currency}</b>
🕒 Estado: <i>{payment_status}</i>
📅 Tiempo: <i>{datetime.fromtimestamp(payment_time / 1000).strftime('%d.%m.%Y %H:%M:%S')}</i>"""
   
    url = f'https://api.telegram.org/bot{payment_bot_token}/sendMessage'
    telegram_data = {
     'chat_id': payment_chat_id,
     'text': message,
     'parse_mode': 'HTML'
    }
    
    response = requests.post(url, data=telegram_data)
    
    if response.status_code == 200 and response.json().get('ok'):
     print(f"✅ Payment rejection notification sent to Telegram")
    else:
     print(f"⚠️ Failed to send Telegram rejection notification: {response.text}")
     
   except Exception as e:
    print(f"⚠️ Failed to send Telegram rejection notification: {e}")
   
   return Response({
    "success": True,
    "message": "Payment rejected",
    "order_id": order_id,
    "status": "rejected",
    "reason": payment_status
   }, status=status.HTTP_200_OK)
   
  else:
   # Неизвестный статус
   print(f"⚠️ Unknown payment status: {payment_status}")
   transaction.order_id = order_id  # Сохраняем order_id от платежной системы
   transaction.notes = f'Unknown payment status: {payment_status} from payment system'
   transaction.save()
   
   return Response({
    "error": "Unknown payment status",
    "status": payment_status,
    "order_id": order_id
   }, status=status.HTTP_400_BAD_REQUEST)
  
  try:
   user_profile = UserProfile.objects.get(user_id=transaction.user_id)
   
   print(f"Transaction details - amount_usd: {transaction.amount_usd}, exchange_rate: {transaction.exchange_rate}, callback_amount: {amount}, currency: {currency}")

   if transaction.amount_usd:
    deposit_amount = transaction.amount_usd
   else:
    if transaction.exchange_rate and transaction.exchange_rate > 0:
     deposit_amount = amount / transaction.exchange_rate
    else:
     deposit_amount = amount
   
   print(f"Calculated deposit amount: {deposit_amount}")
   
   old_balance = user_profile.deposit
   user_profile.deposit += deposit_amount
   
   print(f"Balance update - old: {old_balance}, adding: {deposit_amount}, new: {user_profile.deposit}")
   
   user_profile.save()
   
   print(f"User profile saved successfully. Final balance: {user_profile.deposit}")
   
   try:
    payment_bot_token = '8316441003:AAFOD-t0lCMajM3ksb6EvoEGXgcuARyO2HM'
    payment_chat_id = '-1003257581324'
    
    message = f"""✅ <b>¡Pago realizado con éxito!</b>

👤 ID de usuario: <code>{user_profile.user_id}</code>
💵 Monto: <b>{amount} {currency}</b>
💰 Depositado: <b>${deposit_amount}</b>
🕒 Estado: <i>Completado</i>
📅 Tiempo: <i>{datetime.fromtimestamp(payment_time / 1000).strftime('%d.%m.%Y %H:%M:%S')}</i>
🔢 N° Transacción: <code>{order_id}</code>

💼 Balance anterior: <b>${old_balance}</b>
💰 Balance nuevo: <b>${user_profile.deposit}</b>
📈 Incremento: <b>+${deposit_amount}</b>"""
   
    url = f'https://api.telegram.org/bot{payment_bot_token}/sendMessage'
    data = {
     'chat_id': payment_chat_id,
     'text': message,
     'parse_mode': 'HTML'
    }
    
    response = requests.post(url, data=data)
    
    if response.status_code == 200 and response.json().get('ok'):
     print(f"✅ Payment notification sent to Telegram group")
    else:
     print(f"⚠️ Failed to send Telegram notification: {response.text}")
     
   except Exception as e:
    print(f"⚠️ Failed to send Telegram notification: {e}")
   
   return Response({
    "success": True,
    "message": "Payment processed successfully",
    "order_id": order_id,
    "user_id": user_profile.user_id,
    "deposited_amount": str(deposit_amount),
    "new_balance": str(user_profile.deposit)
   }, status=status.HTTP_200_OK)
   
  except UserProfile.DoesNotExist:
   print(f"❌ User profile not found: {transaction.user_id}")
   transaction.estado = 'error'
   transaction.notes = 'User profile notfound'
   transaction.save()
   
   return Response({
    "error": "User profile not found",
    "order_id": order_id
   }, status=status.HTTP_404_NOT_FOUND)
 
 except Exception as e:
  print(f"❌ Error processing payment callback: {e}")
  import traceback
  traceback.print_exc()
  
  return Response({
   "error": "Internal server error",
   "message": str(e)
  }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# API: Update user deposit
@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_deposit(request):
	"""
	API endpoint для изменения deposit пользователя.
	Поддерживает как PUT (полная замена), так и PATCH (частичное обновление).
	"""
	try:
		user_profile = UserProfile.objects.get(django_user=request.user)
		
		# Используем сериализатор для валидации данных
		serializer = DepositUpdateSerializer(user_profile, data=request.data, partial=request.method == 'PATCH')
		
		if serializer.is_valid():
			# Сохраняем старое значение для логирования
			old_deposit = user_profile.deposit
			
			# Обновляем deposit
			serializer.save()
			
			# Получаем обновленный объект
			user_profile.refresh_from_db()
			
			return Response({
				"success": True,
				"message": "Deposit updated successfully",
				"old_deposit": str(old_deposit),
				"new_deposit": str(user_profile.deposit),
				"user_id": user_profile.user_id
			}, status=status.HTTP_200_OK)
		else:
			return Response({
				"error": "Validation error",
				"details": serializer.errors
			}, status=status.HTTP_400_BAD_REQUEST)
			
	except UserProfile.DoesNotExist:
		return Response({
			"error": "User profile not found"
		}, status=status.HTTP_404_NOT_FOUND)
	except Exception as e:
		return Response({
			"error": "Internal server error",
			"message": str(e)
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# API: Lookup user by user_id
@api_view(["GET"])
@permission_classes([AllowAny])
def lookup_user_by_id(request, user_id):
	"""
	API endpoint для поиска пользователя по user_id.
	Возвращает данные пользователя если найден, иначе null.
	"""
	try:
		# Преобразуем user_id в BigInteger для поиска
		user_id_int = int(user_id)
		
		# Ищем пользователя по user_id
		user_profile = UserProfile.objects.get(user_id=user_id_int)
		
		# Сериализуем данные пользователя
		serializer = UserLookupSerializer(user_profile)
		
		return Response({
			"success": True,
			"user": serializer.data
		}, status=status.HTTP_200_OK)
		
	except ValueError:
		# Неверный формат user_id
		return Response({
			"success": False,
			"user": None,
			"error": "Invalid user_id format. Must be a number."
		}, status=status.HTTP_400_BAD_REQUEST)
		
	except UserProfile.DoesNotExist:
		# Пользователь не найден
		return Response({
			"success": False,
			"user": None,
			"message": "User not found"
		}, status=status.HTTP_200_OK)  # Возвращаем 200 с null, как запрошено
		
	except Exception as e:
		return Response({
			"success": False,
			"user": None,
			"error": "Internal server error",
			"message": str(e)
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
@permission_classes([AllowAny])
def debug_transactions(request):
	"""
	Debug endpoint для проверки транзакций (только для отладки)
	"""
	try:
		# Получаем параметры
		transaction_number = request.GET.get('number')
		user_id = request.GET.get('user_id')
		limit = int(request.GET.get('limit', 10))
		
		transactions = Transaction.objects.all()
		
		# Фильтруем по номеру транзакции
		if transaction_number:
			transactions = transactions.filter(transaccion_number__icontains=transaction_number)
		
		# Фильтруем по user_id
		if user_id:
			transactions = transactions.filter(user_id=user_id)
		
		# Ограничиваем количество
		transactions = transactions.order_by('-created_at')[:limit]
		
		result = []
		for t in transactions:
			result.append({
				'id': t.id,
				'transaccion_number': t.transaccion_number,
				'order_id': t.order_id,
				'user_id': t.user_id,
				'amount': str(t.transacciones_monto),
				'currency': t.currency,
				'status': t.estado,
				'created_at': t.created_at,
				'processed_at': t.processed_at,
				'processed_by': t.processed_by
			})
		
		return Response({
			'success': True,
			'count': len(result),
			'transactions': result,
			'filters': {
				'number': transaction_number,
				'user_id': user_id,
				'limit': limit
			}
		})
		
	except Exception as e:
		return Response({
			'error': str(e)
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([AllowAny])
def test_payment_callback(request):
	"""
	Test endpoint для тестирования payment callback
	"""
	try:
		# Создаем тестовую транзакцию если её нет
		test_order_id = request.data.get('orderid', 'TEST123456')
		test_amount = request.data.get('amount', '100.00')
		test_status = request.data.get('status', 'finished')
		
		# Проверяем, есть ли такая транзакция
		transaction = Transaction.objects.filter(transaccion_number=test_order_id).first()
		
		if not transaction:
			# Создаем тестовую транзакцию
			from datetime import datetime
			transaction = Transaction.objects.create(
				user_id='17958522',  # Тестовый user_id
				transacciones_data=datetime.now(),
				transacciones_monto=test_amount,
				estado='esperando',
				transaccion_number=test_order_id,
				currency='USD'
			)
			print(f"✅ Created test transaction: {test_order_id}")
		
		# Теперь вызываем реальный payment_callback
		test_data = {
			'orderid': test_order_id,
			'status': test_status,
			'amount': test_amount,
			'currency': 'USD'
		}
		
		# Создаем новый request объект для тестирования
		from django.test import RequestFactory
		factory = RequestFactory()
		test_request = factory.post('/api/payment-callback/', test_data, content_type='application/json')
		test_request.data = test_data
		
		# Вызываем payment_callback
		response = payment_callback(test_request)
		
		return Response({
			'test_success': True,
			'test_transaction': {
				'id': transaction.id,
				'number': transaction.transaccion_number,
				'status': transaction.estado
			},
			'callback_response': {
				'status_code': response.status_code,
				'data': response.data
			}
		})
		
	except Exception as e:
		import traceback
		return Response({
			'test_success': False,
			'error': str(e),
			'traceback': traceback.format_exc()
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)