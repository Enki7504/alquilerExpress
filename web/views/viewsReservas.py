import json
import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta
from django.utils import timezone
from datetime import datetime, timedelta, time

# Importaciones de modelos locales
from ..models import (
    Inmueble,
    Reserva,
    ClienteInmueble,
    Estado,
    Cochera,
    ReservaEstado,
    Cochera,
    Huesped,
    Tarjeta,
    ExtensionReserva
)

# Importaciones de utilidades locales
from ..utils import (
    crear_notificacion,
    cambiar_estado_inmueble,
    is_admin_or_empleado,
    is_client
)

################################################################################################################
# --- Vistas de Gestión de Reservas ---
################################################################################################################

@login_required
def crear_reserva_inmueble(request, id_inmueble):
    """
    Permite a un cliente crear una reserva para un inmueble
    """
    # Verificar que el cliente no esté bloqueado
    if not request.user.is_active:
        messages.error(request, "Tu cuenta está bloqueada. No puedes realizar reservas.")
        return redirect("detalle_inmueble", id_inmueble=id_inmueble)
    
    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
    perfil = request.user.perfil

    if request.method == "POST":
        # Obtener fechas del formulario
        fecha_inicio_str = request.POST.get("fecha_inicio")
        fecha_fin_str = request.POST.get("fecha_fin")
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            messages.error(request, "Fechas inválidas.")
            return redirect("detalle_inmueble", id_inmueble=id_inmueble)

        # Validar que la fecha de inicio sea anterior a la de fin
        if fecha_inicio >= fecha_fin:
            messages.error(request, "La fecha de salida debe ser posterior a la de llegada.")
            return redirect("detalle_inmueble", id_inmueble=id_inmueble)

        # Validar mínimo de noches
        dias = (fecha_fin - fecha_inicio).days
        if dias < inmueble.minimo_dias_alquiler:
            messages.error(request, f"El mínimo de noches de alquiler para esta vivienda es {inmueble.minimo_dias_alquiler}.")
            return redirect("detalle_inmueble", id_inmueble=id_inmueble)

        # Validar cantidad de adultos y niños
        try:
            cantidad_adultos = int(request.POST.get("cantidad_adultos", 1))
            cantidad_ninos = int(request.POST.get("cantidad_ninos", 0))
        except (TypeError, ValueError):
            messages.error(request, "Cantidad de huéspedes inválida.")
            return redirect("detalle_inmueble", id_inmueble=id_inmueble)

        # Validar que haya al menos 1 adulto
        if cantidad_adultos < 1:
            messages.error(request, "Debe haber al menos 1 adulto.")
            return redirect("detalle_inmueble", id_inmueble=id_inmueble)

        # Validar que no se exceda la capacidad del inmueble
        total_huespedes = cantidad_adultos + cantidad_ninos
        if total_huespedes > inmueble.cantidad_huespedes:
            messages.error(request, f"El total de huéspedes ({total_huespedes}) excede la capacidad del inmueble ({inmueble.cantidad_huespedes}).")
            return redirect("detalle_inmueble", id_inmueble=id_inmueble)

        # Validar que haya al menos 1 huésped en total
        if total_huespedes < 1:
            messages.error(request, "Debe haber al menos 1 huésped.")
            return redirect("detalle_inmueble", id_inmueble=id_inmueble)

        # Validar que el cliente no tenga reservas superpuestas para el mismo inmueble
        reserva_superpuesta_usuario = Reserva.objects.filter(
            clienteinmueble__cliente=perfil,
            inmueble=inmueble,
            estado__nombre__in=['Pendiente', 'Confirmada', 'Pagada', 'Aprobada'],
            fecha_inicio__lte=fecha_fin,  
            fecha_fin__gte=fecha_inicio   
        ).exists()
        if reserva_superpuesta_usuario:
            messages.error(request, "Ya tienes una reserva activa para este inmueble en esas fechas.")
            return redirect("detalle_inmueble", id_inmueble=id_inmueble)

        # Validar que el inmueble esté disponible en esas fechas
        reserva_superpuesta_inmueble = Reserva.objects.filter(
            inmueble=inmueble,
            estado__nombre__in=['Confirmada', 'Pagada', 'Aprobada'],
            fecha_inicio__lte=fecha_fin,  
            fecha_fin__gte=fecha_inicio   
        ).exists()
        if reserva_superpuesta_inmueble:
            messages.error(request, "El inmueble no está disponible en esas fechas.")
            return redirect("detalle_inmueble", id_inmueble=id_inmueble)

        # Crear la reserva
        reserva = Reserva.objects.create(
            inmueble=inmueble,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=Estado.objects.get(nombre="Pendiente"),
            precio_total=inmueble.precio_por_dia * (fecha_fin - fecha_inicio).days,
            cantidad_adultos=cantidad_adultos,
            cantidad_ninos=cantidad_ninos
        )

        # Relacionar el cliente con la reserva
        ClienteInmueble.objects.create(
            cliente=perfil,
            reserva=reserva
        )

        crear_notificacion(
            usuario=perfil,
            mensaje=f"Tu reserva #{reserva.id_reserva} fue registrada. En menos de 72 horas será revisada por un empleado. Recibirás una notificación cuando sea aprobada o rechazada."
        )

        messages.success(request, "Reserva creada exitosamente.")
        return redirect("detalle_inmueble", id_inmueble=id_inmueble)

    # Si es GET, redirigir al detalle del inmueble
    return redirect("detalle_inmueble", id_inmueble=id_inmueble)

