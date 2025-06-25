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

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_inmuebles(request):
    """
    Lista todos los inmuebles y permite la búsqueda.
    Incluye botones para acciones rápidas (ver, editar, eliminar, estado, historial).
    """
    query = request.GET.get('q', '').strip()
    inmuebles = Inmueble.objects.exclude(estado__nombre='Eliminado').order_by('nombre')
    
    if query:
        inmuebles = inmuebles.filter(
            Q(nombre__icontains=query) | Q(descripcion__icontains=query)
        )
    
    empleados = Perfil.objects.filter(usuario__groups__name="empleado")
    admins = Perfil.objects.filter(usuario__is_staff=True).distinct()

    estados = Estado.objects.filter(nombre__in=["Disponible", "En Mantenimiento"])

    # Fechas ocupadas por reservas activas para cada inmueble
    fechas_max_ocupadas = {}
    for inmueble in inmuebles:
        reservas_activas = Reserva.objects.filter(
            inmueble=inmueble,
            estado__nombre__in=['Aprobada', 'Pagada', 'Confirmada'],
            fecha_inicio__gte=date.today()
        ).order_by('fecha_inicio')
        if reservas_activas.exists():
            # Tomar la fecha de inicio más próxima y restar un día
            fecha_bloqueo = reservas_activas.first().fecha_inicio - timedelta(days=1)
            fechas_max_ocupadas[inmueble.id_inmueble] = fecha_bloqueo.strftime('%Y-%m-%d')
        else:
            fechas_max_ocupadas[inmueble.id_inmueble] = None

    return render(request, 'admin/admin_inmuebles.html', {
        'inmuebles': inmuebles,
        'query': query,
        'empleados': empleados,
        'admins': admins,
        'estados': estados,
        'fechas_max_ocupadas': fechas_max_ocupadas,
    })

@login_required
@user_passes_test(is_admin)
def cambiar_empleado_inmueble(request, id_inmueble):
    if request.method == "POST":
        inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
        empleado_id = request.POST.get("empleado")
        if empleado_id:
            try:
                empleado_perfil = Perfil.objects.get(usuario__id=empleado_id)
                inmueble.empleado = empleado_perfil
                inmueble.save()
                messages.success(request, "Empleado asignado actualizado.")
            except Perfil.DoesNotExist:
                messages.error(request, "El usuario seleccionado no tiene perfil y no puede ser asignado.")
        else:
            inmueble.empleado = None
            inmueble.save()
            messages.success(request, "Empleado desasignado.")
    return redirect('admin_inmuebles')

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_cocheras(request):
    """
    Lista todas las cocheras y permite la búsqueda.
    Incluye botones para acciones rápidas (ver, editar, eliminar, estado, historial).
    """
    query = request.GET.get('q', '').strip()
    cocheras = Cochera.objects.exclude(estado__nombre='Eliminado').order_by('nombre')
    
    if query:
        cocheras = cocheras.filter(
            Q(nombre__icontains=query) | Q(descripcion__icontains=query))
    
    empleados = Perfil.objects.filter(usuario__groups__name="empleado")
    admins = Perfil.objects.filter(usuario__is_staff=True).distinct()
    return render(request, 'admin/admin_cocheras.html', {
        'cocheras': cocheras,
        'query': query,
        'empleados': empleados,
        'admins': admins
    })

@login_required
@user_passes_test(is_admin)
def cambiar_empleado_cochera(request, id_cochera):
    if request.method == "POST":
        cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
        empleado_id = request.POST.get("empleado")
        if empleado_id:
            try:
                perfil = Perfil.objects.get(usuario__id=empleado_id)
                cochera.empleado = perfil
                cochera.save()
                messages.success(request, "Empleado asignado actualizado.")
            except Perfil.DoesNotExist:
                messages.error(request, "El usuario seleccionado no tiene perfil y no puede ser asignado.")
        else:
            cochera.empleado = None
            cochera.save()
            messages.success(request, "Empleado desasignado.")
    return redirect('admin_cocheras')

################################################################################################################
# --- Vistas de Gestión de Inmuebles ---
################################################################################################################

