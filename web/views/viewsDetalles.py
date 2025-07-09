from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from ..forms import (
    ComentarioForm,
    ReseniaForm,
    RespuestaComentarioForm,
)

from ..models import (
    Inmueble,
    InmuebleEstado,
    CocheraEstado,
    Resenia,
    Comentario,
    Reserva,
    Cochera,
    Cochera,
    RespuestaComentario,
)

from ..utils import (
    crear_notificacion,
    is_admin,
    is_admin_or_empleado,
    is_cliente,
)

################################################################################################################
# --- Vistas de Detalles ---
################################################################################################################

def detalle_inmueble(request, id_inmueble):
    inmueble = get_object_or_404(
        Inmueble.objects.select_related('estado'),
        id_inmueble=id_inmueble
    )

    # Datos base
    resenias = Resenia.objects.filter(inmueble=inmueble)
    comentarios = Comentario.objects.filter(inmueble=inmueble).order_by('-fecha_creacion')
    reservas_ocupadas_total = Reserva.objects.filter(inmueble=inmueble, estado__nombre__in=['Confirmada', 'Pagada', 'Aprobada','Finalizada'])
    historial = InmuebleEstado.objects.filter(inmueble=inmueble).order_by('-fecha_inicio')

    es_usuario = request.user.is_authenticated and request.user.groups.filter(name="cliente").exists()
    is_cliente_var = is_cliente(request.user)
    is_admin_or_empleado_var = is_admin_or_empleado(request.user)
    is_admin_var = is_admin(request.user)

    usuario_resenia = None
    if request.user.is_authenticated:
        perfil = getattr(request.user, "perfil", None)
        if perfil:
            usuario_resenia = Resenia.objects.filter(inmueble=inmueble, usuario=perfil).first()

    # Recopilar fechas ocupadas para todos (Flatpickr 'disable')
    fechas_ocupadas = []
    for reserva in reservas_ocupadas_total:
        current = reserva.fecha_inicio
        # Incluir la fecha de inicio y la fecha de fin de la reserva
        while current <= reserva.fecha_fin:
            fechas_ocupadas.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)

    # Recopilar fechas ocupadas por el usuario actual (Flatpickr 'flatpickr-day-propia')
    fechas_ocupadas_propias = []
    if request.user.is_authenticated and hasattr(request.user, "perfil"):
        reservas_propias = Reserva.objects.filter(
            inmueble=inmueble,
            clienteinmueble__cliente=request.user.perfil,
            estado__nombre__in=['Pendiente', 'Aprobada', 'Confirmada', 'Pagada'] # Considerar todos los estados activos/pendientes
        )
        for reserva in reservas_propias:
            fecha = reserva.fecha_inicio
            # Incluir la fecha de inicio y la fecha de fin de la reserva
            while fecha <= reserva.fecha_fin:
                fechas_ocupadas_propias.append(fecha.strftime('%Y-%m-%d'))
                fecha += timedelta(days=1)

    # Formularios
    comentario_form = ComentarioForm()
    respuesta_form = RespuestaComentarioForm()
    resenia_form = ReseniaForm()

    # Procesamiento de formularios POST
    if request.method == 'POST':
        perfil = getattr(request.user, "perfil", None)

        if 'crear_resenia' in request.POST and es_usuario:
            resenia_form = ReseniaForm(request.POST)
            if resenia_form.is_valid():
                resenia = resenia_form.save(commit=False)
                resenia.usuario = perfil
                resenia.inmueble = inmueble
                resenia.save()
                messages.success(request, "¡Reseña publicada!")
                return redirect('detalle_inmueble', id_inmueble=id_inmueble)

        elif 'responder_comentario_id' in request.POST and is_admin_or_empleado_var:
            respuesta_form = RespuestaComentarioForm(request.POST)
            comentario_id = request.POST.get('responder_comentario_id')
            comentario = get_object_or_404(Comentario, id_comentario=comentario_id)
            if respuesta_form.is_valid():
                respuesta = respuesta_form.save(commit=False)
                respuesta.comentario = comentario
                respuesta.usuario = perfil
                respuesta.save()
                # Notificación interna al cliente (no email)
                crear_notificacion(
                    usuario=comentario.usuario,
                    mensaje=f"Tu comentario en '{inmueble.nombre}' fue respondido: \"{respuesta.texto}\""
                )
                messages.success(request, "Respuesta publicada.")
                return redirect('detalle_inmueble', id_inmueble=id_inmueble)

        elif request.user.is_authenticated:
            comentario_form = ComentarioForm(request.POST)
            if comentario_form.is_valid():
                comentario = comentario_form.save(commit=False)
                comentario.usuario = perfil
                comentario.inmueble = inmueble
                comentario.save()
                # Notificar al empleado asignado al inmueble
                if inmueble.empleado:
                    crear_notificacion(
                        usuario=inmueble.empleado,
                        mensaje=f"Nuevo comentario en '{inmueble.nombre}': \"{comentario.descripcion}\""
                    )
                messages.success(request, "Comentario añadido exitosamente.")
                return redirect('detalle_inmueble', id_inmueble=id_inmueble)

    # Diccionario de respuestas
    respuestas_dict = {
        r.comentario.id_comentario: r for r in RespuestaComentario.objects.filter(comentario__in=comentarios)
    }

    puede_reseñar = False
    if request.user.is_authenticated and es_usuario:
        # Busca reservas finalizadas de este usuario en este inmueble
        tiene_reserva_finalizada = reservas_ocupadas_total.filter(
            clienteinmueble__cliente=perfil,
            inmueble=inmueble,
            estado__nombre__iexact="Finalizada"
        ).exists()
        puede_reseñar = tiene_reserva_finalizada

    # Datos del cliente autenticado para precargar como primer huésped
    datos_cliente = None
    if request.user.is_authenticated and hasattr(request.user, "perfil"):
        perfil = request.user.perfil
        datos_cliente = {
            "nombre": perfil.usuario.first_name,
            "apellido": perfil.usuario.last_name,
            "dni": perfil.dni,
            "fecha_nac": perfil.fecha_nacimiento.strftime("%Y-%m-%d") if perfil.fecha_nacimiento else "",
        }

    # Buscar el último estado "En Mantenimiento" con fecha_fin futura o sin fecha_fin
    hoy = timezone.now().date()
    mantenimiento_activo = (
        InmuebleEstado.objects
        .filter(
            inmueble=inmueble,
            estado__nombre="En Mantenimiento",
            fecha_inicio__lte=hoy,
            fecha_fin__gte=hoy
        )
        .order_by('-fecha_fin')
        .first()
    )
    fecha_fin_mantenimiento = None
    if mantenimiento_activo and mantenimiento_activo.fecha_fin:
        fecha_fin_mantenimiento = mantenimiento_activo.fecha_fin.strftime('%Y-%m-%d')

    return render(request, 'detalle/detalle_inmueble.html', {
        'inmueble': inmueble,
        'resenias': resenias,
        'comentarios': comentarios,
        'comentario_form': comentario_form,
        'respuesta_form': respuesta_form,
        'resenia_form': resenia_form,
        'historial': historial,
        'usuario_resenia': usuario_resenia,
        'respuestas': respuestas_dict,
        'fechas_ocupadas': fechas_ocupadas,
        'fechas_ocupadas_propias': fechas_ocupadas_propias,
        'es_usuario': es_usuario,
        'is_admin_or_empleado': is_admin_or_empleado_var,
        'is_admin': is_admin_var,
        'is_cliente': is_cliente_var,
        'puede_reseñar': puede_reseñar,
        'datos_cliente': datos_cliente, 
        'fecha_fin_mantenimiento': fecha_fin_mantenimiento,
    })