@login_required
def crear_reserva_cochera(request, id_cochera):
    """
    Permite a un cliente crear una reserva para una cochera
    """
    # Verificar que el cliente no esté bloqueado
    if not request.user.is_active:
        messages.error(request, "Tu cuenta está bloqueada. No puedes realizar reservas.")
        return redirect("detalle_cochera", id_cochera=id_cochera)
    
    cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
    perfil = request.user.perfil

    if request.method == 'POST':
        # Validar fechas
        try:
            fecha_inicio_date = request.POST.get("fecha_inicio_date")
            fecha_inicio_time = request.POST.get("fecha_inicio_time")
            fecha_fin_date = request.POST.get("fecha_fin_date")
            fecha_fin_time = request.POST.get("fecha_fin_time")
            
            # También verificar si vienen los campos combinados (fallback)
            fecha_inicio_combined = request.POST.get("fecha_inicio")
            fecha_fin_combined = request.POST.get("fecha_fin")
            
            if fecha_inicio_combined and fecha_fin_combined:
                # Si vienen combinados, usarlos
                fecha_inicio = datetime.strptime(fecha_inicio_combined, "%Y-%m-%d %H:%M")
                fecha_fin = datetime.strptime(fecha_fin_combined, "%Y-%m-%d %H:%M")
            elif fecha_inicio_date and fecha_inicio_time and fecha_fin_date and fecha_fin_time:
                # Si vienen separados, combinarlos
                fecha_inicio_str = f"{fecha_inicio_date} {fecha_inicio_time}"
                fecha_fin_str = f"{fecha_fin_date} {fecha_fin_time}"
                fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d %H:%M")
                fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d %H:%M")
            else:
                raise ValueError("Faltan datos de fecha u hora")
                
        except (TypeError, ValueError) as e:
            print(f"Error parseando fechas: {e}")
            print(f"POST data: {request.POST}")
            messages.error(request, 'Fechas inválidas. Verifique que haya seleccionado fecha y hora.')
            return redirect('detalle_cochera', id_cochera=id_cochera)

        if fecha_inicio >= fecha_fin:
            messages.error(request, 'La fecha y hora de salida debe ser posterior a la de llegada.')
            return redirect('detalle_cochera', id_cochera=id_cochera)

        # Validar mínimo de horas
        delta = fecha_fin - fecha_inicio
        horas = delta.total_seconds() / 60 / 60
        if horas < cochera.minimo_dias_alquiler:
            messages.error(request, f"El mínimo de horas de alquiler para esta cochera es {cochera.minimo_dias_alquiler}.")
            return redirect('detalle_cochera', id_cochera=id_cochera)

        # Validar que el cliente no tenga reservas superpuestas para la misma cochera
        # CORREGIDO: Comparar datetime completo, no solo fechas
        reserva_superpuesta_usuario = Reserva.objects.filter(
            clienteinmueble__cliente=perfil,
            cochera=cochera,
            estado__nombre__in=['Pendiente', 'Confirmada', 'Pagada', 'Aprobada'],
            fecha_inicio__lt=fecha_fin,      # Cambio: __lt en lugar de __lte
            fecha_fin__gt=fecha_inicio       # Cambio: __gt en lugar de __gte
        ).exists()
        if reserva_superpuesta_usuario:
            messages.error(request, "Ya tenés una reserva activa para esta cochera en esas fechas y horarios.")
            return redirect('detalle_cochera', id_cochera=id_cochera)

        # Validar que la cochera esté disponible en esas fechas y horarios
        # CORREGIDO: Comparar datetime completo, no solo fechas
        reserva_superpuesta_cochera = Reserva.objects.filter(
            cochera=cochera,
            estado__nombre__in=['Confirmada', 'Pagada', 'Aprobada'],
            fecha_inicio__lt=fecha_fin,      # Cambio: __lt en lugar de __lte
            fecha_fin__gt=fecha_inicio       # Cambio: __gt en lugar de __gte
        ).exists()
        if reserva_superpuesta_cochera:
            messages.error(request, "La cochera no está disponible en esas fechas y horarios.")
            return redirect('detalle_cochera', id_cochera=id_cochera)

        # Calcular precio total
        precio_total = cochera.precio_por_dia * int(horas)

        # Crear la reserva
        reserva = Reserva.objects.create(
            cochera=cochera,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=Estado.objects.get(nombre='Pendiente'),
            precio_total=precio_total,
            descripcion=f"Reserva para {cochera.nombre} del {fecha_inicio} al {fecha_fin}"
        )

        # Relacionar el cliente con la reserva
        ClienteInmueble.objects.create(
            cliente=perfil,
            cochera=cochera,
            reserva=reserva
        )

        # Notificar al cliente
        crear_notificacion(
            usuario=perfil,
            mensaje=f"Tu reserva #{reserva.id_reserva} fue registrada. En menos de 72 horas será revisada por un empleado. Recibirás una notificación cuando sea aprobada o rechazada."
        )

        # Notificar al empleado asignado a la cochera
        if cochera.empleado:
            crear_notificacion(
                usuario=cochera.empleado,
                mensaje=f"Nueva reserva #{reserva.id_reserva} pendiente para la cochera {cochera.nombre} del {fecha_inicio} al {fecha_fin}.",
            )

        messages.success(request, 'Reserva creada exitosamente.')
        return redirect('detalle_cochera', id_cochera=id_cochera)

    return redirect('detalle_cochera', id_cochera=id_cochera)

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
            'Concurrente': ['Aprobada', 'Rechazada'],
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
                
                # ✅ Cancelar automáticamente reservas superpuestas
                estado_cancelada = Estado.objects.get(nombre='Cancelada')
                
                # Para inmuebles
                if reserva.inmueble:
                    reservas_superpuestas = Reserva.objects.filter(
                        inmueble=reserva.inmueble,
                        estado__nombre__in=['Pendiente'],
                        fecha_inicio__lt=reserva.fecha_fin,
                        fecha_fin__gt=reserva.fecha_inicio
                    ).exclude(id_reserva=reserva.id_reserva)
                    
                    for r in reservas_superpuestas:
                        #r.estado = estado_cancelada
                        #r.save()

                        # Cambia el estado de la reserva a "Concurrente"
                        r.estado, _ = Estado.objects.get_or_create(nombre='Concurrente')
                        r.save()

                        
                        # Notificar al cliente afectado
                        #cliente_rel = ClienteInmueble.objects.filter(reserva=r).first()
                        #if cliente_rel:
                        #    crear_notificacion(
                        #        usuario=cliente_rel.cliente,
                        #        mensaje=f"Tu reserva #{r.id_reserva} para '{reserva.inmueble.nombre}' del {r.fecha_inicio} al {r.fecha_fin} fue cancelada automáticamente porque se aprobó otra reserva en fechas superpuestas."
                        #    )
                
                # Para cocheras
                elif reserva.cochera:
                    reservas_superpuestas = Reserva.objects.filter(
                        cochera=reserva.cochera,
                        estado__nombre__in=['Pendiente'],
                        fecha_inicio__lt=reserva.fecha_fin,
                        fecha_fin__gt=reserva.fecha_inicio
                    ).exclude(id_reserva=reserva.id_reserva)
                    
                    for r in reservas_superpuestas:
                        #r.estado = estado_cancelada
                        #r.save()

                        r.estado = Estado.objects.get_or_create(nombre='Concurrente')
                        r.save()
                        
                        # Notificar al cliente afectado
                        #cliente_rel = ClienteInmueble.objects.filter(reserva=r).first()
                        #if cliente_rel:
                        #    crear_notificacion(
                        #        usuario=cliente_rel.cliente,
                        #        mensaje=f"Tu reserva #{r.id_reserva} para '{reserva.cochera.nombre}' del {r.fecha_inicio} al {r.fecha_fin} fue cancelada automáticamente porque se aprobó otra reserva en horarios superpuestos."
                        #    )

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
                        cuerpo += f"\n¡Nos encantaría conocer tu experiencia! Te invitamos a dejar una reseña sobre tu estadía para ayudar a otros huéspedes a tomar la mejor decisión.\n"
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
                        # Agregar que se cancelen todas las reservas que esten dentro del mismo lapso de la reserva que se acepta
                        
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
                        cuerpo += f"\n¡Nos encantaría conocer tu experiencia! Te invitamos a dejar una reseña sobre tu estadía para ayudar a otros huéspedes a tomar la mejor decisión.\n"
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