@login_required
@user_passes_test(is_admin)
def admin_inmuebles_alta(request):
    """
    Permite a los administradores dar de alta nuevos inmuebles.
    Maneja la creación del inmueble y la carga de su imagen principal.
    """
    if request.method == 'POST':
        form = InmuebleForm(request.POST, request.FILES)
        if form.is_valid():
            # Guardar el inmueble completamente
            inmueble = form.save(commit=False)
            inmueble.fecha_publicacion = timezone.now().date()
            inmueble.save()
            form.save_m2m()

            # Guardar todas las imágenes
            for img in request.FILES.getlist('imagenes'):
                InmuebleImagen.objects.create(
                    inmueble=inmueble,
                    imagen=img,
                    descripcion="Imagen del inmueble"
                )
            
            messages.success(request, 'Inmueble creado exitosamente.')
            return redirect('admin_inmuebles_alta')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = InmuebleForm()
    
    return render(request, 'admin/admin_inmuebles_alta.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def admin_inmuebles_editar(request, id_inmueble):
    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
    
    if request.method == "POST":
        form = InmuebleForm(request.POST, request.FILES, instance=inmueble)
        if form.is_valid():
            form.instance.nombre = inmueble.nombre
            inmueble = form.save()
            # Guardar nuevas imágenes
            imagenes = request.FILES.getlist('imagenes')
            for img in imagenes:
                InmuebleImagen.objects.create(inmueble=inmueble, imagen=img)
            
            # Verificar si es una petición AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Inmueble actualizado correctamente.'
                })
                
            messages.success(request, "Inmueble actualizado correctamente.")
            return redirect('admin_inmuebles_editar', id_inmueble=inmueble.id_inmueble)
        else:
            # Manejo de errores para AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Corrige los errores en el formulario.',
                    'errors': form.errors.get_json_data()
                }, status=400)
                
            messages.error(request, "Corrige los errores en el formulario.")
    else:
        form = InmuebleForm(instance=inmueble)
    
    imagenes = inmueble.imagenes.all()
    return render(request, 'admin/admin_inmuebles_editar.html', {
        'form': form,
        'inmueble': inmueble,
        'imagenes': imagenes,
    })

@require_POST
@login_required
@user_passes_test(is_admin)
def eliminar_imagen_inmueble(request, imagen_id):
    imagen = get_object_or_404(InmuebleImagen, id_imagen=imagen_id)
    imagen.imagen.delete()  # Elimina el archivo físico
    imagen.delete()         # Elimina el registro de la base de datos
    return JsonResponse({'success': True})

@login_required
@user_passes_test(is_admin)
def admin_inmuebles_eliminar(request, id_inmueble):
    """
    Cambia el estado de un inmueble a "Eliminado" en lugar de borrarlo,
    pero solo si no tiene reservas a futuro en estado activo.
    Las reservas a futuro en estado 'Pendiente' se cancelan automáticamente.
    """
    # Verificar autenticación para solicitudes AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'No estás autenticado.'}, status=401)

    # Verificar permisos para solicitudes AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'No tienes permisos para realizar esta acción.'}, status=403)

    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)

    # --- VERIFICAR RESERVAS A FUTURO ---
    reservas_futuras_activas = Reserva.objects.filter(
        inmueble=inmueble,
        fecha_inicio__gte=timezone.now().date(),
        estado__nombre__in=['Aprobada', 'Pagada', 'Confirmada']
    )
    if reservas_futuras_activas.exists():
        mensaje = 'No se puede eliminar el inmueble porque tiene reservas a futuro.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': mensaje}, status=400)
        messages.error(request, mensaje)
        return redirect('admin_inmuebles')
    # -----------------------------------

    if request.method == 'POST':
        # Cancelar reservas futuras en estado Pendiente
        reservas_pendientes = Reserva.objects.filter(
            inmueble=inmueble,
            fecha_inicio__gte=timezone.now().date(),
            estado__nombre='Pendiente'
        )
        estado_cancelada, _ = Estado.objects.get_or_create(nombre='Cancelada')
        for reserva in reservas_pendientes:
            reserva.estado = estado_cancelada
            reserva.save()
            # Notificar y enviar mail al cliente
            cliente_rel = ClienteInmueble.objects.filter(reserva=reserva).first()
            if cliente_rel:
                perfil_cliente = cliente_rel.cliente
                # Notificación interna
                crear_notificacion(
                    usuario=perfil_cliente,
                    mensaje=f"Tu reserva #{reserva.id_reserva} para la vivienda '{inmueble.nombre}' fue rechazada porque la vivienda fue eliminada por el administrador."
                )
                # Enviar mail
                send_mail(
                    subject="Reserva cancelada",
                    message=f"Tu reserva #{reserva.id_reserva} para la vivienda '{inmueble.nombre}' fue rechazada porque la vivienda fue eliminada por el administrador.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[perfil_cliente.usuario.email],
                    fail_silently=True,
                )

        # Eliminar el inmueble de la DB
        inmueble.delete()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Vivienda eliminada. Reservas pendientes a futuro canceladas.'})

        messages.success(request, 'Vivienda eliminada. Reservas pendientes a futuro canceladas.')
        return redirect('admin_inmuebles')

    # Si es GET, muestra la confirmación
    return render(request, 'admin/confirmar_eliminacion.html', {
        'objeto': inmueble,
        'tipo': 'inmueble'
    })

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_inmuebles_historial(request, id_inmueble):
    """
    Muestra el historial de estados y reservas finalizadas/canceladas/rechazadas de un inmueble específico.
    """
    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
    historial = InmuebleEstado.objects.filter(inmueble=inmueble).order_by('-fecha_inicio')
    return render(request, 'admin/admin_inmuebles_historial.html', {'inmueble': inmueble, 'historial': historial})

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_inmuebles_reservas(request, id_inmueble):
    """
    Muestra el estado actual y las reservas de un inmueble específico.
    """
    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
    reservas = Reserva.objects.filter(
        inmueble=inmueble,
        estado__nombre__in=["Pendiente", "Aprobada", "Pagada", "Confirmada"]
    ).order_by('-fecha_inicio')
    return render(request, 'admin/admin_inmuebles_reservas.html', {
        'inmueble': inmueble, 
        'reservas': reservas
    })

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_inmuebles_historial(request, id_inmueble):
    """
    Muestra el historial de estados y reservas finalizadas/canceladas/rechazadas de un inmueble específico.
    """
    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
    historial = InmuebleEstado.objects.filter(inmueble=inmueble).order_by('-fecha_inicio')
    reservas = Reserva.objects.filter(
        inmueble=inmueble,
        estado__nombre__in=['Cancelada', 'Rechazada', 'Finalizada']
    ).order_by('-fecha_inicio')
    return render(request, 'admin/admin_inmuebles_historial.html', {
        'inmueble': inmueble,
        'historial': historial,
        'reservas': reservas,
    })