def detalle_cochera(request, id_cochera):
    cochera = get_object_or_404(
        Cochera.objects.select_related('estado'),
        id_cochera=id_cochera
    )
    resenias = Resenia.objects.filter(cochera=cochera)
    comentarios = Comentario.objects.filter(cochera=cochera).order_by('-fecha_creacion')
    reservas = Reserva.objects.filter(cochera=cochera, estado__nombre__in=['Confirmada', 'Pagada', 'Aprobada', 'Finalizada'])
    historial = CocheraEstado.objects.filter(cochera=cochera).order_by('-fecha_inicio')

    es_usuario = request.user.is_authenticated and request.user.groups.filter(name="cliente").exists()
    is_cliente_var = is_cliente(request.user)
    is_admin_or_empleado_var = is_admin_or_empleado(request.user)
    is_admin_var = is_admin(request.user)

    # Fechas ocupadas (para todos)
    fechas_ocupadas = []
    for reserva in reservas:
        current = reserva.fecha_inicio
        while current <= reserva.fecha_fin:
            fechas_ocupadas.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)

    # Fechas ocupadas por el usuario actual (para marcar en naranja)
    fechas_ocupadas_propias = []
    if request.user.is_authenticated and hasattr(request.user, "perfil"):
        reservas_propias = Reserva.objects.filter(
            cochera=cochera,
            clienteinmueble__cliente=request.user.perfil,
            estado__nombre__in=['Pendiente', 'Aprobada', 'Confirmada', 'Pagada']
        )
        for reserva in reservas_propias:
            fecha = reserva.fecha_inicio
            while fecha <= reserva.fecha_fin:
                fechas_ocupadas_propias.append(fecha.strftime('%Y-%m-%d'))
                fecha += timedelta(days=1)

    usuario_resenia = None
    if request.user.is_authenticated:
        perfil = getattr(request.user, "perfil", None)
        usuario_resenia = Resenia.objects.filter(cochera=cochera, usuario=perfil).first()

    # Formularios
    comentario_form = ComentarioForm()
    respuesta_form = RespuestaComentarioForm()
    resenia_form = ReseniaForm()

    # Procesamiento de formularios POST (sin cambios...)

    # Diccionario de respuestas
    respuestas_dict = {
        r.comentario.id_comentario: r for r in RespuestaComentario.objects.filter(comentario__in=comentarios)
    }

    puede_reseñar = False
    if request.user.is_authenticated and es_usuario:
        tiene_reserva_finalizada = reservas.filter(
            clienteinmueble__cliente=perfil,
            cochera=cochera,
            estado__nombre__iexact="Finalizada"
        ).exists()
        puede_reseñar = tiene_reserva_finalizada

    return render(request, 'detalle/detalle_cochera.html', {
        'cochera': cochera,
        'resenias': resenias,
        'comentarios': comentarios,
        'comentario_form': comentario_form,
        'respuesta_form': respuesta_form,
        'resenia_form': resenia_form,
        'reservas': reservas,
        'historial': historial,
        'usuario_resenia': usuario_resenia,
        'fechas_ocupadas': fechas_ocupadas,
        'fechas_ocupadas_propias': fechas_ocupadas_propias,  # <-- AGREGADO
        'respuestas': respuestas_dict,
        'es_usuario': es_usuario,
        'is_admin_or_empleado': is_admin_or_empleado_var,
        'is_admin': is_admin_var,
        'is_cliente': is_cliente_var,
        'puede_reseñar': puede_reseñar,
    })

################################################################################################################
# --- Vistas de Comentarios y Reseñas ---
################################################################################################################

@require_POST
@login_required
@user_passes_test(is_admin_or_empleado)
def eliminar_comentario(request, id_comentario):
    comentario = get_object_or_404(Comentario, id_comentario=id_comentario)
    comentario.delete()
    messages.success(request, "Comentario eliminado correctamente.")
    return redirect(request.META.get('HTTP_REFERER', 'index'))

@require_POST
@login_required
@user_passes_test(is_admin_or_empleado)
def eliminar_resenia(request, id_resenia):
    resenia = get_object_or_404(Resenia, id_resenia=id_resenia)
    
    # Verificar si la reseña pertenece a un inmueble o cochera que el empleado administra
    if (resenia.inmueble and resenia.inmueble.empleado != request.user.perfil) or \
       (resenia.cochera and resenia.cochera.empleado != request.user.perfil):
        if not request.user.is_staff:  # Solo el admin puede eliminar cualquier reseña
            messages.error(request, "No tienes permiso para eliminar esta reseña.")
            return redirect(request.META.get('HTTP_REFERER', 'index'))
    
    # Eliminar la reseña
    resenia.delete()
    messages.success(request, "Reseña eliminada correctamente.")
    return redirect(request.META.get('HTTP_REFERER', 'index'))