################################################################################################################
# --- DETALLE DE RESERVAS  ---
################################################################################################################

@login_required
def reservas_usuario(request):
    """
    Muestra todas las reservas del usuario autenticado.
    """
    reservas = Reserva.objects.filter(clienteinmueble__cliente=request.user.perfil).distinct().order_by('-id_reserva')
    return render(request, 'reservas.html', {
        'reservas': reservas
    })

@login_required
def ver_detalle_reserva(request, id_reserva):
    reserva = get_object_or_404(Reserva, id_reserva=id_reserva)
    huespedes = list(Huesped.objects.filter(reserva=reserva))

    # Agregar al titular como huésped si tiene datos válidos
    cliente_principal = reserva.cliente()
    if cliente_principal:
        ya_esta = any(
            h.dni == cliente_principal.dni
            for h in huespedes
        )
        if not ya_esta:
            huesped_titular = Huesped(
                reserva=reserva,
                nombre=cliente_principal.usuario.first_name,
                apellido=cliente_principal.usuario.last_name,
                dni=cliente_principal.dni,
                fecha_nacimiento=cliente_principal.fecha_nacimiento
            )
            huespedes.insert(0, huesped_titular)

    # Mapear datos para precargar inputs
    huespedes_precargados = {}
    for i, huesped in enumerate(huespedes):
        huespedes_precargados[f'nombre_{i}'] = huesped.nombre
        huespedes_precargados[f'apellido_{i}'] = huesped.apellido
        huespedes_precargados[f'dni_{i}'] = huesped.dni
        huespedes_precargados[f'fecha_nacimiento_{i}'] = huesped.fecha_nacimiento.strftime('%Y-%m-%d') if huesped.fecha_nacimiento else ''

    # Calcular tiempo restante desde la creación (72 horas)
    tiempo_restante_creacion = None
    if reserva.estado.nombre == "Pendiente":
        tiempo_limite_creacion = reserva.creada_en + timedelta(hours=72)  # Cambio aquí
        ahora = timezone.now()
        if ahora < tiempo_limite_creacion:
            tiempo_restante_creacion = (tiempo_limite_creacion - ahora).total_seconds()
        else:
            tiempo_restante_creacion = 0

    # Calcular tiempo restante para pagar (24 horas desde aprobación)
    tiempo_restante = None
    if reserva.estado.nombre == "Aprobada":
        # Asegurar que ambos sean datetime
        fecha_aprobacion = reserva.aprobada_en  # Debe ser datetime
        if fecha_aprobacion:
            tiempo_limite = fecha_aprobacion + timedelta(hours=24)
            ahora = timezone.now()
            tiempo_restante = max(0, (tiempo_limite - ahora).total_seconds())
    
    # Verificar si puede extender y calcular cuándo podrá hacerlo
    puede_extender = False
    fecha_disponible_extension = None
    horas_para_extension = None
    
    if reserva.estado.nombre == 'Confirmada' and not is_admin_or_empleado(request.user):
        # Usar localtime para obtener la fecha/hora actual con la zona horaria correcta
        ahora = timezone.localtime()
        
        # Convertir fecha_fin a datetime con la misma zona horaria
        fecha_fin_datetime = timezone.localtime(
            timezone.make_aware(
                datetime.combine(reserva.fecha_fin, datetime.min.time().replace(hour=23, minute=59, second=59))
            )
        )
        
        # Calcular horas restantes hasta el final de la reserva
        horas_restantes = (fecha_fin_datetime - ahora).total_seconds() / 3600
        
        # ✅ CORREGIR: Permitir extensión si quedan MÁS de 24 horas
        puede_extender = horas_restantes > 24
        
        # Calcular cuándo ya NO estará disponible la extensión (24 horas antes del final)
        fecha_limite_extension = fecha_fin_datetime - timedelta(hours=24)
        
        # Calcular horas restantes para que se deshabilite la extensión
        if puede_extender:
            # Si puede extender, mostrar cuántas horas quedan hasta que se deshabilite
            diferencia_segundos = (fecha_limite_extension - ahora).total_seconds()
            horas_para_extension = max(0, diferencia_segundos / 3600)
            fecha_disponible_extension = fecha_limite_extension
        else:
            # Si ya no puede extender, mostrar que ya pasó el límite
            horas_para_extension = 0
            fecha_disponible_extension = fecha_limite_extension
        
        # Debug: Agregar print para verificar
        print(f"DEBUG - horas_restantes hasta final: {horas_restantes}")
        print(f"DEBUG - puede_extender: {puede_extender}")
        print(f"DEBUG - fecha_limite_extension: {fecha_limite_extension}")
        print(f"DEBUG - horas_para_extension: {horas_para_extension}")
            
        # Verificar que no haya extensiones pendientes
        if ExtensionReserva.objects.filter(reserva=reserva, estado__nombre='Pendiente').exists():
            puede_extender = False
    
    # Obtener extensiones de la reserva
    extensiones = ExtensionReserva.objects.filter(reserva=reserva).order_by('-fecha_solicitud')
    
    context = {
        'reserva': reserva,
        'huespedes': huespedes,
        'rango_adultos': range(reserva.cantidad_adultos),
        'rango_ninos': range(reserva.cantidad_ninos),
        'huespedes_precargados': huespedes_precargados,
        'is_admin_or_empleado': is_admin_or_empleado(request.user),
        'tiempo_restante': tiempo_restante,
        'tiempo_restante_creacion': tiempo_restante_creacion,
        'puede_extender': puede_extender,
        'fecha_disponible_extension': fecha_disponible_extension,
        'horas_para_extension': horas_para_extension,
        'extensiones': extensiones,
    }
    return render(request, 'reservas_detalle.html', context)

