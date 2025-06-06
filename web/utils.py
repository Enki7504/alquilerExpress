from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.conf import settings
from .models import ClienteInmueble, Reserva

def notificar_cambio_estado_reserva(reserva, nuevo_estado, comentario=None):
    """
    Envía un mail al cliente asociado a la reserva notificando el nuevo estado.
    """
    try:
        # Buscar el cliente asociado a la reserva
        cliente_rel = ClienteInmueble.objects.filter(reserva=reserva).first()
        if not cliente_rel or not cliente_rel.cliente.usuario.email:
            print("No se encontró cliente asociado o no tiene email.")
            return False

        email_cliente = cliente_rel.cliente.usuario.email
        nombre_cliente = cliente_rel.cliente.usuario.get_full_name() or cliente_rel.cliente.usuario.username

        asunto = f"Actualización de tu reserva #{reserva.id_reserva}"
        cuerpo = (
            f"Hola {nombre_cliente},\n\n"
            f"El estado de tu reserva #{reserva.id_reserva} ha cambiado a: {nuevo_estado}.\n"
        )
        if comentario:
            cuerpo += f"\nComentario del administrador: {comentario}\n"
        cuerpo += (
            f"\nDetalles de la reserva:\n"
            f"- Inmueble: {reserva.inmueble or reserva.cochera}\n"
            f"- Fechas: {reserva.fecha_inicio} a {reserva.fecha_fin}\n"
            f"- Estado actual: {nuevo_estado}\n"
            f"\nGracias por usar Alquiler Express."
        )

        send_mail(
            subject=asunto,
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email_cliente],
            fail_silently=False,
        )
        print(f"Notificación enviada a {email_cliente}")
        return True
    except Exception as e:
        print("Error al notificar al cliente:", e)
        return False


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
            f"Para aceptar la reserva, haga click en el siguiente enlace: "
            f"http://localhost:8000/reservas/confirmar/{reserva.id_reserva}/"
            f"Para rechazar la reserva, haga click en el siguiente enlace: "
            f"http://localhost:8000/reservas/rechazar/{reserva.id_reserva}/"
            f"Para ver la reserva, haga click en el siguiente enlace: "
            f"http://localhost:8000/reservas/{reserva.id_reserva}/"
        )

        # Obtener todos los mails de empleados
        empleados_group = Group.objects.get(name="empleados")
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

# Enviar mail al cliente sobre la reserva
