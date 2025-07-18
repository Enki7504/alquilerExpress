from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Q
from datetime import timedelta, date

from ..forms import (
    InmuebleForm,
    CocheraForm,
)

from ..models import (
    Inmueble,
    InmuebleImagen,
    InmuebleEstado,
    CocheraEstado,
    CocheraImagen,
    Reserva,
    ClienteInmueble,
    Estado,
    Cochera,
    Perfil,
    Cochera,
)

from ..utils import (
    crear_notificacion,
    is_admin,
    is_admin_or_empleado,
)

################################################################################################################
# --- Vistas de Gestión de Inmuebles ---
################################################################################################################

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

    #estados = Estado.objects.filter(nombre__in=["Disponible", "En Mantenimiento"])

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
    estados = list(Estado.objects.filter(nombre__in=["Disponible", "En Mantenimiento"]).values('id_estado', 'nombre'))
    id_disponible = next((e['id_estado'] for e in estados if e['nombre'] == "Disponible"), None)
    id_mantenimiento = next((e['id_estado'] for e in estados if e['nombre'] == "En Mantenimiento"), None)

    return render(request, 'admin/admin_inmuebles.html', {
        'inmuebles': inmuebles,
        'query': query,
        'empleados': empleados,
        'admins': admins,
        'estados': estados,
        'id_disponible': id_disponible,
        'id_mantenimiento': id_mantenimiento,
        'fechas_max_ocupadas': fechas_max_ocupadas,
    })

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
            Q(nombre__icontains=query) | Q(descripcion__icontains=query)
        )

    empleados = Perfil.objects.filter(usuario__groups__name="empleado")
    admins = Perfil.objects.filter(usuario__is_staff=True).distinct()

    # Fechas ocupadas por reservas activas para cada cochera
    fechas_max_ocupadas = {}
    for cochera in cocheras:
        reservas_activas = Reserva.objects.filter(
            cochera=cochera,
            estado__nombre__in=['Aprobada', 'Pagada', 'Confirmada'],
            fecha_inicio__gte=date.today()
        ).order_by('fecha_inicio')
        if reservas_activas.exists():
            fecha_bloqueo = reservas_activas.first().fecha_inicio - timedelta(days=1)
            fechas_max_ocupadas[cochera.id_cochera] = fecha_bloqueo.strftime('%Y-%m-%d')
        else:
            fechas_max_ocupadas[cochera.id_cochera] = None

    # Fechas ocupadas por estados "En Mantenimiento" para cada cochera (NUEVO O CORREGIDO)
    fechas_ocupadas_dict = {}
    for cochera in cocheras:
        estados_mantenimiento = CocheraEstado.objects.filter(
            cochera=cochera,
            estado__nombre='En Mantenimiento',
            fecha_fin__gte=date.today()
        ).order_by('fecha_inicio')

        fechas_bloqueadas_cochera = []
        for estado_mantenimiento in estados_mantenimiento:
            if estado_mantenimiento.fecha_inicio and estado_mantenimiento.fecha_fin:
                delta = estado_mantenimiento.fecha_fin - estado_mantenimiento.fecha_inicio
                for i in range(delta.days + 1):
                    day = estado_mantenimiento.fecha_inicio + timedelta(days=i)
                    fechas_bloqueadas_cochera.append(day.strftime('%Y-%m-%d'))
        fechas_ocupadas_dict[cochera.id_cochera] = fechas_bloqueadas_cochera

    estados = list(Estado.objects.filter(nombre__in=["Disponible", "En Mantenimiento"]).values('id_estado', 'nombre'))
    id_disponible = next((e['id_estado'] for e in estados if e['nombre'] == "Disponible"), None)
    id_mantenimiento = next((e['id_estado'] for e in estados if e['nombre'] == "En Mantenimiento"), None)

    return render(request, 'admin/admin_cocheras.html', {
        'cocheras': cocheras,
        'query': query,
        'empleados': empleados,
        'id_disponible': id_disponible,
        'id_mantenimiento': id_mantenimiento,
        'admins': admins,
        'fechas_max_ocupadas': fechas_max_ocupadas,  # Asegúrate de pasar esta variable
        'fechas_ocupadas_dict': fechas_ocupadas_dict, # Asegúrate de pasar esta variable
    })

################################################################################################################
# --- Acciones Inmuebles ---
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

    empleados = Perfil.objects.filter(usuario__groups__name="empleado").distinct()
    admins = Perfil.objects.filter(usuario__is_staff=True).distinct()
    perfiles_posibles = empleados | admins

    # Asegurar que el empleado actual esté en el queryset
    if inmueble.empleado and inmueble.empleado.pk not in perfiles_posibles.values_list('pk', flat=True):
        perfiles_posibles = perfiles_posibles | Perfil.objects.filter(pk=inmueble.empleado.pk)

    if request.method == "POST":
        form = InmuebleForm(
            request.POST or None,
            request.FILES or None,
            instance=inmueble,
            perfiles_empleados=perfiles_posibles
        )
        form.fields['empleado'].queryset = perfiles_posibles.distinct()

        if form.is_valid():
            form.instance.nombre = inmueble.nombre
            inmueble = form.save()

            imagenes = request.FILES.getlist('imagenes')
            for img in imagenes:
                InmuebleImagen.objects.create(inmueble=inmueble, imagen=img)

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Inmueble actualizado correctamente.'})

            messages.success(request, "Inmueble actualizado correctamente.")
            return redirect('admin_inmuebles_editar', id_inmueble=inmueble.id_inmueble)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Corrige los errores en el formulario.',
                    'errors': form.errors.get_json_data()
                }, status=400)
            messages.error(request, "Corrige los errores en el formulario.")
    else:
        form = InmuebleForm(instance=inmueble)
        form.fields['empleado'].queryset = perfiles_posibles

    imagenes = inmueble.imagenes.all()
    return render(request, 'admin/admin_inmuebles_editar.html', {
        'form': form,
        'inmueble': inmueble,
        'imagenes': imagenes,
        'empleados': empleados,
        'admins': admins,
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
def admin_inmuebles_reservas(request, id_inmueble):
    """
    Muestra el estado actual y las reservas de un inmueble específico.
    """
    today = timezone.now()
    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
    reservas = Reserva.objects.filter(
        inmueble=inmueble,
        estado__nombre__in=["Pendiente", "Aprobada", "Pagada", "Confirmada"]
    ).order_by('-fecha_inicio')
    return render(request, 'admin/admin_inmuebles_reservas.html', {
        'inmueble': inmueble, 
        'reservas': reservas,
        'today': today,
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
    ).order_by('-id_reserva')
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
        # Cerrar el último historial de "Disponible" (si existe)
        ultimo_disponible = InmuebleEstado.objects.filter(
            inmueble=inmueble,
            estado__nombre="Disponible"
        ).order_by('-fecha_inicio').first()
        if ultimo_disponible:
            ultimo_disponible.fecha_fin = timezone.now().date()
            ultimo_disponible.save()
        # Crear el nuevo historial de "En Mantenimiento"
        InmuebleEstado.objects.create(
            inmueble=inmueble,
            estado=estado,
            fecha_inicio=timezone.now().date(),
            fecha_fin=fecha_estimacion if fecha_estimacion else None,
            descripcion=razon or ""
        )
    # Si es "Disponible", cerrar el historial anterior y crear uno nuevo
    elif estado.nombre == "Disponible":
        # Buscar el último historial de En Mantenimiento (el más reciente que no sea Disponible)
        ultimo_historial = InmuebleEstado.objects.filter(
            inmueble=inmueble
        ).exclude(estado__nombre="Disponible").order_by('-fecha_inicio').first()
        if ultimo_historial:
            ultimo_historial.fecha_fin = timezone.now().date()
            ultimo_historial.save()
        InmuebleEstado.objects.create(
            inmueble=inmueble,
            estado=estado,
            fecha_inicio=timezone.now().date(),
            fecha_fin=None,  # No hay fecha de fin para "Disponible"
            descripcion=""
        )

    messages.success(request, "Estado actualizado correctamente.")
    return redirect('admin_inmuebles')

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

################################################################################################################
# --- Acciones Cocheras ---
################################################################################################################

@login_required
@user_passes_test(is_admin)
def admin_cocheras_alta(request):
    """
    Permite a los administradores dar de alta nuevas cocheras.
    Maneja la creación de la cochera y la carga de su imagen principal.
    """
    if request.method == 'POST':
        # ✅ NO PASAR PARÁMETROS EXTRA AL CREAR EL FORMULARIO
        form = CocheraForm(request.POST, request.FILES)
        if form.is_valid():
            cochera = form.save(commit=False)
            cochera.fecha_publicacion = timezone.now().date()
            cochera.save()
            form.save_m2m()

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
        # ✅ CREAR FORMULARIO SIN PARÁMETROS EXTRA
        form = CocheraForm()
    
    return render(request, 'admin/admin_cocheras_alta.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def admin_cocheras_editar(request, id_cochera):
    """
    Permite a los administradores editar cocheras existentes.
    """
    cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
    
    # ✅ AGREGAR LA MISMA LÓGICA QUE INMUEBLES
    empleados = Perfil.objects.filter(usuario__groups__name="empleado").distinct()
    admins = Perfil.objects.filter(usuario__is_staff=True).distinct()
    perfiles_posibles = empleados | admins

    # Asegurar que el empleado actual esté en el queryset
    if cochera.empleado and cochera.empleado.pk not in perfiles_posibles.values_list('pk', flat=True):
        perfiles_posibles = perfiles_posibles | Perfil.objects.filter(pk=cochera.empleado.pk)
    
    if request.method == 'POST':
        # ✅ PASAR perfiles_empleados AL FORMULARIO
        form = CocheraForm(
            request.POST, 
            request.FILES, 
            instance=cochera,
            perfiles_empleados=perfiles_posibles  # ← AGREGAR ESTO
        )
        form.fields['empleado'].queryset = perfiles_posibles.distinct()  # ← AGREGAR ESTO
        
        if form.is_valid():
            form.save()
            
            # Guardar nuevas imágenes
            for img in request.FILES.getlist('imagenes'):
                CocheraImagen.objects.create(
                    cochera=cochera,
                    imagen=img,
                    descripcion="Imagen de la cochera"
                )
            
            # ✅ AGREGAR SOPORTE PARA AJAX (como inmuebles)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Cochera actualizada correctamente.'})
            
            messages.success(request, 'Cochera actualizada exitosamente.')
            return redirect('admin_cocheras_editar', id_cochera=cochera.id_cochera)  # ← CAMBIAR REDIRECT
        else:
            # ✅ AGREGAR SOPORTE PARA ERRORES AJAX (como inmuebles)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Corrige los errores en el formulario.',
                    'errors': form.errors.get_json_data()
                }, status=400)
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        # ✅ PASAR perfiles_empleados Y CONFIGURAR QUERYSET
        form = CocheraForm(instance=cochera, perfiles_empleados=perfiles_posibles)
        form.fields['empleado'].queryset = perfiles_posibles
    
    # ✅ AGREGAR imagenes AL CONTEXTO (como inmuebles)
    imagenes = cochera.imagenes.all()
    
    return render(request, 'admin/admin_cocheras_editar.html', {
        'form': form,
        'cochera': cochera,
        'imagenes': imagenes,  # ← AGREGAR ESTO
        'empleados': empleados,
        'admins': admins,
    })

@require_POST
@login_required
@user_passes_test(is_admin)
def eliminar_imagen_cochera(request, imagen_id):
    imagen = get_object_or_404(CocheraImagen, id_imagen=imagen_id)
    imagen.imagen.delete()  # Elimina el archivo físico
    imagen.delete()         # Elimina el registro de la base de datos
    return JsonResponse({'success': True})

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
def admin_cocheras_reservas(request, id_cochera):
    """
    Muestra el estado actual y las reservas de una cochera específica.
    """
    today = timezone.now()
    cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
    reservas = Reserva.objects.filter(
        cochera=cochera,
        estado__nombre__in=["Pendiente", "Aprobada", "Pagada", "Confirmada"]
    ).order_by('-fecha_inicio')
    return render(request, 'admin/admin_cocheras_reservas.html', {
        'cochera': cochera, 
        'reservas': reservas,
        'today': today, 
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
    ).order_by('-id_reserva')
    return render(request, 'admin/admin_cocheras_historial.html', {
        'cochera': cochera,
        'historial': historial,
        'reservas': reservas,
    })

@require_POST
@login_required
@user_passes_test(is_admin)
def cambiar_estado_cochera(request, id_cochera):
    cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
    nuevo_estado_id = request.POST.get("estado")
    fecha_estimacion = request.POST.get("fecha_estimacion")
    razon = request.POST.get("razon")

    if not nuevo_estado_id:
        return JsonResponse({'success': False, 'message': 'Debe seleccionar un estado.'}, status=400)

    estado = get_object_or_404(Estado, id_estado=nuevo_estado_id)
    cochera.estado = estado
    cochera.save()

    # Guardar historial
    if estado.nombre == "En Mantenimiento":
        ultimo_disponible = CocheraEstado.objects.filter(
            cochera=cochera,
            estado__nombre="Disponible"
        ).order_by('-fecha_inicio').first()
        if ultimo_disponible:
            ultimo_disponible.fecha_fin = timezone.now().date()
            ultimo_disponible.save()
        CocheraEstado.objects.create(
            cochera=cochera,
            estado=estado,
            fecha_inicio=timezone.now().date(),
            fecha_fin=fecha_estimacion if fecha_estimacion else None,
            descripcion=razon or ""
        )
    elif estado.nombre == "Disponible":
        ultimo_historial = CocheraEstado.objects.filter(
            cochera=cochera
        ).exclude(estado__nombre="Disponible").order_by('-fecha_inicio').first()
        if ultimo_historial:
            ultimo_historial.fecha_fin = timezone.now().date()
            ultimo_historial.save()
        CocheraEstado.objects.create(
            cochera=cochera,
            estado=estado,
            fecha_inicio=timezone.now().date(),
            fecha_fin=None,
            descripcion=""
        )

    return JsonResponse({'success': True, 'message': 'Estado actualizado correctamente.'})

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
