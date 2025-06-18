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
from datetime import timedelta
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

def buscar_inmuebles(request):
    query = request.GET.get('q', '').strip()
    provincia_id = request.GET.get('provincia')
    ciudad_id = request.GET.get('ciudad')
    precio = request.GET.get('precio')
    ubicacion = request.GET.get('ubicacion')
    huespedes = request.GET.get('huespedes')
    ambientes = request.GET.get('ambientes')
    camas = request.GET.get('camas')
    banios = request.GET.get('banios')

    # Solo mostrar inmuebles que NO estén en estado Eliminado ni Oculto
    inmuebles = Inmueble.objects.exclude(estado__nombre__in=['Oculto','Eliminado'])

    if query:
        inmuebles = inmuebles.filter(nombre__icontains=query)
    if provincia_id:
        inmuebles = inmuebles.filter(provincia_id=provincia_id)
    if ciudad_id:
        inmuebles = inmuebles.filter(ciudad_id=ciudad_id)
    if precio:
        inmuebles = inmuebles.filter(precio_por_dia__lte=precio)
    if ubicacion:
        inmuebles = inmuebles.filter(ubicacion__icontains=ubicacion)
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

    # Provincias solo con inmuebles
    provincias = Provincia.objects.filter(ciudades__inmueble__isnull=False).distinct()
    # Ciudades solo con inmuebles (y opcionalmente de la provincia seleccionada)
    if provincia_id:
        ciudades = Ciudad.objects.filter(
            provincia_id=provincia_id,
            inmueble__isnull=False
        ).distinct()
    else:
        ciudades = Ciudad.objects.filter(
            inmueble__isnull=False
        ).distinct()

    return render(request, 'buscar_inmuebles.html', {
        'inmuebles': inmuebles,
        'query': query,
        'provincias': provincias,
        'ciudades': ciudades,
    })

def buscar_cocheras(request):
    """
    Permite buscar cocheras por nombre y muestra todas si no hay consulta.
    """
    query = request.GET.get('q', '').strip()
    
    # Solo mostrar cocheras que NO estén en estado Eliminado ni Oculto
    cocheras = Cochera.objects.exclude(estado__nombre__in=['Oculto','Eliminado'])

    if query:
        cocheras = cocheras.filter(nombre__icontains=query)
    
    return render(request, 'buscar_cocheras.html', {
        'cocheras': cocheras,
        'query': query
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
    reservas = Reserva.objects.filter(inmueble=inmueble, estado__nombre__in=['Confirmada', 'Pagada', 'Aprobada','Finalizada'])
    historial = InmuebleEstado.objects.filter(inmueble=inmueble).order_by('-fecha_inicio')

    es_usuario = request.user.is_authenticated and request.user.groups.filter(name="cliente").exists()
    is_admin_or_empleado_var = is_admin_or_empleado(request.user)
    is_admin_var = is_admin(request.user)

    usuario_resenia = None
    if request.user.is_authenticated:
        perfil = getattr(request.user, "perfil", None)
        if perfil:
            usuario_resenia = Resenia.objects.filter(inmueble=inmueble, usuario=perfil).first()

    # Fechas ocupadas
    fechas_ocupadas = []
    for reserva in reservas:
        current = reserva.fecha_inicio
        while current <= reserva.fecha_fin + timedelta(days=1):
            fechas_ocupadas.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)

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
        tiene_reserva_finalizada = reservas.filter(
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

    return render(request, 'inmueble.html', {
        'inmueble': inmueble,
        'resenias': resenias,
        'comentarios': comentarios,
        'comentario_form': comentario_form,
        'respuesta_form': respuesta_form,
        'resenia_form': resenia_form,
        'reservas': reservas,
        'historial': historial,
        'usuario_resenia': usuario_resenia,
        'respuestas': respuestas_dict,
        'fechas_ocupadas': fechas_ocupadas,
        'es_usuario': es_usuario,
        'is_admin_or_empleado': is_admin_or_empleado_var,
        'is_admin': is_admin_var,
        'puede_reseñar': puede_reseñar,
        'datos_cliente': datos_cliente, 
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

    # Fechas ocupadas
    fechas_ocupadas = []
    for reserva in reservas:
        current = reserva.fecha_inicio
        while current <= reserva.fecha_fin + timedelta(days=1):
            fechas_ocupadas.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)

    usuario_resenia = None
    if request.user.is_authenticated:
        perfil = getattr(request.user, "perfil", None)
        usuario_resenia = Resenia.objects.filter(cochera=cochera, usuario=perfil).first()

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
                resenia.cochera = cochera
                resenia.save()
                messages.success(request, "¡Reseña publicada!")
                return redirect('detalle_cochera', id_cochera=id_cochera)

        elif 'responder_comentario_id' in request.POST and is_admin_or_empleado_var:
            respuesta_form = RespuestaComentarioForm(request.POST)
            comentario_id = request.POST.get('responder_comentario_id')
            comentario = get_object_or_404(Comentario, id_comentario=comentario_id)
            if respuesta_form.is_valid():
                respuesta = respuesta_form.save(commit=False)
                respuesta.comentario = comentario
                respuesta.usuario = perfil
                respuesta.save()
                # Enviar notificación al usuario del comentario
                crear_notificacion(
                    usuario=comentario.usuario,
                    mensaje=f"Tu comentario en el inmueble {cochera.nombre} ha sido respondido.",
                )
                messages.success(request, "Respuesta publicada.")
                return redirect('detalle_cochera', id_cochera=id_cochera)

        elif request.user.is_authenticated:
            comentario_form = ComentarioForm(request.POST)
            if comentario_form.is_valid():
                comentario = comentario_form.save(commit=False)
                comentario.usuario = perfil
                comentario.cochera = cochera
                comentario.save()
                messages.success(request, "Comentario añadido exitosamente.")
                return redirect('detalle_cochera', id_cochera=id_cochera)

    # Diccionario de respuestas
    respuestas_dict = {
        r.comentario.id_comentario: r for r in RespuestaComentario.objects.filter(comentario__in=comentarios)
    }

    puede_reseñar = False
    if request.user.is_authenticated and es_usuario:
        # Busca reservas finalizadas de este usuario en esta cochera
        tiene_reserva_finalizada = reservas.filter(
            clienteinmueble__cliente=perfil,
            cochera=cochera,
            estado__nombre__iexact="Finalizada"
        ).exists()
        puede_reseñar = tiene_reserva_finalizada

    return render(request, 'cochera.html', {
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
        'respuestas': respuestas_dict,
        'es_usuario': es_usuario,
        'is_admin_or_empleado': is_admin_or_empleado_var,
        'is_admin': is_admin_var,
        'puede_reseñar': puede_reseñar,
    })