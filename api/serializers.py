from rest_framework import serializers
from .models import UserProfile, Country, Transaction, HistorialPagos
# Serializer for HistorialPagos
class HistorialPagosSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialPagos
        fields = '__all__'
# ...existing code...

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
# ...existing code...

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name', 'currency']


class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'user_id', 'ref', 'email', 'password', 'country', 'nombre', 'apellido',
            'cumpleanos', 'sexo', 'ciudad', 'direccion', 'numero_de_telefono'
        ]
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Hash the password before saving
        from django.contrib.auth.hashers import make_password
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)



# Serializer for updating user profile (allow all fields except user_id and registration_date)
class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        exclude = ['user_id', 'registration_date']

    def update(self, instance, validated_data):
        # If password is being updated, hash it
        password = validated_data.get('password', None)
        if password:
            from django.contrib.auth.hashers import make_password
            instance.password = make_password(password)
            validated_data.pop('password')
        return super().update(instance, validated_data)
