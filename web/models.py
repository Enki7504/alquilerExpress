from django.contrib.auth.models import User
from django.db import models

class Perfil(models.Model):
    id_perfil = models.AutoField(primary_key=True)
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    dni = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.usuario.first_name} {self.usuario.last_name} - DNI: {self.dni}"


class Estado(models.Model):
    id_estado = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Inmueble(models.Model):
    id_inmueble = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    ubicacion = models.TextField()
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