@login_required
@user_passes_test(is_admin)
@require_POST
def cambiar_estado_inmueble(request, id_inmueble):
    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
    nuevo_estado_id = request.POST.get("estado")
    fecha_estimacion = request.POST.get("fecha_estimacion")
    razon = request.POST.get("razon")

    if not nuevo_estado_id:
        messages.error(request, "Debe seleccionar un estado.")
        return redirect('admin_inmuebles')

    estado = get_object_or_404(Estado, id_estado=nuevo_estado_id)
    inmueble.estado = estado
    inmueble.save()

    # Si es "En mantenimiento", guardar fecha y razón en el historial
    if estado.nombre == "En Mantenimiento":
        InmuebleEstado.objects.create(
            inmueble=inmueble,
            estado=estado,
            fecha_inicio=timezone.now().date(),
            fecha_fin=fecha_estimacion if fecha_estimacion else None,
        )
        # Puedes guardar la razón en un campo extra o en un comentario/log si tienes uno
        # Por ejemplo, podrías agregar un campo "razon" a InmuebleEstado si lo deseas

    messages.success(request, "Estado actualizado correctamente.")
    return redirect('admin_inmuebles')

################################################################################################################
# --- Vistas de Gestión de Cocheras ---
################################################################################################################

@login_required
@user_passes_test(is_admin)
def admin_cocheras_alta(request):
    """
    Permite a los administradores dar de alta nuevas cocheras.
    Maneja la creación de la cochera y la carga de su imagen principal.
    """
    if request.method == 'POST':
        form = CocheraForm(request.POST, request.FILES)
        if form.is_valid():
            cochera = form.save(commit=False)
            cochera.fecha_publicacion = timezone.now().date()
            cochera.save() # Guardar el cochera completamente
            form.save_m2m() # Guardar relaciones many-to-many si las hay

            # Guardar todas las imágenes
            for img in request.FILES.getlist('imagenes'):
                CocheraImagen.objects.create(
                    cochera=cochera,
                    imagen=img,
                    descripcion="Imagen de la cochera"
                )
            messages.success(request, 'Cochera creada exitosamente.')
            return redirect('admin_cocheras_alta')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = CocheraForm()
    
    return render(request, 'admin/admin_cocheras_alta.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def admin_cocheras_editar(request, id_cochera):
    cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
    
    if request.method == "POST":
        form = CocheraForm(request.POST, request.FILES, instance=cochera)
        if form.is_valid():
            form.instance.nombre = cochera.nombre
            cochera = form.save()
            # Guardar nuevas imágenes
            imagenes = request.FILES.getlist('imagenes')
            for img in imagenes:
                CocheraImagen.objects.create(cochera=cochera, imagen=img)
            
            # Verificar si es una petición AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Cochera actualizada correctamente.'
                })
                
            messages.success(request, "Cochera actualizada correctamente.")
            return redirect('admin_cocheras_editar', id_cochera=cochera.id_cochera)
        else:
            # Manejo de errores para AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Corrige los errores en el formulario.',
                    'errors': form.errors.get_json_data()
                }, status=400)
                
            messages.error(request, "Corrige los errores en el formulario.")
    else:
        form = CocheraForm(instance=cochera)
    
    return render(request, 'admin/admin_cocheras_editar.html', {
        'form': form,
        'cochera': cochera,
    })

