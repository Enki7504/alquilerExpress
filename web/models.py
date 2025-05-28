from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from datetime import timedelta

class Perfil(models.Model):
    id_perfil = models.AutoField(primary_key=True)
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    dni = models.CharField(max_length=20)

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

class Inmueble(models.Model):
    id_inmueble = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    ubicacion = models.TextField()
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
    cochera = models.BooleanField()
    estado = models.ForeignKey(Estado, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.nombre


class Cochera(models.Model):
    id_cochera = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    alto = models.FloatField()
    ancho = models.FloatField()
    largo = models.FloatField()
    cantidad_vehiculos = models.IntegerField()
    con_techo = models.BooleanField()
    descripcion = models.TextField()
    ubicacion = models.TextField()
    provincia = models.ForeignKey(Provincia, on_delete=models.SET_NULL, null=True)
    ciudad = models.ForeignKey(Ciudad, on_delete=models.SET_NULL, null=True)
    precio_por_dia = models.DecimalField(max_digits=10, decimal_places=2)
    politica_cancelacion = models.TextField()
    fecha_publicacion = models.DateField()
    estado = models.ForeignKey(Estado, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.nombre


class InmuebleCochera(models.Model):
    id_inmueble_cochera = models.AutoField(primary_key=True)
    inmueble = models.ForeignKey(Inmueble, on_delete=models.CASCADE)
    cochera = models.ForeignKey(Cochera, on_delete=models.CASCADE)


class Reserva(models.Model):
    id_reserva = models.AutoField(primary_key=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    precio_total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.ForeignKey(Estado, on_delete=models.SET_NULL, null=True)  # Aquí está el estado FK
    inmueble = models.ForeignKey(Inmueble, null=True, blank=True, on_delete=models.SET_NULL)
    cochera = models.ForeignKey(Cochera, null=True, blank=True, on_delete=models.SET_NULL)
    descripcion = models.TextField()

    def __str__(self):
        return f"Reserva #{self.id_reserva} - Estado: {self.estado.nombre if self.estado else 'Sin estado'}"


class ReservaEstado(models.Model):
    id_reserva_estado = models.AutoField(primary_key=True)
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE)
    estado = models.ForeignKey(Estado, on_delete=models.CASCADE)
    fecha = models.DateTimeField()


class InmuebleEstado(models.Model):
    id_inmueble_estado = models.AutoField(primary_key=True)
    inmueble_cochera = models.ForeignKey(InmuebleCochera, on_delete=models.CASCADE)
    estado = models.ForeignKey(Estado, on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)


class ClienteInmueble(models.Model):
    id_cliente_inmueble = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(Perfil, on_delete=models.CASCADE)  # FK a Perfil, no Usuario
    inmueble = models.ForeignKey(Inmueble, null=True, blank=True, on_delete=models.SET_NULL)
    cochera = models.ForeignKey(Cochera, null=True, blank=True, on_delete=models.SET_NULL)
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE)


class Resenia(models.Model):
    id_resenia = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Perfil, on_delete=models.CASCADE)  # FK a Perfil
    inmueble = models.ForeignKey(Inmueble, null=True, blank=True, on_delete=models.SET_NULL)
    cochera = models.ForeignKey(Cochera, null=True, blank=True, on_delete=models.SET_NULL)
    titulo = models.CharField(max_length=200)
    calificacion = models.IntegerField()
    descripcion = models.TextField()


class Comentario(models.Model):
    id_comentario = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Perfil, on_delete=models.CASCADE)  # FK a Perfil
    inmueble = models.ForeignKey(Inmueble, null=True, blank=True, on_delete=models.SET_NULL)
    cochera = models.ForeignKey(Cochera, null=True, blank=True, on_delete=models.SET_NULL)
    descripcion = models.TextField()


# Para guardar imagenes de inmuebles y cocheras
class InmuebleImagen(models.Model):
    id_imagen = models.AutoField(primary_key=True)
    inmueble = models.ForeignKey(Inmueble, related_name='imagenes', on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='inmuebles/')
    descripcion = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Imagen de {self.inmueble.nombre}"

class CocheraImagen(models.Model):
    id_imagen = models.AutoField(primary_key=True)
    cochera = models.ForeignKey(Cochera, related_name='imagenes', on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='cocheras/')
    descripcion = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Imagen de {self.cochera.nombre}"

# para el login con 2FA, guardamos el código y la fecha de creación para que expire en 10 minutos
class LoginOTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=6)
    creado_en = models.DateTimeField(auto_now_add=True)

    def is_valido(self):
        # Verifica si el código es válido (dentro de 10 minutos)        
        return timezone.now() < self.creado_en + timedelta(minutes=10)