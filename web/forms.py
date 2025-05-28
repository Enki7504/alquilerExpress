from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Perfil, Comentario, Inmueble, Estado, Cochera
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

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
        
# esto sirve? 
class AdminLoginForm(forms.Form):
    email = forms.EmailField(label='Email')
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña')

# para el registro de cliente
class ClienteCreationForm(forms.ModelForm):
    email = forms.EmailField(label="Correo electrónico")
    first_name = forms.CharField(label="Nombre")
    last_name = forms.CharField(label="Apellido")
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    dni = forms.CharField(label="DNI")

    class Meta:
        model = Perfil
        fields = ["dni"]

    def save(self, commit=True):
        email = self.cleaned_data["email"]
        password = self.cleaned_data["password"]
        first_name = self.cleaned_data["first_name"]
        last_name = self.cleaned_data["last_name"]

        # Crear el usuario
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        # Agregar al grupo "cliente"
        from django.contrib.auth.models import Group
        grupo_cliente, _ = Group.objects.get_or_create(name="cliente")
        user.groups.add(grupo_cliente)

        # Crear el perfil
        perfil = super().save(commit=False)
        perfil.usuario = user
        if commit:
            perfil.save()
        return perfil

#para el registro de empleado
class ClienteCreationForm(forms.ModelForm):
    email = forms.EmailField(label="Correo electrónico")
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    first_name = forms.CharField(label="Nombre")
    last_name = forms.CharField(label="Apellido")
    dni = forms.CharField(label="DNI")

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name"]

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if len(password) < 9:
            raise forms.ValidationError("La contraseña debe tener más de 8 caracteres.")
        return password

    def clean_dni(self):
        dni = self.cleaned_data.get("dni")
        if Perfil.objects.filter(dni=dni).exists():
            raise forms.ValidationError("Este DNI ya está registrado.")
        return dni

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

            # Asignar grupo cliente
            grupo_cliente, _ = Group.objects.get_or_create(name="cliente")
            user.groups.add(grupo_cliente)

            # Crear perfil
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

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if len(password) < 9:
            raise forms.ValidationError("La contraseña debe tener más de 8 caracteres.")
        return password

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