@require_POST
@login_required
@user_passes_test(is_admin)
def eliminar_imagen_cochera(request, id_imagen):
    try:
        imagen = get_object_or_404(CocheraImagen, id_imagen=id_imagen)
        imagen.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@user_passes_test(is_admin)
def admin_cocheras_eliminar(request, id_cochera):
    """
    Cambia el estado de una cochera a "Eliminado" en lugar de borrarla,
    pero solo si no tiene reservas a futuro en estado activo.
    Las reservas a futuro en estado 'Pendiente' se cancelan automáticamente.
    """
    # Verificar autenticación para solicitudes AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'No estás autenticado.'}, status=401)

    # Verificar permisos para solicitudes AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'No tienes permisos para realizar esta acción.'}, status=403)

    cochera = get_object_or_404(Cochera, id_cochera=id_cochera)

    # --- VERIFICAR RESERVAS A FUTURO ---
    reservas_futuras_activas = Reserva.objects.filter(
        cochera=cochera,
        fecha_inicio__gte=timezone.now().date(),
        estado__nombre__in=['Aprobada', 'Pagada', 'Confirmada']
    )
    if reservas_futuras_activas.exists():
        mensaje = 'No se puede eliminar la cochera porque tiene reservas a futuro.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': mensaje}, status=400)
        messages.error(request, mensaje)
        return redirect('admin_cocheras')
    # -----------------------------------

    if request.method == 'POST':
        # Cancelar reservas futuras en estado Pendiente
        reservas_pendientes = Reserva.objects.filter(
            cochera=cochera,
            fecha_inicio__gte=timezone.now().date(),
            estado__nombre='Pendiente'
        )
        estado_cancelada, _ = Estado.objects.get_or_create(nombre='Cancelada')
        for reserva in reservas_pendientes:
            reserva.estado = estado_cancelada
            reserva.save()
            # Notificar y enviar mail al cliente
            cliente_rel = ClienteInmueble.objects.filter(reserva=reserva).first()
            if cliente_rel:
                perfil_cliente = cliente_rel.cliente
                # Notificación interna
                crear_notificacion(
                    usuario=perfil_cliente,
                    mensaje=f"Tu reserva #{reserva.id_reserva} para la cochera '{cochera.nombre}' fue rechazada porque la cochera fue eliminada por el administrador."
                )
                # Enviar mail
                send_mail(
                    subject="Reserva cancelada",
                    message=f"Tu reserva #{reserva.id_reserva} para la cochera '{cochera.nombre}' fue rechazada porque la cochera fue eliminada por el administrador.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[perfil_cliente.usuario.email],
                    fail_silently=True,
                )

        # Eliminar la cochera de la DB
        cochera.delete()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Cochera eliminada. Reservas pendientes a futuro canceladas.'})

        messages.success(request, 'Cochera eliminada. Reservas pendientes a futuro canceladas.')
        return redirect('admin_cocheras')

    # Si es GET, muestra la confirmación
    return render(request, 'admin/confirmar_eliminacion.html', {
        'objeto': cochera,
        'tipo': 'cochera'
    })

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_cocheras_historial(request, id_cochera):
    """
    Muestra el historial de estados y reservas finalizadas/canceladas/rechazadas de una cochera específica.
    """
    cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
    historial = CocheraEstado.objects.filter(cochera=cochera).order_by('-fecha_inicio')
    reservas = Reserva.objects.filter(
        cochera=cochera,
        estado__nombre__in=['Cancelada', 'Rechazada', 'Finalizada']
    ).order_by('-fecha_inicio')
    return render(request, 'admin/admin_cocheras_historial.html', {
        'cochera': cochera,
        'historial': historial,
        'reservas': reservas,
    })

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_cocheras_reservas(request, id_cochera):
    """
    Muestra el estado actual y las reservas de una cochera específica.
    """
    cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
    reservas = Reserva.objects.filter(
        cochera=cochera,
        estado__nombre__in=["Pendiente", "Aprobada", "Pagada", "Confirmada"]
    ).order_by('-fecha_inicio')
    return render(request, 'admin/admin_cocheras_reservas.html', {'cochera': cochera, 'reservas': reservas})