import random
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Perfil(models.Model):
    id_perfil = models.AutoField(primary_key=True)
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    dni = models.CharField(max_length=20)
    fecha_nacimiento = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.usuario.first_name} {self.usuario.last_name} - DNI: {self.dni}"

# para los estados de los inmuebles, cocheras y reservas
class Estado(models.Model):
    id_estado = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

# para las provincias y ciudades que se usan en los inmuebles y cocheras
class Provincia(models.Model):
    id = models.PositiveIntegerField(primary_key=True)  # para usar IDs específicos
    nombre = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.nombre

class Ciudad(models.Model):
    id = models.PositiveIntegerField(primary_key=True)  # para usar IDs específicos
    nombre = models.CharField(max_length=255)
    provincia = models.ForeignKey(Provincia, related_name='ciudades', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.nombre} ({self.provincia.nombre})"
     
class Cochera(models.Model):
    id_cochera = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    alto = models.FloatField()
    ancho = models.FloatField()
    largo = models.FloatField()
    cantidad_vehiculos = models.IntegerField()
    con_techo = models.BooleanField()
    descripcion = models.TextField()
    direccion = models.TextField()
    provincia = models.ForeignKey(Provincia, on_delete=models.SET_NULL, null=True)
    ciudad = models.ForeignKey(Ciudad, on_delete=models.SET_NULL, null=True)
    precio_por_dia = models.DecimalField(max_digits=10, decimal_places=2)
    politica_cancelacion = models.TextField()
    fecha_publicacion = models.DateField()
    estado = models.ForeignKey(Estado, on_delete=models.SET_NULL, null=True)
    # se le asigna un perfil de empleado que lo administre, puede ser null si no hay
    empleado = models.ForeignKey(Perfil, null=True, blank=True, on_delete=models.SET_NULL)

    minimo_dias_alquiler = models.PositiveIntegerField(default=1, verbose_name="Mínimo de días de alquiler")

    def first_image(self):
            return self.imagenes.first()

    def __str__(self):
        return self.nombre

class Inmueble(models.Model):
    id_inmueble = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    direccion = models.TextField()
    provincia = models.ForeignKey(Provincia, on_delete=models.SET_NULL, null=True)
    ciudad = models.ForeignKey(Ciudad, on_delete=models.SET_NULL, null=True)
    descripcion = models.TextField()
    cantidad_banios = models.IntegerField()
    cantidad_ambientes = models.IntegerField()
    cantidad_camas = models.IntegerField()
    cantidad_huespedes = models.IntegerField()
    precio_por_dia = models.DecimalField(max_digits=10, decimal_places=2)
    politica_cancelacion = models.TextField()
    fecha_publicacion = models.DateField()
    cochera = models.ForeignKey(Cochera, null=True, blank=True, on_delete=models.SET_NULL)
    estado = models.ForeignKey(Estado, on_delete=models.SET_NULL, null=True)
    # se le asigna un perfil de empleado que lo administre, puede ser null si no hay
    empleado = models.ForeignKey(Perfil, null=True, blank=True, on_delete=models.SET_NULL)
    minimo_dias_alquiler = models.PositiveIntegerField(default=1, verbose_name="Mínimo de días de alquiler")

    def first_image(self):
            return self.imagenes.first() 
    
    def __str__(self):
        return self.nombre
    
class InmuebleImagen(models.Model):
    id_imagen = models.AutoField(primary_key=True)
    inmueble = models.ForeignKey(Inmueble, related_name='imagenes', on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='inmuebles/')
    descripcion = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Imagen de {self.inmueble.nombre}"
    
# para el login con 2FA, guardamos el código y la fecha de creación para que expire en 10 minutos
class LoginOTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=6)
    creado_en = models.DateTimeField(default=timezone.now)

    def is_valido(self):
        return (timezone.now() - self.creado_en).total_seconds() < 60

    @staticmethod
    def generar_para_usuario(user):
        codigo = f"{random.randint(0, 999999):06d}"
        otp_obj, _ = LoginOTP.objects.update_or_create(
            user=user,
            defaults={"codigo": codigo, "creado_en": timezone.now()},
        )
        return otp_obj
    