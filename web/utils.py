from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.conf import settings
from .models import ClienteInmueble, Reserva
from django.contrib.auth.models import Group

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

        # Obtener datos del inmueble o cochera
        if reserva.inmueble:
            nombre_obj = f"inmueble #{reserva.inmueble.id_inmueble} - {reserva.inmueble.nombre}"
            precio_por_dia = reserva.inmueble.precio_por_dia
        elif reserva.cochera:
            nombre_obj = f"cochera #{reserva.cochera.id_cochera} - {reserva.cochera.nombre}"
            precio_por_dia = reserva.cochera.precio_por_dia
        else:
            nombre_obj = "reserva"
            precio_por_dia = 0

        # Calcular cantidad de días y total
        cantidad_dias = (reserva.fecha_fin - reserva.fecha_inicio).days
        total = cantidad_dias * float(precio_por_dia)

        # Armar el cuerpo del mensaje
        cuerpo = (
            f"El cliente {nombre_cliente} solicitó una reserva #{reserva.id_reserva} "
            f"para el {nombre_obj} desde el {reserva.fecha_inicio} hasta el {reserva.fecha_fin}. "
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

        # Obtener todos los mails de empleados (grupo "empleado")
        try:
            empleados_group = Group.objects.get(name="empleado")
        except Group.DoesNotExist:
            print("No existe el grupo 'empleado'.")
            return False

        empleados = empleados_group.user_set.all()
        lista_mails = [emp.email for emp in empleados if emp.email]

        if not lista_mails:
            print("No hay empleados con mail definido.")
            return False

        # Enviar el mail
        send_mail(
            subject="Nueva solicitud de reserva",
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=lista_mails,
            fail_silently=False,
        )

        print("Mail enviado a empleados:", lista_mails)
        return True

    except Exception as e:
        print("Error al enviar mail a empleados:", e)
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
