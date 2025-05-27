from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Perfil, Comentario, Inmueble, Estado, Cochera

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

class LoginForm(forms.Form):
    email = forms.EmailField(label='Correo electrónico')
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña')


class InmuebleForm(forms.ModelForm):
    imagen = forms.ImageField(required=False, label="Foto del inmueble")
    estado = forms.ModelChoiceField(queryset=Estado.objects.all(), required=True, label="Estado")

    class Meta:
        model = Inmueble
        fields = [
            'nombre', 'ubicacion', 'descripcion', 'cantidad_banios', 'cantidad_ambientes',
            'cantidad_camas', 'cantidad_huespedes', 'precio_por_dia', 'politica_cancelacion',
            'cochera', 'estado'
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'politica_cancelacion': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'cantidad_banios': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'cantidad_ambientes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'cantidad_camas': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'cantidad_huespedes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'precio_por_dia': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'cochera': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }

class CocheraForm(forms.ModelForm):
    imagen = forms.ImageField(required=False, label="Foto de la cochera")
    estado = forms.ModelChoiceField(queryset=Estado.objects.all(), required=True, label="Estado")

    class Meta:
        model = Cochera
        fields = [
            'nombre', 'ubicacion', 'descripcion', 'alto', 'ancho', 'largo',
            'cantidad_vehiculos', 'con_techo', 'precio_por_dia', 'politica_cancelacion',
            'estado'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'alto': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'ancho': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'largo': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'cantidad_vehiculos': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'con_techo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'precio_por_dia': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'politica_cancelacion': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }