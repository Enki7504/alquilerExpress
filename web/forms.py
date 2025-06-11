from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Cochera, Comentario, Estado, Inmueble, Perfil, Resenia, RespuestaComentario
from .models import Perfil, Comentario, Inmueble, Estado, Cochera, Ciudad, Provincia
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

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
        fields = ("email", "first_name", "last_name", "password1", "password2")  # Quitar "dni" de aquí

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

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data["email"]
        user.username = email
        user.email = email
        if commit:
            user.save()
            dni = self.cleaned_data["dni"]
            # Solo crear el perfil si no existe
            if not Perfil.objects.filter(usuario=user).exists():
                Perfil.objects.create(usuario=user, dni=dni)
            # Asignar grupo cliente
            grupo_cliente, _ = Group.objects.get_or_create(name="cliente")
            user.groups.add(grupo_cliente)
        return user

class LoginForm(forms.Form):
    email = forms.EmailField(label='Correo electrónico')
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña')


class InmuebleForm(forms.ModelForm):
    provincia = forms.ModelChoiceField(
        queryset=Provincia.objects.all(),
        required=True,
        label="Provincia",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_provincia'})
    )
    ciudad = forms.ModelChoiceField(
        queryset=Ciudad.objects.none(),
        required=True,
        label="Ciudad",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_ciudad'})
    )
    estado = forms.ModelChoiceField(
        queryset=Estado.objects.filter(nombre__in=["Disponible", "Ocupado", "Oculto", "En Mantenimiento"]),
        required=True,
        label="Estado"
    )
    cochera = forms.ModelChoiceField(
        queryset=Cochera.objects.filter(estado__nombre="Disponible"),
        required=False,
        label="Cochera",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'cocheraSelect'})
    )
    empleado = forms.ModelChoiceField(
        queryset=Perfil.objects.filter(usuario__groups__name="empleado"),
        required=False,
        label="Empleado asignado",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    minimo_dias_alquiler = forms.IntegerField(
        min_value=1,
        label="Mínimo de días de alquiler",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        initial=1
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'provincia' in self.data:
            try:
                provincia_id = int(self.data.get('provincia'))
                self.fields['ciudad'].queryset = Ciudad.objects.filter(provincia_id=provincia_id).order_by('nombre')
            except (ValueError, TypeError):
                self.fields['ciudad'].queryset = Ciudad.objects.none()
        elif self.instance.pk and self.instance.provincia:
            self.fields['ciudad'].queryset = Ciudad.objects.filter(provincia=self.instance.provincia).order_by('nombre')
        else:
            self.fields['ciudad'].queryset = Ciudad.objects.none()

    class Meta:
        model = Inmueble
        fields = [
            'nombre', 'ubicacion', 'descripcion', 'cantidad_banios', 'cantidad_ambientes',
            'cantidad_camas', 'cantidad_huespedes', 'precio_por_dia', 'politica_cancelacion',
            'provincia', 'ciudad', 'cochera', 'estado', 'empleado', 'minimo_dias_alquiler'  # <-- AGREGADO AQUÍ
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

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre']
        qs = Inmueble.objects.filter(nombre=nombre)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe una vivienda con este nombre.")
        return nombre

    # Esto pone el estado de la cochera a "Oculto" cuando se guarda el inmueble
    def save(self, commit=True):
        inmueble = super().save(commit=False)
        cochera = self.cleaned_data.get('cochera')
        if cochera:
            # Cambiar el estado de la cochera a "Oculto"
            estado_oculto = Estado.objects.get(nombre="Oculto")
            cochera.estado = estado_oculto
            cochera.save()
        if commit:
            inmueble.save()
            self.save_m2m()
        return inmueble

class CocheraForm(forms.ModelForm):
    provincia = forms.ModelChoiceField(
        queryset=Provincia.objects.all(),
        required=True,
        label="Provincia",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_provincia'})
    )
    ciudad = forms.ModelChoiceField(
        queryset=Ciudad.objects.none(),
        required=True,
        label="Ciudad",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_ciudad'})
    )
    estado = forms.ModelChoiceField(
        queryset=Estado.objects.filter(nombre__in=["Disponible", "Ocupado", "Oculto", "En Mantenimiento"]),
        required=True,
        label="Estado"
    )
    empleado = forms.ModelChoiceField(
        queryset=Perfil.objects.filter(usuario__groups__name="empleado"),
        required=False,
        label="Empleado asignado",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    minimo_dias_alquiler = forms.IntegerField(
        min_value=1,
        label="Mínimo de días de alquiler",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        initial=1
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'provincia' in self.data:
            try:
                provincia_id = int(self.data.get('provincia'))
                self.fields['ciudad'].queryset = Ciudad.objects.filter(provincia_id=provincia_id).order_by('nombre')
            except (ValueError, TypeError):
                self.fields['ciudad'].queryset = Ciudad.objects.none()
        elif self.instance.pk and self.instance.provincia:
            self.fields['ciudad'].queryset = Ciudad.objects.filter(provincia=self.instance.provincia).order_by('nombre')
        else:
            self.fields['ciudad'].queryset = Ciudad.objects.none()

    class Meta:
        model = Cochera
        fields = [
            'nombre', 'ubicacion', 'descripcion', 'alto', 'ancho', 'largo',
            'cantidad_vehiculos', 'con_techo', 'precio_por_dia', 'politica_cancelacion',
            'provincia', 'ciudad', 'estado', 'empleado', 'minimo_dias_alquiler'  # <-- AGREGADO AQUÍ
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
    
    def clean_nombre(self):
        nombre = self.cleaned_data['nombre']
        qs = Cochera.objects.filter(nombre=nombre)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe una cochera con este nombre.")
        return nombre

# esto sirve? 
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

class EmpleadoAdminCreationForm(forms.Form):
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
    dni = forms.CharField(
        label="DNI",
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\d{7,8}$',  # Para DNI argentino; ajusta según el formato de tu país
                message="El DNI debe contener 7 u 8 dígitos numéricos."
            )
        ]
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("Ya existe un usuario con este correo electrónico.")
        return email

    def clean_dni(self):
        dni = self.cleaned_data['dni']
        if Perfil.objects.filter(dni=dni).exists():
            raise forms.ValidationError("Ya existe un usuario con este DNI.")
        return dni

class ClienteAdminCreationForm(forms.Form):
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

class ReseniaForm(forms.ModelForm):
    calificacion = forms.ChoiceField(
        choices=[
            (5, "⭐️⭐️⭐️⭐️⭐️ Excelente"),
            (4, "⭐️⭐️⭐️⭐️ Muy bueno"),
            (3, "⭐️⭐️⭐️ Bueno"),
            (2, "⭐️⭐️ Regular"),
            (1, "⭐️ Malo"),
        ],
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'}),
        label="Calificación",
        required=True
    )
    descripcion = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Compartí detalles de tu estadía...'}),
        label="Opinión (opcional)",
        required=False
    )

    class Meta:
        model = Resenia
        fields = ['calificacion', 'descripcion']

class RespuestaComentarioForm(forms.ModelForm):
    texto = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Responder al comentario...'}),
        label='Respuesta',
        required=True
    )

    class Meta:
        model = RespuestaComentario
        fields = ['texto']

class NotificarImprevistoForm(forms.Form):
    usuario = forms.ModelChoiceField(
        queryset=Perfil.objects.all(),
        label="Usuario afectado",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    mensaje = forms.CharField(
        label="Mensaje del imprevisto",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        required=True
    )