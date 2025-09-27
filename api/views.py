from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from .models import UserProfile, HistorialPagos
from .serializers import UserRegisterSerializer, CountrySerializer, TransactionSerializer, UserProfileUpdateSerializer, HistorialPagosSerializer
# API: List all historial pagos
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def historial_pagos_list(request):
	pagos = HistorialPagos.objects.all().order_by('-transacciones_data')
	serializer = HistorialPagosSerializer(pagos, many=True)
	return Response(serializer.data)

# API: Create historial pago
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def historial_pagos_create(request):
	serializer = HistorialPagosSerializer(data=request.data)
	if serializer.is_valid():
		serializer.save()
		return Response(serializer.data, status=status.HTTP_201_CREATED)
	return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# API endpoint to update user profile (authenticated user updates their own profile)
@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_profile(request):
	user = request.user
	try:
		profile = UserProfile.objects.get(email=user.email)
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
def transactions_list(request):
	transactions = Transaction.objects.all().order_by('-created_at')
	serializer = TransactionSerializer(transactions, many=True)
	return Response(serializer.data)

@api_view(["POST"])
@permission_classes([AllowAny])
def transaction_create(request):
	serializer = TransactionSerializer(data=request.data)
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
		user = UserProfile.objects.get(email=request.user.email)
		# Возвращаем все поля модели
		data = {
			'user_id': user.user_id,
			'email': user.email,
			'deposit': user.deposit,
			'country': user.country,
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
			'chicken_trap_coefficient': user.chicken_trap_coefficient
		}
		return Response(data)
	except UserProfile.DoesNotExist:
		print(f"UserProfile not found for email: {request.user.email}")
		return Response({"error": "User not found.", "debug": {"email": request.user.email}}, status=status.HTTP_404_NOT_FOUND)
