# forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from .models import Perfil
from datetime import date
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

class RegistroUsuarioForm(UserCreationForm):
    dni = forms.CharField(max_length=20, required=True, label="DNI")
    email = forms.EmailField(required=True, label="Correo electrónico")
    fecha_nacimiento = forms.DateField(
        label="Fecha de nacimiento",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "fecha_nacimiento", "dni", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("Ya existe un usuario con este correo electrónico.")
        return email

    def clean_dni(self):
        dni = self.cleaned_data["dni"]
        if Perfil.objects.filter(dni=dni).exists():
            raise forms.ValidationError("Este DNI ya está registrado.")
        return dni

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data["fecha_nacimiento"]
        hoy = date.today()
        edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
        if edad < 18:
            raise forms.ValidationError("Debes ser mayor de 18 años.")
        return fecha

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data["email"]
        user.username = email
        user.email = email
        if commit:
            user.save()
            dni = self.cleaned_data["dni"]
            fecha_nacimiento = self.cleaned_data["fecha_nacimiento"]
            if not Perfil.objects.filter(usuario=user).exists():
                Perfil.objects.create(usuario=user, dni=dni, fecha_nacimiento=fecha_nacimiento)
            grupo_cliente, _ = Group.objects.get_or_create(name="cliente")
            user.groups.add(grupo_cliente)
        return user

class LoginForm(forms.Form):
    email = forms.EmailField(label='Correo electrónico')
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña')


class AdminLoginForm(forms.Form):
    email = forms.EmailField(label='Email')
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña')

class ClienteCreationForm(forms.Form):
    first_name = forms.CharField(
        label="Nombre",
        max_length=30,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
                message="El nombre solo puede contener letras y espacios."
            )
        ]
    )
    last_name = forms.CharField(
        label="Apellido",
        max_length=30,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
                message="El apellido solo puede contener letras y espacios."
            )
        ]
    )
    email = forms.EmailField(label="Correo electrónico")
    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Contraseña",
        min_length=9,
        help_text="La contraseña debe tener al menos 9 caracteres."
    )
    dni = forms.CharField(
        label="DNI",
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\d{7,8}$',
                message="El DNI debe contener 7 u 8 dígitos numéricos."
            )
        ]
    )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("Ya existe un usuario con este correo electrónico.")
        return email

    def clean_dni(self):
        dni = self.cleaned_data["dni"]
        if Perfil.objects.filter(dni=dni).exists():
            raise forms.ValidationError("Ya existe un usuario con este DNI.")
        return dni

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if len(password) < 9:
            raise forms.ValidationError("La contraseña debe tener al menos 9 caracteres.")
        return password

    def save(self, commit=True):
        user = User(
            username=self.cleaned_data["email"],
            email=self.cleaned_data["email"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
        )
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            grupo_cliente, _ = Group.objects.get_or_create(name="cliente")
            user.groups.add(grupo_cliente)
            Perfil.objects.create(
                usuario=user,
                dni=self.cleaned_data["dni"]
            )
        return user
    
class EmpleadoCreationForm(forms.Form):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    dni = forms.CharField(max_length=20)

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(username=email).exists():
            raise ValidationError("Ya existe un usuario con este email.")
        return email

    def clean_dni(self):
        dni = self.cleaned_data["dni"]
        if Perfil.objects.filter(dni=dni).exists():
            raise ValidationError("Este DNI ya está registrado.")
        return dni    

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["email"],
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"]
        )
        # Asignar al grupo "empleado"
        grupo_empleado, _ = Group.objects.get_or_create(name="empleado")
        user.groups.add(grupo_empleado)
        Perfil.objects.create(usuario=user, dni=data["dni"])
        return user
    

class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(
        label="Contraseña actual",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    new_password1 = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True,
        min_length=8
    )
    new_password2 = forms.CharField(
        label="Repetir nueva contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True,
        min_length=8
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        current_password = self.cleaned_data.get("current_password")
        if not self.user.check_password(current_password):
            raise forms.ValidationError("La contraseña actual es incorrecta.")
        return current_password

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get("new_password1")
        new_password2 = cleaned_data.get("new_password2")
        current_password = cleaned_data.get("current_password")

        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise forms.ValidationError("Las contraseñas no coinciden.")
            if len(new_password1) < 8:
                raise forms.ValidationError("La contraseña tiene menos de 8 caracteres.")
            if current_password and new_password1 == current_password:
                raise forms.ValidationError("La contraseña debe ser diferente a la actual.")
        return cleaned_data

class EmpleadoCreationForm(forms.Form):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    dni = forms.CharField(max_length=20)

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(username=email).exists():
            raise ValidationError("Ya existe un usuario con este email.")
        return email

    def clean_dni(self):
        dni = self.cleaned_data["dni"]
        if Perfil.objects.filter(dni=dni).exists():
            raise ValidationError("Este DNI ya está registrado.")
        return dni    

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["email"],
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"]
        )
        # Asignar al grupo "empleado"
        grupo_empleado, _ = Group.objects.get_or_create(name="empleado")
        user.groups.add(grupo_empleado)
        Perfil.objects.create(usuario=user, dni=data["dni"])
        return user

# esto sirve? 
class AdminLoginForm(forms.Form):
    email = forms.EmailField(label='Email')
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña')