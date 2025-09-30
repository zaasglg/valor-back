from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from .models import UserProfile, HistorialPagos
from .serializers import UserRegisterSerializer, CountrySerializer, TransactionSerializer, UserProfileUpdateSerializer, HistorialPagosSerializer
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
		# Save the withdrawal record
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
	# Get user profile to access user_id
	try:
		user_profile = UserProfile.objects.get(django_user=request.user)
		user_id = str(user_profile.user_id)
	except UserProfile.DoesNotExist:
		return Response({"error": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)
	
	# Add user_id to request data
	data = request.data.copy()
	data['user_id'] = user_id
	
	serializer = TransactionSerializer(data=data)
	if serializer.is_valid():
		serializer.save()
		return Response(serializer.data, status=status.HTTP_201_CREATED)
	return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
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
		# Generate JWT token
		refresh = RefreshToken.for_user(django_user)
		data = serializer.data.copy()
		data["refresh"] = str(refresh)
		data["access"] = str(refresh.access_token)
		return Response(data, status=status.HTTP_201_CREATED)
	return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
