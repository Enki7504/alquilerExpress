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

@shared_task
def cancelar_reservas_vencidas_task():
    ahora = timezone.now()
    estado_aprobada = Estado.objects.get(nombre="Aprobada")
    estado_cancelada, _ = Estado.objects.get_or_create(nombre="Cancelada")
    reservas = Reserva.objects.filter(estado=estado_aprobada, aprobada_en__isnull=False)
    count = 0
    for reserva in reservas:
        if (ahora - reserva.aprobada_en).total_seconds() >= 24 * 3600:
            reserva.estado = estado_cancelada
            reserva.save()
            count += 1
    return count