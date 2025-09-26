from django.contrib import admin


from .models import UserProfile, Country, PaymentMethod, CountryPaymentMethod, Transaction, HistorialPagos

# Admin for HistorialPagos
@admin.register(HistorialPagos)
class HistorialPagosAdmin(admin.ModelAdmin):
	list_display = ('id', 'user_id', 'transacciones_data', 'transacciones_monto', 'estado', 'transaccion_number', 'metodo_de_pago', 'phone', 'cuenta_corriente', 'numero_de_cuenta', 'tipo_de_documento', 'numero_documento', 'banco')
	search_fields = ('user_id', 'transaccion_number', 'metodo_de_pago', 'phone', 'numero_de_cuenta', 'numero_documento', 'banco')
	list_filter = ('estado', 'metodo_de_pago', 'banco')
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
	list_display = ('id', 'user_id', 'transacciones_data', 'transacciones_monto', 'estado', 'transaccion_number', 'metodo_de_pago', 'amount_usd', 'stage_processed', 'currency', 'exchange_rate', 'created_at')
	search_fields = ('user_id', 'transaccion_number', 'metodo_de_pago', 'currency')
	list_filter = ('estado', 'metodo_de_pago', 'currency', 'stage_processed')



from django import forms
from django.contrib.auth.hashers import make_password

class UserProfileAdminForm(forms.ModelForm):
	password = forms.CharField(widget=forms.PasswordInput, required=False, help_text="Leave blank to keep unchanged.")

	class Meta:
		model = UserProfile
		fields = '__all__'

	def clean_password(self):
		password = self.cleaned_data.get('password')
		if password:
			return make_password(password)
		# If password not provided, keep the old one
		if self.instance and self.instance.pk:
			return self.instance.password
		return password

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
	form = UserProfileAdminForm
	list_display = ('id', 'email', 'user_id', 'status', 'registration_date')
	search_fields = ('email', 'user_id', 'nombre', 'apellido')
	list_filter = ('status', 'country', 'sexo', 'stage')


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'currency')
	search_fields = ('name', 'currency')


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
	list_display = ('id', 'label', 'numero_de_cuenta', 'banco', 'cryptoId', 'is_universal', 'status')
	search_fields = ('label', 'numero_de_cuenta', 'banco', 'cryptoId')
	list_filter = ('is_universal', 'status', 'banco', 'cryptoId')


@admin.register(CountryPaymentMethod)
class CountryPaymentMethodAdmin(admin.ModelAdmin):
	list_display = ('id', 'country', 'payment_method')
	search_fields = ('country__name', 'payment_method__label')