@require_POST
@login_required
def cancelar_reserva(request, id_reserva):
    reserva = get_object_or_404(Reserva, id_reserva=id_reserva)
    if request.method == 'POST':
        estado_cancelada = Estado.objects.get(nombre='Cancelada')
        estado_pendiente = Estado.objects.get(nombre='Pendiente')
        reserva_estado_anterior = reserva.estado.nombre if reserva.estado else None

        reserva.estado = estado_cancelada
        reserva.save()

        # Si la reserva cancelada era "Aprobada", liberar las concurrentes
        if reserva_estado_anterior == 'Aprobada':
            if reserva.inmueble:
                reservas_concurrentes = Reserva.objects.filter(
                    inmueble=reserva.inmueble,
                    estado__nombre='Concurrente',
                    fecha_inicio__lt=reserva.fecha_fin,
                    fecha_fin__gt=reserva.fecha_inicio
                ).exclude(id_reserva=reserva.id_reserva)
            elif reserva.cochera:
                reservas_concurrentes = Reserva.objects.filter(
                    cochera=reserva.cochera,
                    estado__nombre='Concurrente',
                    fecha_inicio__lt=reserva.fecha_fin,
                    fecha_fin__gt=reserva.fecha_inicio
                ).exclude(id_reserva=reserva.id_reserva)
            else:
                reservas_concurrentes = Reserva.objects.none()

            for r in reservas_concurrentes:
                r.estado = estado_pendiente
                r.save()
                # Opcional: notificar al cliente

        # Notificar al empleado a cargo
        empleado = None
        if reserva.inmueble and reserva.inmueble.empleado:
            empleado = reserva.inmueble.empleado
        elif reserva.cochera and reserva.cochera.empleado:
            empleado = reserva.cochera.empleado

        if empleado:
            mensaje = f"El cliente canceló la reserva #{reserva.id_reserva}."
            if reserva.estado.nombre == "Pagada":
                if reserva.inmueble and hasattr(reserva.inmueble, 'politica_cancelacion'):
                    mensaje += f" Política de cancelación: {reserva.inmueble.politica_cancelacion}"
                elif reserva.cochera and hasattr(reserva.cochera, 'politica_cancelacion'):
                    mensaje += f" Política de cancelación: {reserva.cochera.politica_cancelacion}"
            crear_notificacion(
                usuario=empleado,
                mensaje=mensaje
            )
        mensaje = "La reserva fue cancelada correctamente."
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'mensaje': mensaje
            })
        messages.success(request, mensaje)
        return redirect('reservas_usuario')

def pagar_reserva(request, id_reserva):
    reserva = get_object_or_404(Reserva, id_reserva=id_reserva)
    tarjetas = Tarjeta.objects.all()  # <-- Todas las tarjetas, sin filtro por usuario
    saldo = tarjetas[0].saldo if tarjetas else 0
    precio = reserva.precio_total
    if request.method == "POST":
        data = json.loads(request.body)
        id_reserva = data.get('id_reserva')
        try:
            reserva = Reserva.objects.get(id_reserva=id_reserva)
            estado_actual = reserva.estado.nombre

            if estado_actual in ['Cancelada', 'Rechazada']:
                return JsonResponse({'success': False, 'error': 'La reserva fue rechazada.'}, status=400)
            if estado_actual in ['Pagada', 'Confirmada', 'Finalizada', 'Terminada']:
                return JsonResponse({'success': False, 'error': 'La reserva ya fue pagada previamente.'}, status=400)
            if estado_actual != 'Aprobada':
                return JsonResponse({'success': False, 'error': 'La reserva no está en estado "Aprobada".'}, status=400)

            # --- Verificar que no hayan pasado más de 24 horas desde que fue aprobada ---
            aprobada_estado = ReservaEstado.objects.filter(
                reserva=reserva,
                estado__nombre='Aprobada'
            ).order_by('-fecha').first()
            if not aprobada_estado:
                return JsonResponse({'success': False, 'error': 'La reserva no está en estado "Aprobada"'}, status=400)
            tiempo_aprobada = aprobada_estado.fecha
            ahora = timezone.now()
            if ahora - tiempo_aprobada > timedelta(hours=24):
                # Cambiar estado a Cancelada
                estado_cancelada = Estado.objects.get(nombre='Cancelada')
                reserva.estado = estado_cancelada
                reserva.save()
                return JsonResponse({'success': False, 'error': 'El tiempo para pagar la reserva ha expirado (más de 24 horas desde la aprobación).'}, status=400)
            # ---------------------------------------------------------------------------

            # ...lógica de pago...
            estado_pagada = Estado.objects.get(nombre='Confirmada')
            reserva.estado = estado_pagada
            reserva.save()
                    
            # Rechazar automáticamente reservas pendientes superpuestas
            reservas_superpuestas = Reserva.objects.filter(
                inmueble=reserva.inmueble,
                estado__nombre='Pendiente',
                fecha_inicio__lte=reserva.fecha_fin,
                fecha_fin__gte=reserva.fecha_inicio
            ).exclude(id_reserva=reserva.id_reserva)

            estado_rechazada = Estado.objects.get(nombre='Rechazada')
            for r in reservas_superpuestas:
                r.estado = estado_rechazada
                r.save()
                # Notificar al cliente si querés
                cliente_rel = ClienteInmueble.objects.filter(reserva=r).first()
                if cliente_rel:
                    crear_notificacion(
                        usuario=cliente_rel.cliente,
                        mensaje=f"Tu reserva #{r.id_reserva} para la vivienda '{reserva.inmueble.nombre} fue rechazada'."
                    )

            # Cancelar reservas superpuestas en estado "Concurrente"
            reservas_concurrentes = Reserva.objects.filter(
                inmueble=reserva.inmueble,
                estado__nombre='Concurrente',
                fecha_inicio__lt=reserva.fecha_fin,
                fecha_fin__gt=reserva.fecha_inicio
            ).exclude(id_reserva=reserva.id_reserva)

            estado_rechazada = Estado.objects.get(nombre='Rechazada')
            for r in reservas_concurrentes:
                r.estado = estado_rechazada
                r.save()
                cliente_rel = ClienteInmueble.objects.filter(reserva=r).first()
                if cliente_rel:
                    crear_notificacion(
                        usuario=cliente_rel.cliente,
                        mensaje=f"Tu reserva #{r.id_reserva} para la vivienda '{reserva.inmueble.nombre} fue rechazada'."
                    )

            # Notificación al empleado asignado
            empleado_asignado = reserva.inmueble.empleado if reserva.inmueble else reserva.cochera.empleado
            if empleado_asignado:
                crear_notificacion(
                    usuario=empleado_asignado,
                    mensaje=f"La reserva #{reserva.id_reserva} ha sido pagada por el cliente {request.user.perfil}.",
                )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return render(request, 'simulador_mercadopago.html', {
        'saldo': saldo,
        'precio': precio,
        'id_reserva': id_reserva,
        'tarjetas': tarjetas,
    })

# En viewsReservas.py
@login_required
def solicitar_extension(request, id_reserva):
    reserva = get_object_or_404(Reserva, id_reserva=id_reserva)
    
    # Verificar que el usuario es el dueño de la reserva
    if not ClienteInmueble.objects.filter(cliente=request.user.perfil, reserva=reserva).exists():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'No tienes permisos para esta reserva.'})
        messages.error(request, "No tienes permisos para esta reserva.")
        return redirect('ver_detalle_reserva', id_reserva=id_reserva)
    
    # Verificar que la reserva esté confirmada
    if reserva.estado.nombre != 'Confirmada':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Solo se pueden extender reservas confirmadas.'})
        messages.error(request, "Solo se pueden extender reservas confirmadas.")
        return redirect('ver_detalle_reserva', id_reserva=id_reserva)
    
    # Verificar que no haya extensiones pendientes
    if ExtensionReserva.objects.filter(reserva=reserva, estado__nombre='Pendiente').exists():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Ya tienes una solicitud de extensión pendiente.'})
        messages.error(request, "Ya tienes una solicitud de extensión pendiente.")
        return redirect('ver_detalle_reserva', id_reserva=id_reserva)
    
    if request.method == 'POST':
        try:
            dias_extension = int(request.POST.get('dias_extension', 0))
            motivo = request.POST.get('motivo', '')
            
            # Validaciones
            if dias_extension < 1 or dias_extension > 7:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Los días de extensión deben ser entre 1 y 7.'})
                messages.error(request, "Los días de extensión deben ser entre 1 y 7.")
                return redirect('ver_detalle_reserva', id_reserva=id_reserva)
            
            # Calcular nueva fecha fin
            fecha_fin_nueva = reserva.fecha_fin + timedelta(days=dias_extension)
            
            # Verificar disponibilidad
            if reserva.inmueble:
                conflictos = Reserva.objects.filter(
                    inmueble=reserva.inmueble,
                    estado__nombre__in=['Confirmada', 'Pagada', 'Aprobada'],
                    fecha_inicio__lte=fecha_fin_nueva,
                    fecha_fin__gte=reserva.fecha_fin
                ).exclude(id_reserva=reserva.id_reserva)
            else:
                conflictos = Reserva.objects.filter(
                    cochera=reserva.cochera,
                    estado__nombre__in=['Confirmada', 'Pagada', 'Aprobada'],
                    fecha_inicio__lte=fecha_fin_nueva,
                    fecha_fin__gte=reserva.fecha_fin
                ).exclude(id_reserva=reserva.id_reserva)
            
            if conflictos.exists():
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'No se puede extender. Hay conflictos con otras reservas.'})
                messages.error(request, "No se puede extender. Hay conflictos con otras reservas.")
                return redirect('ver_detalle_reserva', id_reserva=id_reserva)
            
            # Calcular precio
            precio_por_dia = reserva.inmueble.precio_por_dia if reserva.inmueble else reserva.cochera.precio_por_dia
            precio_extension = precio_por_dia * dias_extension
            
            # Crear solicitud de extensión
            ExtensionReserva.objects.create(
                reserva=reserva,
                fecha_fin_original=reserva.fecha_fin,
                fecha_fin_nueva=fecha_fin_nueva,
                dias_extension=dias_extension,
                precio_extension=precio_extension,
                estado=Estado.objects.get(nombre='Pendiente'),
                motivo=motivo
            )
            
            # Notificar al empleado
            empleado = reserva.inmueble.empleado if reserva.inmueble else reserva.cochera.empleado
            if empleado:
                crear_notificacion(
                    usuario=empleado,
                    mensaje=f"Nueva solicitud de extensión para la reserva #{reserva.id_reserva} por {dias_extension} días."
                )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Solicitud de extensión enviada correctamente.'})
            
            messages.success(request, "Solicitud de extensión enviada. Será revisada por un administrador.")
            return redirect('ver_detalle_reserva', id_reserva=id_reserva)
            
        except ValueError:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Datos inválidos.'})
            messages.error(request, "Datos inválidos.")
            return redirect('ver_detalle_reserva', id_reserva=id_reserva)
    
    return redirect('ver_detalle_reserva', id_reserva=id_reserva)

################################################################################################################
# --- Cancelar reservas vencidas  ---
################################################################################################################

def cancelar_reservas_vencidas(request):
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
    return JsonResponse({'success': True, 'canceladas': count})

#################################################################################################################
# --- Huespedes ---
#################################################################################################################

@login_required
@require_POST
def completar_huespedes(request, id_reserva):
    reserva = get_object_or_404(Reserva, id_reserva=id_reserva)
    total = reserva.cantidad_adultos + reserva.cantidad_ninos

    errores = {}
    dnis = set()
    huespedes_data = []

    # 1. Datos del titular (índice 0)
    # Ejemplo: suponemos que el titular es el cliente relacionado a la reserva
    try:
        titular = reserva.clienteinmueble_set.first().cliente  # o como tengas el modelo
    except Exception:
        titular = None

    if titular:
        # Suponemos que el titular tiene nombre, apellido, dni y fecha_nacimiento
        nombre = titular.usuario.first_name or ''
        apellido = titular.usuario.last_name or ''
        dni = getattr(titular, 'dni', '')  # o donde tengas el dni
        fecha_nacimiento = getattr(titular, 'fecha_nacimiento', None)

        # Validar datos del titular si querés (puedes saltar si confías)
        if dni:
            if not dni.isdigit():
                errores['dni_0'] = "El DNI del titular debe contener solo números."
            elif len(dni) not in [7,8]:
                errores['dni_0'] = "El DNI del titular debe tener 7 u 8 dígitos."
            elif dni in dnis:
                errores['dni_0'] = "El DNI del titular está repetido."
            else:
                dnis.add(dni)

        huespedes_data.append({
            'nombre': nombre,
            'apellido': apellido,
            'dni': dni,
            'fecha_nacimiento': fecha_nacimiento
        })
    else:
        errores['titular'] = "No se pudo obtener datos del titular."

    # 2. Datos del resto de huéspedes (del 1 al total-1)
    for i in range(1, total):
        nombre = request.POST.get(f'nombre_{i}', '').strip()
        apellido = request.POST.get(f'apellido_{i}', '').strip()
        dni = request.POST.get(f'dni_{i}', '').strip()
        fecha_str = request.POST.get(f'fecha_nacimiento_{i}', '').strip()

        print(f"Datos huésped {i}: nombre='{nombre}', apellido='{apellido}', dni='{dni}', fecha_nacimiento='{fecha_str}'")

        # Validar fecha
        try:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            errores[f'fecha_nacimiento_{i}'] = "Fecha de nacimiento inválida."
            fecha_obj = None

        if not dni.isdigit():
            errores[f'dni_{i}'] = "El DNI debe contener solo números."
        elif len(dni) not in [7, 8]:
            errores[f'dni_{i}'] = "El DNI debe tener 7 u 8 dígitos."
        elif dni in dnis:
            errores[f'dni_{i}'] = "Este DNI está repetido."
        elif Huesped.objects.filter(reserva=reserva, dni=dni).exists():
            errores[f'dni_{i}'] = "Este DNI ya está registrado para esta reserva."
        else:
            dnis.add(dni)

        if any(char.isdigit() for char in nombre):
            errores[f'nombre_{i}'] = "El nombre no debe contener números."
        if any(char.isdigit() for char in apellido):
            errores[f'apellido_{i}'] = "El apellido no debe contener números."

        huespedes_data.append({
            'nombre': nombre,
            'apellido': apellido,
            'dni': dni,
            'fecha_nacimiento': fecha_obj
        })

    if errores:
        return JsonResponse({'success': False, 'errores': errores})

    # Borrar huéspedes anteriores
    Huesped.objects.filter(reserva=reserva).delete()

    # Guardar todos
    for data in huespedes_data:
        Huesped.objects.create(
            reserva=reserva,
            nombre=data['nombre'],
            apellido=data['apellido'],
            dni=data['dni'],
            fecha_nacimiento=data['fecha_nacimiento']
        )

    return JsonResponse({'success': True, 'message': 'Huéspedes cargados correctamente.'})

