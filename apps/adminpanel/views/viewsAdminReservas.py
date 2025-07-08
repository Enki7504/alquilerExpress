import json
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST

from ..models import Reserva, Estado, ReservaEstado, ClienteInmueble
from .viewsAdminInmuebles import cambiar_estado_inmueble
from .viewsAdminNotificaciones import crear_notificacion
from ..utils import (
    is_admin_or_empleado,
)


@require_POST
@login_required
@user_passes_test(is_admin_or_empleado)
def cambiar_estado_reserva(request, id_reserva):
    """
    Maneja el cambio de estado para reservas de INMUEBLES y COCHERAS.
    """
    reserva = get_object_or_404(Reserva, id_reserva=id_reserva)
    
    reserva = get_object_or_404(Reserva, id_reserva=id_reserva)
    try:
        data = json.loads(request.body)
        nuevo_estado = data.get('estado')
        comentario = data.get('comentario', '')
    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'error': 'Formato JSON inválido'}, 
            status=400
        )
    
    try:
        estado = Estado.objects.get(nombre=nuevo_estado)
        
        # Validar transiciones de estado permitidas
        transiciones_permitidas = {
            'Pendiente': ['Aprobada', 'Rechazada'],
            'Aprobada': ['Pagada', 'Cancelada', 'Rechazada'],
            'Pagada': ['Confirmada', 'Cancelada'],
            'Confirmada': ['Finalizada', 'Cancelada']
        }
        
        estado_actual = reserva.estado.nombre if reserva.estado else None
        if (estado_actual in transiciones_permitidas and 
            nuevo_estado in transiciones_permitidas[estado_actual]):
            
            # Si pasa a Aprobada, setea aprobada_en
            if nuevo_estado == "Aprobada":
                reserva.aprobada_en = timezone.now()
            reserva.estado = estado
            reserva.save()

            # Registrar en el historial (reservaEstado)
            ReservaEstado.objects.create(
                reserva=reserva,
                estado=estado,
                fecha=timezone.now()
            )

            """
            Envía un mail al cliente asociado a la reserva del inmueble notificando el nuevo estado.
            """
            if reserva.inmueble:
                cliente_rel = ClienteInmueble.objects.filter(reserva=reserva).first()
                if cliente_rel and cliente_rel.cliente.usuario.email:
                    email_cliente = cliente_rel.cliente.usuario.email
                    nombre_cliente = cliente_rel.cliente.usuario.get_full_name() or cliente_rel.cliente.usuario.username
                    
                    asunto = f"Actualización de tu reserva #{reserva.id_reserva}"
                    cuerpo = (
                        f"Hola {nombre_cliente},\n\n"
                        f"El estado de tu reserva #{reserva.id_reserva} para la vivienda {reserva.inmueble.nombre} ha cambiado a: {estado.nombre}.\n"
                    )
                    if comentario:
                        cuerpo += f"\nComentario del administrador: {comentario}\n"
                    cuerpo += (
                        f"\nDetalles de la reserva:\n"
                        f"- Inmueble: {reserva.inmueble}\n"
                        f"- Fechas: {reserva.fecha_inicio} a {reserva.fecha_fin}\n"
                        f"- Estado actual: {estado.nombre}\n"
                    )
                    saldo = 40000  # Este valor puede ser dinámico según tu lógica de negocio
                    if nuevo_estado == "Aprobada":
                        # Construir el link de pago
                        dominio = request.get_host()
                        protocolo = 'https' if request.is_secure() else 'http'
                        url_pago = f"{protocolo}://{dominio}/reservas/{reserva.id_reserva}/pagar/"
                        cuerpo += f"\nAhora debe abonar la reserva, el total es de ${reserva.precio_total}.\n"
                        cuerpo += f"Debe pagar dentro de las próximas 24 horas\n"
                        cuerpo += f"Para pagar presione el siguiente enlace:\n{url_pago}\n"
                    elif nuevo_estado == "Pagada":
                        cuerpo += f"\nLa reserva ha sido pagada. Por favor, espere a que un empleado se comunique con usted.\n"
                    elif nuevo_estado == "Confirmada":
                        cuerpo += f"\nLa reserva ha sido confirmada. ¡Disfrute de su inmueble!\n"
                    elif nuevo_estado == "Finalizada":
                        cuerpo += f"\nLa reserva ha sido finalizada. Esperamos que haya disfrutado de su estancia.\n"
                    elif nuevo_estado == "Cancelada":
                        cuerpo += f"\nLa reserva ha sido cancelada. Si tiene alguna pregunta, por favor contáctenos.\n"
                    elif nuevo_estado == "Rechazada":
                        cuerpo += f"\nLa reserva ha sido rechazada. Si tiene alguna pregunta, por favor contáctenos.\n"

                    # Actualiza el estado del inmueble si es necesario
                    cambiar_estado_inmueble(reserva.id_reserva)

                    cuerpo += f"\nGracias por usar Alquiler Express."

                    if nuevo_estado == "Aprobada":
                        dominio = request.get_host()
                        protocolo = 'https' if request.is_secure() else 'http'
                        url_pago = f"{protocolo}://{dominio}/reservas/{reserva.id_reserva}/pagar/"
                        mensaje_notif = (
                            f"El estado de tu reserva #{reserva.id_reserva} ha cambiado a: {estado.nombre}."
                            f" Ahora debes abonar ${reserva.precio_total}. "
                            f"Accedé al apartado 'Mis Reservas' para pagar."
                            + (f" (Comentario: {comentario})" if comentario else "")
                        )
                    else:
                        mensaje_notif = (
                            f"El estado de tu reserva #{reserva.id_reserva} ha cambiado a: {estado.nombre}"
                            + (f" (Comentario: {comentario})" if comentario else "") + "."
                        )

                    crear_notificacion(
                        usuario=cliente_rel.cliente,
                        mensaje=mensaje_notif
                    )
                    
                    # send_mail(
                    #     subject=asunto,
                    #     message=cuerpo,
                    #     from_email=settings.DEFAULT_FROM_EMAIL,
                    #     recipient_list=[email_cliente],
                    #     fail_silently=False,
                    # )
            elif reserva.cochera:
                cliente_rel = ClienteInmueble.objects.filter(reserva=reserva).first()
                if cliente_rel and cliente_rel.cliente.usuario.email:
                    email_cliente = cliente_rel.cliente.usuario.email
                    nombre_cliente = cliente_rel.cliente.usuario.get_full_name() or cliente_rel.cliente.usuario.username
                    
                    asunto = f"Actualización de tu reserva #{reserva.id_reserva}"
                    cuerpo = (
                        f"Hola {nombre_cliente},\n\n"
                        f"El estado de tu reserva #{reserva.id_reserva} para la cochera {reserva.cochera.nombre} ha cambiado a: {estado.nombre}.\n"
                    )
                    if comentario:
                        cuerpo += f"\nComentario del administrador: {comentario}\n"
                    cuerpo += (
                        f"\nDetalles de la reserva:\n"
                        f"- Cochera: {reserva.cochera}\n"
                        f"- Fechas: {reserva.fecha_inicio} a {reserva.fecha_fin}\n"
                        f"- Estado actual: {estado.nombre}\n"
                    )
                    saldo = 40000  # Este valor puede ser dinámico según tu lógica de negocio
                    if nuevo_estado == "Aprobada":
                        # Construir el link de pago
                        dominio = request.get_host()
                        protocolo = 'https' if request.is_secure() else 'http'
                        url_pago = f"{protocolo}://{dominio}/reservas/{reserva.id_reserva}/pagar/"
                        cuerpo += f"\nAhora debe abonar la reserva, el total es de ${reserva.precio_total}.\n"
                        cuerpo += f"Debe pagar dentro de las próximas 24 horas\n"
                        cuerpo += f"Para pagar presione el siguiente enlace:\n{url_pago}\n"
                    elif nuevo_estado == "Pagada":
                        cuerpo += f"\nLa reserva ha sido pagada. Por favor, espere a que un empleado se comunique con usted.\n"
                    elif nuevo_estado == "Confirmada":
                        cuerpo += f"\nLa reserva ha sido confirmada. ¡Disfrute de su cochera!\n"
                    elif nuevo_estado == "Finalizada":
                        cuerpo += f"\nLa reserva ha sido finalizada. Esperamos que haya disfrutado de su estancia.\n"
                    elif nuevo_estado == "Cancelada":
                        cuerpo += f"\nLa reserva ha sido cancelada. Si tiene alguna pregunta, por favor contáctenos.\n"
                    elif nuevo_estado == "Rechazada":
                        cuerpo += f"\nLa reserva ha sido rechazada. Si tiene alguna pregunta, por favor contáctenos.\n"

                    cuerpo += f"\nGracias por usar Alquiler Express."

                    # Actualiza el estado de la cochera si es necesario
                    cambiar_estado_inmueble(reserva.id_reserva)
                    
                    if nuevo_estado == "Aprobada":
                        dominio = request.get_host()
                        protocolo = 'https' if request.is_secure() else 'http'
                        url_pago = f"{protocolo}://{dominio}/reservas/{reserva.id_reserva}/pagar/"
                        mensaje_notif = (
                            f"El estado de tu reserva #{reserva.id_reserva} ha cambiado a: {estado.nombre}."
                            f" Ahora debes abonar ${reserva.precio_total} dentro de las próximas 24 horas. "
                            f"Accedé al apartado 'Mis Reservas' para pagar."
                            + (f" (Comentario: {comentario})" if comentario else "")
                        )
                    else:
                        mensaje_notif = (
                            f"El estado de tu reserva #{reserva.id_reserva} ha cambiado a: {estado.nombre}"
                            + (f" (Comentario: {comentario})" if comentario else "") + "."
                        )

                    crear_notificacion(
                        usuario=cliente_rel.cliente,
                        mensaje=mensaje_notif
                    )

                    
                    # send_mail(
                    #     subject=asunto,
                    #     message=cuerpo,
                    #     from_email=settings.DEFAULT_FROM_EMAIL,
                    #     recipient_list=[email_cliente],
                    #     fail_silently=False,
                    # )
            
            # Opcional: Registrar en historial (si tienes un modelo para ello)
            # HistorialEstadoReserva.objects.create(
            #     reserva=reserva,
            #     estado=estado,
            #     usuario=request.user,
            #     comentario=comentario,
            #     tipo='COCHERA' if reserva.cochera else 'INMUEBLE'
            # )
            
            return JsonResponse({
                'success': True,
                'tipo': 'COCHERA' if reserva.cochera else 'INMUEBLE'  # Para debug/frontend
            })
        else:
            return JsonResponse(
                {'success': False, 'error': 'Transición no permitida'}, 
                status=400
            )
            
    except Estado.DoesNotExist:
        return JsonResponse(
            {'success': False, 'error': 'Estado no válido'}, 
            status=400
        )
