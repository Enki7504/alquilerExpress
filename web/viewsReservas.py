import datetime
import random
import json
import secrets
import string
import mercadopago

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST
from django.db import IntegrityError, transaction
from django.db.models import Q
from datetime import timedelta, date
from django.template.loader import render_to_string
# mercado pago
from django.views.decorators.csrf import csrf_exempt

# Importaciones de formularios locales
from .forms import (
    RegistroUsuarioForm,
    InmuebleForm,
    CocheraForm,
    ComentarioForm,
    LoginForm,
    ClienteCreationForm,
    EmpleadoCreationForm,
    EmpleadoAdminCreationForm,
    ClienteAdminCreationForm,
    ChangePasswordForm,
    ReseniaForm,
    RespuestaComentarioForm,
    NotificarImprevistoForm,
)

# Importaciones de modelos locales
from .models import (
    Inmueble,
    InmuebleImagen,
    InmuebleEstado,
    CocheraEstado,
    CocheraImagen,
    Notificacion,
    Resenia,
    Comentario,
    LoginOTP,
    Reserva,
    ClienteInmueble,
    Estado,
    Cochera,
    Perfil,
    ReservaEstado,
    Ciudad,
    Provincia,
    Cochera,
    RespuestaComentario,
    Huesped,
    Tarjeta
)

# Importaciones de utilidades locales
from .utils import (
    email_link_token,
    crear_notificacion,
    cambiar_estado_inmueble,
    is_admin,
    is_admin_or_empleado,
)

# para enviar correos a empleados sobre reservas
from .utils import enviar_mail_a_empleados_sobre_reserva

################################################################################################################
# --- Vistas de Gestión de Reservas ---
################################################################################################################

