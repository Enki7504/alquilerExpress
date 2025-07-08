from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from datetime import timedelta


# Importaciones de formularios locales
from ..forms import (
    ComentarioForm,
    ReseniaForm,
    RespuestaComentarioForm,
)

# Importaciones de modelos locales
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

# Importaciones de utilidades locales
from ..utils import (
    crear_notificacion,
    is_admin,
    is_admin_or_empleado,
    obtener_provincias_y_ciudades
)

def buscar_inmuebles(request):
    query = request.GET.get('q', '').strip()
    precio_min = request.GET.get('precio_min')
    precio_max = request.GET.get('precio_max')
    direccion = request.GET.get('direccion')
    huespedes = request.GET.get('huespedes')
    ambientes = request.GET.get('ambientes')
    camas = request.GET.get('camas')
    banios = request.GET.get('banios')
    provincia_id = request.GET.get('provincia')
    ciudad_id = request.GET.get('ciudad')
    provincias, ciudades = obtener_provincias_y_ciudades('inmueble', provincia_id)

    # Solo mostrar inmuebles que NO estén en estado Eliminado ni Oculto
    inmuebles = Inmueble.objects.exclude(estado__nombre__in=['Oculto','Eliminado'])

    if query:
        inmuebles = inmuebles.filter(nombre__icontains=query)
    if provincia_id:
        inmuebles = inmuebles.filter(provincia_id=provincia_id)
    if ciudad_id:
        inmuebles = inmuebles.filter(ciudad_id=ciudad_id)
    if precio_min:
        try:
            inmuebles = inmuebles.filter(precio_por_dia__gte=float(precio_min))
        except ValueError:
            pass
    if precio_max:
        try:
            inmuebles = inmuebles.filter(precio_por_dia__lte=float(precio_max))
        except ValueError:
            pass
    if direccion:
        inmuebles = inmuebles.filter(direccion__icontains=direccion)
    if huespedes:
        inmuebles = inmuebles.filter(cantidad_huespedes__gte=huespedes)
    if ambientes:
        if ambientes.endswith('+'):
            inmuebles = inmuebles.filter(cantidad_ambientes__gte=int(ambientes[:-1]))
        else:
            inmuebles = inmuebles.filter(cantidad_ambientes=int(ambientes))
    if camas:
        if camas.endswith('+'):
            inmuebles = inmuebles.filter(cantidad_camas__gte=int(camas[:-1]))
        else:
            inmuebles = inmuebles.filter(cantidad_camas=int(camas))
    if banios:
        if banios.endswith('+'):
            inmuebles = inmuebles.filter(cantidad_banios__gte=int(banios[:-1]))
        else:
            inmuebles = inmuebles.filter(cantidad_banios=int(banios))

    # Add a variable to check if any provinces were found
    no_provinces_found = not provincias.exists()

    return render(request, 'busqueda/buscar_inmuebles.html', {
        'inmuebles': inmuebles,
        'query': query,
        'provincias': provincias,
        'ciudades': ciudades,
        'no_provinces_found': no_provinces_found, # Pass this to the template
    })

def buscar_cocheras(request):
    query = request.GET.get('q', '').strip()
    precio_min = request.GET.get('precio_min')
    precio_max = request.GET.get('precio_max')
    direccion = request.GET.get('direccion')
    cantidad_vehiculos = request.GET.get('cantidad_vehiculos')
    ancho = request.GET.get('ancho')
    largo = request.GET.get('largo')
    alto = request.GET.get('alto')
    con_techo = request.GET.get('con_techo')
    provincia_id = request.GET.get('provincia')
    ciudad_id = request.GET.get('ciudad')
    provincias, ciudades = obtener_provincias_y_ciudades('cochera', provincia_id)

    cocheras = Cochera.objects.exclude(estado__nombre__in=['Oculto','Eliminado'])

    if query:
        cocheras = cocheras.filter(nombre__icontains=query)
    if provincia_id:
        cocheras = cocheras.filter(provincia_id=provincia_id)
    if ciudad_id:
        cocheras = cocheras.filter(ciudad_id=ciudad_id)
    if precio_min:
        try:
            cocheras = cocheras.filter(precio_por_dia__gte=float(precio_min))
        except ValueError:
            pass
    if precio_max:
        try:
            cocheras = cocheras.filter(precio_por_dia__lte=float(precio_max))
        except ValueError:
            pass
    if direccion:
        cocheras = cocheras.filter(direccion__icontains=direccion)
    if cantidad_vehiculos:
        try:
            if cantidad_vehiculos.endswith('+'):
                cocheras = cocheras.filter(cantidad_vehiculos__gte=int(cantidad_vehiculos[:-1]))
            else:
                cocheras = cocheras.filter(cantidad_vehiculos=int(cantidad_vehiculos))
        except ValueError:
            pass
    if ancho:
        try:
            cocheras = cocheras.filter(ancho__gte=float(ancho))
        except ValueError:
            pass
    if largo:
        try:
            cocheras = cocheras.filter(largo__gte=float(largo))
        except ValueError:
            pass
    if alto:
        try:
            cocheras = cocheras.filter(alto__gte=float(alto))
        except ValueError:
            pass
    if con_techo:
        cocheras = cocheras.filter(con_techo=True)

    # Add a variable to check if any provinces were found
    no_provinces_found = not provincias.exists()

    return render(request, 'busqueda/buscar_cocheras.html', {
        'cocheras': cocheras,
        'query': query,
        'provincias': provincias,
        'ciudades': ciudades,
        'no_provinces_found': no_provinces_found, # Pass this to the template
    })

def lista_inmuebles(request):
    """
    Muestra una lista completa de todos los inmuebles disponibles.
    """
    inmuebles = Inmueble.objects.all()
    return render(request, 'lista_inmuebles.html', {'inmuebles': inmuebles})

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

    return render(request, 'detalle_inmueble.html', {
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

    return render(request, 'detalle_cochera.html', {
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
        'puede_reseñar': puede_reseñar,
    })

def obtener_provincias_y_ciudades(tipo='inmueble', provincia_id=None):
    from .models import Provincia, Ciudad, Inmueble, Cochera

    if tipo == 'inmueble':
        inmuebles_validos = Inmueble.objects.exclude(estado__nombre__in=['Oculto', 'Eliminado'])
        if provincia_id:
            ciudades = Ciudad.objects.filter(
                provincia_id=provincia_id,
                inmueble__in=inmuebles_validos
            ).distinct()
        else:
            ciudades = Ciudad.objects.filter(
                inmueble__in=inmuebles_validos
            ).distinct()
        provincias = Provincia.objects.filter(
            ciudades__inmueble__in=inmuebles_validos
        ).distinct()
    elif tipo == 'cochera':
        cocheras_validas = Cochera.objects.exclude(estado__nombre__in=['Oculto', 'Eliminado'])
        if provincia_id:
            ciudades = Ciudad.objects.filter(
                provincia_id=provincia_id,
                cochera__in=cocheras_validas
            ).distinct()
        else:
            ciudades = Ciudad.objects.filter(
                cochera__in=cocheras_validas
            ).distinct()
        provincias = Provincia.objects.filter(
            ciudades__cochera__in=cocheras_validas
        ).distinct()
    else:
        provincias = Provincia.objects.none()
        ciudades = Ciudad.objects.none()
    return provincias, ciudades