@login_required
def guardar_patente(request, id_reserva):
    if request.method == 'POST':
        reserva = get_object_or_404(Reserva, id_reserva=id_reserva)
        
        patente = request.POST.get('patente', '').strip().upper()
        
        if not patente:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Debes ingresar una patente válida.'})
            messages.error(request, "Debes ingresar una patente válida.")
            return redirect('ver_detalle_reserva', id_reserva=id_reserva)
        
        # Validar formato básico de patente (opcional)
        import re
        if not re.match(r'^[A-Z0-9]{6,8}$', patente):
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'El formato de la patente no es válido.'})
            messages.error(request, "El formato de la patente no es válido.")
            return redirect('ver_detalle_reserva', id_reserva=id_reserva)
        
        # Guardar la patente
        reserva.patente = patente
        reserva.save()
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Patente guardada correctamente.'})
        
        messages.success(request, "Patente guar dada correctamente.")
        return redirect('ver_detalle_reserva', id_reserva=id_reserva)
    
    return redirect('ver_detalle_reserva', id_reserva=id_reserva)

def obtener_horarios_ocupados(request, id_cochera):
    """Obtiene los horarios ocupados para una fecha específica"""
    if request.method == 'GET':
        fecha = request.GET.get('fecha')
        print(f"DEBUG: Fecha recibida: {fecha}")
        
        if not fecha:
            return JsonResponse({'error': 'Fecha requerida'}, status=400)
        
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
            print(f"DEBUG: Fecha parseada: {fecha_obj}")
        except ValueError as e:
            print(f"DEBUG: Error parseando fecha: {e}")
            return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)
        
        try:
            cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
            print(f"DEBUG: Cochera encontrada: {cochera.nombre}")
            
            # Obtener TODAS las reservas de la cochera primero
            todas_reservas = Reserva.objects.filter(cochera=cochera)
            print(f"DEBUG: Total de reservas en la cochera: {todas_reservas.count()}")
            
            # Filtrar por estados válidos
            reservas_validas = todas_reservas.filter(
                estado__nombre__in=['Pendiente','Confirmada', 'Pagada', 'Aprobada']
            )
            print(f"DEBUG: Reservas con estados válidos: {reservas_validas.count()}")
            
            # Mostrar todas las reservas para debugging
            for reserva in reservas_validas:
                print(f"DEBUG: Reserva {reserva.id_reserva} - Estado: {reserva.estado.nombre}")
                print(f"  Fecha inicio: {reserva.fecha_inicio}")
                print(f"  Fecha fin: {reserva.fecha_fin}")
            
            horarios_ocupados = set()
            horas_propias = set()
            
            # Procesar cada reserva
            for reserva in reservas_validas:
                fecha_inicio_reserva = reserva.fecha_inicio.date()
                fecha_fin_reserva = reserva.fecha_fin.date()
                
                print(f"DEBUG: Verificando reserva {reserva.id_reserva}")
                print(f"  Fecha inicio reserva: {fecha_inicio_reserva}")
                print(f"  Fecha fin reserva: {fecha_fin_reserva}")
                print(f"  Fecha consultada: {fecha_obj}")
                
                # Verificar si esta reserva afecta la fecha consultada
                if fecha_inicio_reserva <= fecha_obj <= fecha_fin_reserva:
                    print(f"DEBUG: ✓ Reserva {reserva.id_reserva} SÍ afecta la fecha {fecha_obj}")
                    
                    # Determinar las horas para este día específico
                    if fecha_inicio_reserva == fecha_obj:
                        # La reserva empieza este día
                        hora_inicio_dia = reserva.fecha_inicio.hour
                        print(f"  Hora inicio en este día: {hora_inicio_dia}")
                    else:
                        # La reserva empezó antes, desde las 00:00
                        hora_inicio_dia = 0
                        print(f"  Reserva empezó antes, hora inicio: {hora_inicio_dia}")
                    
                    if fecha_fin_reserva == fecha_obj:
                        # La reserva termina este día
                        hora_fin_dia = reserva.fecha_fin.hour
                        if reserva.fecha_fin.minute > 0:
                            hora_fin_dia += 1  # Si hay minutos, ocupar la hora completa
                        print(f"  Hora fin en este día: {hora_fin_dia}")
                    else:
                        # La reserva termina después, hasta las 23:59 (24 horas)
                        hora_fin_dia = 24
                        print(f"  Reserva termina después, hora fin: {hora_fin_dia}")
                    
                    # Agregar las horas ocupadas (de 0 a 23)
                    for hora in range(max(0, hora_inicio_dia), min(24, hora_fin_dia)):
                        hora_str = f"{hora:02d}:00"
                        horarios_ocupados.add(hora_str)
                        horas_propias.add(hora_str)
                        print(f"  → Agregando hora ocupada: {hora_str}")
                            
                else:
                    print(f"DEBUG: ✗ Reserva {reserva.id_reserva} NO afecta la fecha {fecha_obj}")
            
            horarios_lista = sorted(list(horarios_ocupados))
            print(f"DEBUG: Horarios ocupados finales: {horarios_lista}")
            
            return JsonResponse({
                'horarios_ocupados': horarios_lista,
                'horarios_propios': sorted(horas_propias),
                'fecha': fecha
            })
            
        except Exception as e:
            print(f"ERROR en obtener_horarios_ocupados: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)