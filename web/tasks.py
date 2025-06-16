from celery import shared_task
from django.utils import timezone
from web.models import Reserva, Estado, ClienteInmueble
from web.utils import crear_notificacion

@shared_task
def rechazar_reservas_pendientes():
    estado_pendiente = Estado.objects.get(nombre='Pendiente')
    estado_rechazada = Estado.objects.get(nombre='Rechazada')
    ahora = timezone.now()
    reservas = Reserva.objects.filter(
        estado=estado_pendiente,
        creada_en__lte=ahora - timezone.timedelta(hours=72)
    )
    for reserva in reservas:
        reserva.estado = estado_rechazada
        reserva.save()
        cliente_rel = ClienteInmueble.objects.filter(reserva=reserva).first()
        if cliente_rel:
            crear_notificacion(
                usuario=cliente_rel.cliente,
                mensaje=f"Tu reserva #{reserva.id_reserva} fue rechazada."
            )