@login_required
def crear_reserva(request, id_inmueble):
    """
    Permite a un cliente crear una reserva para un inmueble, validando que no existan reservas superpuestas
    del mismo cliente para el mismo inmueble.
    """
    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
    perfil = request.user.perfil

    if request.method == "POST":
        # Obtener fechas del formulario
        fecha_inicio_str = request.POST.get("fecha_inicio")
        fecha_fin_str = request.POST.get("fecha_fin")
        try:
            fecha_inicio = datetime.datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
            fecha_fin = datetime.datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
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
            precio_total=inmueble.precio_por_dia * (fecha_fin - fecha_inicio).days
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
    Permite a los usuarios crear una reserva para una cochera.
    Valida fechas, mínimo de noches, superposición de reservas y crea la relación con el cliente.
    """
    cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
    perfil = request.user.perfil

    if request.method == 'POST':
        fecha_inicio_str = request.POST.get('fecha_inicio')
        fecha_fin_str = request.POST.get('fecha_fin')

        # Validar fechas
        try:
            fecha_inicio = datetime.datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            messages.error(request, 'Fechas inválidas.')
            return redirect('detalle_cochera', id_cochera=id_cochera)

        if fecha_inicio >= fecha_fin:
            messages.error(request, 'La fecha de salida debe ser posterior a la de llegada.')
            return redirect('detalle_cochera', id_cochera=id_cochera)

        # Validar mínimo de noches
        dias = (fecha_fin - fecha_inicio).days
        if dias < cochera.minimo_dias_alquiler:
            messages.error(request, f"El mínimo de noches de alquiler para esta cochera es {cochera.minimo_dias_alquiler}.")
            return redirect('detalle_cochera', id_cochera=id_cochera)

        # Validar que el cliente no tenga reservas superpuestas para la misma cochera
        reserva_superpuesta_usuario = Reserva.objects.filter(
            clienteinmueble__cliente=perfil,
            cochera=cochera,
            estado__nombre__in=['Pendiente', 'Confirmada', 'Pagada', 'Aprobada'],
            fecha_inicio__lte=fecha_fin,
            fecha_fin__gte=fecha_inicio
        ).exists()
        if reserva_superpuesta_usuario:
            messages.error(request, "Ya tenés una reserva activa para esta cochera en esas fechas.")
            return redirect('detalle_cochera', id_cochera=id_cochera)

        # Validar que la cochera esté disponible en esas fechas
        reserva_superpuesta_cochera = Reserva.objects.filter(
            cochera=cochera,
            estado__nombre__in=['Confirmada', 'Pagada', 'Aprobada'],
            fecha_inicio__lte=fecha_fin,
            fecha_fin__gte=fecha_inicio
        ).exists()
        if reserva_superpuesta_cochera:
            messages.error(request, "La cochera no está disponible en esas fechas.")
            return redirect('detalle_cochera', id_cochera=id_cochera)

        # Calcular precio total
        precio_total = cochera.precio_por_dia * dias

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

################################################################################################################
# --- DETALLE DE RESERVAS  ---
################################################################################################################

@login_required
def reservas_usuario(request):
    """
    Muestra todas las reservas del usuario autenticado.
    """
    reservas = Reserva.objects.filter(clienteinmueble__cliente=request.user.perfil).distinct().order_by('-fecha_inicio')
    return render(request, 'reservas.html', {
        'reservas': reservas
    })

@login_required
def ver_detalle_reserva(request, id_reserva):
    reserva = get_object_or_404(Reserva, id_reserva=id_reserva)
    huespedes = reserva.huespedes.all()
    tiempo_restante = None

    if reserva.estado.nombre == "Aprobada" and reserva.aprobada_en:
        limite = reserva.aprobada_en + timedelta(hours=24)
        ahora = timezone.now()
        tiempo_restante = (limite - ahora).total_seconds()
        if tiempo_restante < 0:
            tiempo_restante = 0
    es_admin_o_empleado = is_admin_or_empleado(request.user)

    return render(request, 'reservas_detalle.html', {
        'reserva': reserva,
        'huespedes': huespedes,
        'tiempo_restante': tiempo_restante,
        'is_admin_or_empleado': es_admin_o_empleado,
    })

@require_POST
@login_required
def cancelar_reserva(request, id_reserva):
    reserva = get_object_or_404(Reserva, id_reserva=id_reserva)
    estado_cancelada = Estado.objects.get(nombre="Cancelada")
    reserva.estado = estado_cancelada
    reserva.save()

    # Notificar al empleado a cargo
    empleado = None
    if reserva.inmueble and reserva.inmueble.empleado:
        empleado = reserva.inmueble.empleado
    elif reserva.cochera and reserva.cochera.empleado:
        empleado = reserva.cochera.empleado

    if empleado:
        crear_notificacion(
            usuario=empleado,
            mensaje=f"El cliente canceló la reserva #{reserva.id_reserva}."
        )
    mensaje = "La reserva fue cancelada correctamente."
    # Si es una petición AJAX, devolvé JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'mensaje': mensaje
        })
    # Redirección tradicional
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
def completar_huespedes(request, id_reserva):
    reserva = get_object_or_404(Reserva, id_reserva=id_reserva)
    total = reserva.cantidad_adultos + reserva.cantidad_ninos
    if request.method == "POST":
        for i in range(total):
            nombre = request.POST.get(f'nombre_{i}')
            apellido = request.POST.get(f'apellido_{i}')
            dni = request.POST.get(f'dni_{i}')
            # Validar fecha de nacimiento solo si es un adulto
            if reserva.cantidad_adultos > 0 and i < reserva.cantidad_adultos:
                fecha_nacimiento = request.POST.get(f'fecha_nacimiento_{i}')
            else:
                fecha_nacimiento = request.POST.get(f'fecha_nacimiento_{i}')
            if nombre and apellido and dni and fecha_nacimiento:
                reserva.huespedes.create(
                    nombre=nombre,
                    apellido=apellido,
                    dni=dni,
                    fecha_nacimiento=fecha_nacimiento
                )
        return redirect('ver_detalle_reserva', id_reserva=id_reserva)
    return redirect('ver_detalle_reserva', id_reserva=id_reserva)