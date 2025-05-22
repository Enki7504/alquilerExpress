from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Perfil

class RegistroUsuarioForm(UserCreationForm):
    dni = forms.CharField(max_length=20, required=True, label="DNI")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2", "dni")

    def save(self, commit=True):
        user = super().save(commit)
        dni = self.cleaned_data["dni"]
        Perfil.objects.create(usuario=user, dni=dni)
        return user