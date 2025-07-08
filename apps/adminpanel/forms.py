from django import forms
from django.contrib.auth.models import User
from datetime import date

from .models import Cochera, Estado, Inmueble, Perfil
from .models import Perfil, Inmueble, Estado, Cochera, Ciudad, Provincia
from django.core.validators import RegexValidator
from django.db.models import Q

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
    fecha_nacimiento = forms.DateField(
        label="Fecha de nacimiento",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
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

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data["fecha_nacimiento"]
        hoy = date.today()
        edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
        if edad < 18:
            raise forms.ValidationError("El empleado debe ser mayor de 18 años.")
        return fecha
    
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
    fecha_nacimiento = forms.DateField(
        label="Fecha de nacimiento",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
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
    
    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data["fecha_nacimiento"]
        hoy = date.today()
        edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
        if edad < 18:
            raise forms.ValidationError("El cliente debe ser mayor de 18 años.")
        return fecha
    
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
        if self.instance.pk and self.instance.cochera:
            cocheras = Cochera.objects.filter(
                Q(estado__nombre="Disponible") | Q(pk=self.instance.cochera.pk)
            )
        else:
            cocheras = Cochera.objects.filter(estado__nombre="Disponible")
        self.fields['cochera'].queryset = cocheras

    class Meta:
        model = Inmueble
        fields = [
            'nombre', 'direccion', 'descripcion', 'cantidad_banios', 'cantidad_ambientes',
            'cantidad_camas', 'cantidad_huespedes', 'precio_por_dia', 'politica_cancelacion',
            'provincia', 'ciudad', 'cochera', 'estado', 'empleado', 'minimo_dias_alquiler'  # <-- AGREGADO AQUÍ
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'politica_cancelacion': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'cantidad_banios': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'cantidad_ambientes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'cantidad_camas': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'cantidad_huespedes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'precio_por_dia': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'cochera': forms.Select(attrs={'class': 'form-select', 'id': 'cocheraSelect'}),
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
        cochera_nueva = self.cleaned_data.get('cochera')
        cochera_anterior = None

        # Si el inmueble ya existe y tenía cochera asignada, la guardamos
        if self.instance.pk:
            inmueble_db = Inmueble.objects.get(pk=self.instance.pk)
            cochera_anterior = inmueble_db.cochera

        # Si se desasigna la cochera (se deja vacío)
        if cochera_anterior and cochera_anterior != cochera_nueva:
            # Cambiar el estado de la cochera anterior a "Disponible"
            estado_disponible = Estado.objects.get(nombre="Disponible")
            cochera_anterior.estado = estado_disponible
            cochera_anterior.save()

        # Si se asigna una nueva cochera
        if cochera_nueva:
            # Cambiar el estado de la cochera nueva a "Oculto"
            estado_oculto = Estado.objects.get(nombre="Oculto")
            cochera_nueva.estado = estado_oculto
            cochera_nueva.save()

        inmueble.cochera = cochera_nueva

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
            'nombre', 'direccion', 'descripcion', 'alto', 'ancho', 'largo',
            'cantidad_vehiculos', 'con_techo', 'precio_por_dia', 'politica_cancelacion',
            'provincia', 'ciudad', 'estado', 'empleado', 'minimo_dias_alquiler'  # <-- AGREGADO AQUÍ
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
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