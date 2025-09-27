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
            'email', 'password', 'country',
            'ref', 'nombre', 'apellido', 'cumpleanos', 'sexo', 'ciudad', 'direccion', 'numero_de_telefono'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'ref': {'required': False, 'allow_blank': True, 'allow_null': True},
            'nombre': {'required': False, 'allow_blank': True, 'allow_null': True},
            'apellido': {'required': False, 'allow_blank': True, 'allow_null': True},
            'cumpleanos': {'required': False, 'allow_null': True},
            'sexo': {'required': False, 'allow_blank': True, 'allow_null': True},
            'ciudad': {'required': False, 'allow_blank': True, 'allow_null': True},
            'direccion': {'required': False, 'allow_blank': True, 'allow_null': True},
            'numero_de_telefono': {'required': False, 'allow_blank': True, 'allow_null': True},
        }

    def create(self, validated_data):
        # Hash the password before saving
        from django.contrib.auth.hashers import make_password
        validated_data['password'] = make_password(validated_data['password'])
        
        # Generate user_id if not provided
        if 'user_id' not in validated_data or not validated_data['user_id']:
            import random
            while True:
                new_id = random.randint(100000, 999999999)
                if not UserProfile.objects.filter(user_id=new_id).exists():
                    validated_data['user_id'] = new_id
                    break
        
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
