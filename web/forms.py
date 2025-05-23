from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Perfil

class RegistroUsuarioForm(UserCreationForm):
    dni = forms.CharField(max_length=20, required=True, label="DNI")

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "password1", "password2", "dni")

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '')
        return first_name.title()

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '')
        return last_name.title()

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data["email"]
        user.username = email  # Asigna el email como username
        user.email = email
        # Normaliza los nombres antes de guardar
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
            dni = self.cleaned_data["dni"]
            Perfil.objects.create(usuario=user, dni=dni)
        return user

class LoginForm(forms.Form):
    email = forms.EmailField(label='Correo electrónico')
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña')