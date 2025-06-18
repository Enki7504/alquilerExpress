from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.conf import settings
from django.db import models
from .models import ClienteInmueble, Reserva, Notificacion, Perfil, Estado

#comando para ejecutar el script en consola
# python manage.py shell
#from web.utils import enviar_mail_a_empleados_sobre_reserva
#from web.models import Reserva
#enviar_mail_a_empleados_sobre_reserva(1)


def enviar_mail_a_empleados_sobre_reserva(id_reserva):
    try:
        # Obtener la reserva
        reserva = Reserva.objects.get(id_reserva=id_reserva)

        # Buscar el cliente asociado
        cliente_reserva = ClienteInmueble.objects.filter(reserva_id=id_reserva).first()
        if not cliente_reserva:
            print("No se encontró cliente asociado a la reserva.")
            return False
        perfil = cliente_reserva.cliente
        nombre_cliente = f"{perfil.usuario.first_name} {perfil.usuario.last_name}"

        # Obtener datos del inmueble o cochera y el empleado asignado
        empleado_perfil = None
        empleado_email = None
        if reserva.inmueble and reserva.inmueble.empleado:
            nombre_obj = f"vivienda #{reserva.inmueble.id_inmueble} - {reserva.inmueble.nombre}"
            precio_por_dia = reserva.inmueble.precio_por_dia
            empleado_perfil = reserva.inmueble.empleado
            empleado_email = empleado_perfil.usuario.email
        elif reserva.cochera and reserva.cochera.empleado:
            nombre_obj = f"cochera #{reserva.cochera.id_cochera} - {reserva.cochera.nombre}"
            precio_por_dia = reserva.cochera.precio_por_dia
            empleado_perfil = reserva.cochera.empleado
            empleado_email = empleado_perfil.usuario.email
        else:
            nombre_obj = "reserva"
            precio_por_dia = 0

        if not empleado_email or not empleado_perfil:
            print("No hay empleado asignado al inmueble o cochera, o no tiene email.")
            return False

        # Calcular cantidad de días y total
        cantidad_dias = (reserva.fecha_fin - reserva.fecha_inicio).days
        total = cantidad_dias * float(precio_por_dia)

        # Armar el cuerpo del mensaje
        cuerpo = (
            f"El cliente {nombre_cliente} solicitó una reserva #{reserva.id_reserva} "
            f"para la {nombre_obj} desde el {reserva.fecha_inicio} hasta el {reserva.fecha_fin}. "
            f"Debe pagar ${precio_por_dia:.2f} por día, en total son ${total:.2f} por {cantidad_dias} días. "
            f"¿Desea confirmar la reserva para que el cliente pueda pagar?\n"
            f"Para aceptar o rechazar la reserva, haga click en el siguiente enlace: "
        )
        if reserva.inmueble:
            cuerpo += (
                f"http://localhost:8000/panel/inmuebles/reservas/{reserva.inmueble.id_inmueble}/"
            )
        elif reserva.cochera:
            cuerpo += (
                f"http://localhost:8000/panel/cocheras/reservas/{reserva.cochera.id_cochera}/"
            )

        # --- AGREGAR NOTIFICACIÓN AL EMPLEADO ---
        crear_notificacion(
            usuario=empleado_perfil,
            mensaje=f"Tienes una nueva solicitud de reserva #{reserva.id_reserva} para la {nombre_obj}."
        )
        # ----------------------------------------


        # Enviar el mail solo al empleado asignado
        send_mail(
            subject="Nueva solicitud de reserva",
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[empleado_email],
            fail_silently=False,
        )

        print("Mail enviado a empleado:", empleado_email)
        return True

    except Exception as e:
        print("Error al enviar mail a empleado:", e)
        return False

#si borro esto da error, no se porque
class EmailLinkTokenGenerator(PasswordResetTokenGenerator):
    """
    Genera tokens únicos ligados al usuario y su estado.
    """
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.is_active}"

# instanciamos un generador
email_link_token = EmailLinkTokenGenerator()

# Enviar mail al cliente sobre la reserva

def crear_notificacion(usuario, mensaje):
    """
    Crea una notificación para el usuario indicado.
    """
    notificacion = Notificacion.objects.create(
        usuario=usuario,
        mensaje=mensaje
    )
    print(f"Notificación creada para {usuario.usuario.username}: {mensaje}")
    return notificacion

