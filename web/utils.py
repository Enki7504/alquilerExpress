from django.core.mail import send_mail
from django.template import Template, Context
from django.conf import settings
from django.contrib.auth.models import User
from .models import Reserva, ClienteInmueble, Perfil
from django.contrib.auth.tokens import PasswordResetTokenGenerator

from datetime import timedelta

def enviar_mail_a_empleados_sobre_reserva(id_reserva):
    try:
        # Obtener la reserva
        reserva = Reserva.objects.get(id_reserva=id_reserva)

        # Buscar el cliente asociado
        cliente_reserva = ClienteInmueble.objects.get(reserva_id=id_reserva)
        perfil = cliente_reserva.cliente
        nombre_cliente = f"{perfil.usuario.first_name} {perfil.usuario.last_name}"

        # Obtener datos del inmueble
        inmueble = reserva.inmueble
        nombre_inmueble = inmueble.nombre
        id_inmueble = inmueble.id_inmueble
        precio_por_dia = inmueble.precio_por_dia

        # Calcular cantidad de días y total
        cantidad_dias = (reserva.fecha_fin - reserva.fecha_inicio).days
        total = cantidad_dias * precio_por_dia

        # Armar el cuerpo del mensaje
        cuerpo = (
            f"El cliente {nombre_cliente} solicitó una reserva #{reserva.id_reserva} "
            f"para el inmueble #{id_inmueble} - {nombre_inmueble} desde el {reserva.fecha_inicio} "
            f"hasta el {reserva.fecha_fin}. Debe pagar ${precio_por_dia:.2f} por día, "
            f"en total son ${total:.2f} por {cantidad_dias} días. "
            f"¿Desea confirmar la reserva para que el cliente pueda pagar?"
        )

        # Obtener todos los mails de empleados
        empleados = User.objects.filter(is_staff=True)  # Todos los que pueden entrar al admin
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

        print("Mail enviado a empleados")
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