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
		user = serializer.save()
		# Generate JWT token for the new user
		refresh = RefreshToken.for_user(user)
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
		user = UserProfile.objects.get(email=email)
		if check_password(password, user.password):
			refresh = RefreshToken.for_user(user)
			return Response({
				"refresh": str(refresh),
				"access": str(refresh.access_token),
			})
		else:
			return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
	except UserProfile.DoesNotExist:
		return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