# Actuliza estado de un inmueble o cochera, recibe id_reserva
def cambiar_estado_inmueble(id_reserva):
    """
    Actuliza el estado del inmueble o cochera asociado.
    """
    try:
        reserva = Reserva.objects.get(id_reserva=id_reserva)
        
        # Cambiar el estado del inmueble o cochera

        if reserva.inmueble:
            if hay_reserva_confirmada_hoy(id_reserva):
                # Buscar o crear el estado
                estado_obj, _ = Estado.objects.get_or_create(nombre="Ocupado")
            else:
                # Buscar o crear el estado
                estado_obj, _ = Estado.objects.get_or_create(nombre="Disponible")
            inmueble = reserva.inmueble
            inmueble.estado = estado_obj
            inmueble.save()
            print(f"Estado del inmueble #{inmueble.id_inmueble} cambiado a {estado_obj.nombre}.")
        elif reserva.cochera:
            cochera = reserva.cochera
            if hay_reserva_confirmada_hoy(id_reserva):
                # Buscar o crear el estado
                estado_obj, _ = Estado.objects.get_or_create(nombre="Ocupado")
            else:
                # Buscar o crear el estado
                estado_obj, _ = Estado.objects.get_or_create(nombre="Disponible")
            cochera.estado = estado_obj
            cochera.save()
            print(f"Estado de la cochera #{cochera.id_cochera} cambiado a {estado_obj.nombre}.")
        else:
            print("Reserva no tiene asociado ni inmueble ni cochera.")
            return False
        return True
    except Exception as e:
        print("Error al cambiar estado de reserva:", e)
        return False
    
def hay_reserva_confirmada_hoy(id_reserva):
    """
    Dado el id_reserva, busca si el inmueble y/o cochera asociados tienen una reserva en estado 'Confirmada'
    que se superponga con ayer, hoy o mañana (date.today() - 1, date.today(), date.today() + 1).
    Retorna True si existe, False si no.
    """
    try:
        reserva = Reserva.objects.get(id_reserva=id_reserva)
        hoy = date.today()
        dias_a_verificar = [hoy - timedelta(days=1), hoy, hoy + timedelta(days=1)]

        # Buscar en inmueble
        if reserva.inmueble:
            existe_inmueble = Reserva.objects.filter(
                inmueble=reserva.inmueble,
                estado__nombre="Confirmada"
            ).exclude(id_reserva=reserva.id_reserva).filter(
                # Al menos uno de los días está dentro del rango de la reserva
                *(
                    [
                        (
                            models.Q(fecha_inicio__lte=dia) &
                            models.Q(fecha_fin__gte=dia)
                        ) for dia in dias_a_verificar
                    ]
                )
            ).exists()
            if existe_inmueble:
                return True

        # Buscar en cochera
        if reserva.cochera:
            existe_cochera = Reserva.objects.filter(
                cochera=reserva.cochera,
                estado__nombre="Confirmada"
            ).exclude(id_reserva=reserva.id_reserva).filter(
                *(
                    [
                        (
                            models.Q(fecha_inicio__lte=dia) &
                            models.Q(fecha_fin__gte=dia)
                        ) for dia in dias_a_verificar
                    ]
                )
            ).exists()
            if existe_cochera:
                return True

        return False
    except Exception as e:
        print("Error al buscar reserva confirmada:", e)
        return False

################################################################################################################
# --- Funciones de Ayuda para Permisos ---
################################################################################################################

def is_admin(user):
    """Verifica si el usuario es un superusuario."""
    return user.is_authenticated and user.is_staff

def is_empleado(user):
    """Verifica si el usuario es un superusuario."""
    return user.is_authenticated and user.groups.filter(name="empleado").exists()

def is_admin_or_empleado(user):
    """Verifica si el usuario es un superusuario o pertenece al grupo 'empleado'."""
    return user.is_authenticated and (user.is_staff or user.groups.filter(name="empleado").exists())

def is_client(user):
    """Verifica si el usuario es un cliente."""
    return user.is_authenticated and user.groups.filter(name="cliente").exists()