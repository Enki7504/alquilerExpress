from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.conf import settings
from .models import ClienteInmueble, Reserva, Notificacion, Perfil

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