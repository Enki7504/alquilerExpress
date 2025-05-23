from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Perfil
from .models import Comentario
class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['descripcion']
        widgets = {
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Escribe tu comentario aquí...'
            }),
        }
        labels = {
            'descripcion': 'Comentario',
        }
class RegistroUsuarioForm(UserCreationForm):
    dni = forms.CharField(max_length=20, required=True, label="DNI")
    email = forms.EmailField(required=True, label="Correo electrónico")

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "password1", "password2", "dni")

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data["email"]
        user.username = email  # Asigna el email como username
        user.email = email
        if commit:
            user.save()
            dni = self.cleaned_data["dni"]
            Perfil.objects.create(usuario=user, dni=dni)
        return user