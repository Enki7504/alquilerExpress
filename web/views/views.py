import datetime
import random
import json
import secrets
import string

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
from django.db.models import Q
from datetime import timedelta
# mercado pago
from django.views.decorators.csrf import csrf_exempt

# Importaciones de formularios locales
from ..forms import (
    RegistroUsuarioForm,
    InmuebleForm,
    CocheraForm,
    ComentarioForm,
    LoginForm,
    EmpleadoAdminCreationForm,
    ChangePasswordForm,
    ReseniaForm,
    RespuestaComentarioForm,
    NotificarImprevistoForm,
    ClienteAdminCreationForm
)

# Importaciones de modelos locales
from ..models import (
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
    Cochera,
    RespuestaComentario,
    Tarjeta,
    Provincia,
)

# Importaciones de utilidades locales
from ..utils import (
    email_link_token,
    crear_notificacion,
    cambiar_estado_inmueble
)

################################################################################################################
# --- Vistas Públicas Generales ---
################################################################################################################

def index(request):
    """
    Renderiza la página de inicio de la aplicación.
    """
    # Tomar las primeras 5 imágenes de inmuebles
    hero_imgs = [img.imagen.url for img in InmuebleImagen.objects.all()[:5] if img.imagen]
    # Si se quiere sumar cocheras, descomentar la línea:
    # hero_imgs += [img.imagen.url for img in CocheraImagen.objects.all()[:5] if img.imagen]

    # Si no hay imágenes en la BD, usar imágenes por defecto
    if not hero_imgs:
        hero_imgs = [
            "https://images.unsplash.com/photo-1560184897-292b8d0a21d6?auto=format&fit=crop&w=1350&q=80",
            "https://images.unsplash.com/photo-1590080877777-9b9b28d24d7d?auto=format&fit=crop&w=600&q=80",
            "https://images.unsplash.com/photo-1600585154197-3c2f1d93d9e0?auto=format&fit=crop&w=600&q=80"
        ]

    mostrar_bienvenida = request.session.pop('mostrar_bienvenida', False)
    return render(request, 'index.html', {'hero_imgs': hero_imgs, 'mostrar_bienvenida': mostrar_bienvenida})

def logout_view(request):
    """
    Cierra la sesión del usuario. Solo procesa solicitudes POST.
    Redirige al usuario a la página de login después de cerrar sesión.
    """
    if request.method == 'POST':
        logout(request)
        messages.success(request, "Has cerrado sesión correctamente.")
        return redirect('login')
    # Si alguien entra por GET, lo mandamos al index
    return redirect('index')

def register(request):
    """
    Maneja el registro de nuevos usuarios (clientes).
    """
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cuenta creada exitosamente. Por favor, inicia sesión.")
            return redirect('login')
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = RegistroUsuarioForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    """
    Maneja el inicio de sesión de usuarios (clientes y administradores/empleados).
    Si es un administrador/empleado, inicia el flujo de autenticación de dos factores.
    """
    form = LoginForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, 'Usuario o contraseña inválidos.')
                return render(request, 'login.html', {'form': form})

            user_auth = authenticate(request, username=user.username, password=password)
            if user_auth is not None:
                if user_auth.is_staff:
                    # Si es admin o empleado, inicia 2FA
                    codigo = f"{random.randint(0, 999999):06d}"
                    LoginOTP.objects.update_or_create(
                        user=user_auth,
                        defaults={"codigo": codigo, "creado_en": timezone.now()},
                    )
                    send_mail(
                        "Código de verificación",
                        f"Tu código para ingresar al panel administrativo es: {codigo}",
                        settings.DEFAULT_FROM_EMAIL,
                        [user_auth.email],
                        fail_silently=False,
                    )
                    request.session["username_otp"] = user_auth.username
                    return redirect("loginAdmin_2fa")
                else:
                    login(request, user_auth)
                    request.session['mostrar_bienvenida'] = True
                    messages.success(request, f"Bienvenido, {user_auth.first_name}!")
                    return redirect('index')
            else:
                messages.error(request, 'Usuario o contraseña inválidos.')
    return render(request, 'login.html', {'form': form})

def loginAdmin(request):
    """
    Vista para el login inicial de administradores/empleados antes del 2FA.
    Genera y envía el código OTP al correo del usuario.
    """
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user and (user.is_staff or user.groups.filter(name="empleado").exists()):
            codigo = f"{random.randint(0, 999999):06d}"

            LoginOTP.objects.update_or_create(
                user=user,
                defaults={"codigo": codigo, "creado_en": timezone.now()},
            )

            send_mail(
                "Código de verificación",
                f"Tu código para ingresar al panel administrativo es: {codigo}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            request.session["username_otp"] = username
            messages.info(request, "Se ha enviado un código de verificación a tu correo electrónico.")
            return redirect("loginAdmin_2fa")
        messages.error(request, "Credenciales inválidas o no tienes permisos de administrador/empleado.")
        return render(request, "loginAdmin.html", {"error": "Credenciales inválidas o no es administrador"})

    return render(request, "loginAdmin.html")

def loginAdmin_2fa(request):
    """
    Vista para la verificación de dos factores (2FA) para administradores/empleados.
    Verifica el código OTP ingresado por el usuario.
    """
    tiempo_restante = 70
    error = None

    if "username_otp" in request.session:
        try:
            user = User.objects.get(username=request.session["username_otp"])
            otp_obj = LoginOTP.objects.get(user=user)
            expiracion = otp_obj.creado_en + timedelta(minutes=1)
            ahora = timezone.now()
            tiempo_restante = int((expiracion - ahora).total_seconds())
            if tiempo_restante <= 0:
                error = "El tiempo para ingresar el código ha expirado. Vuelva a iniciar sesión."
                tiempo_restante = 0 
        except (User.DoesNotExist, LoginOTP.DoesNotExist):
            tiempo_restante = 0

    if request.method == "POST":
        codigo_ingresado = request.POST.get("codigo")

        if tiempo_restante <= 0:
            error = "El tiempo para ingresar el código ha expirado. Vuelva a iniciar sesión."
        elif not otp_obj.is_valido():
            error = "El código ha expirado. Vuelva a iniciar sesión."
        elif otp_obj.codigo != codigo_ingresado:
            error = "Código inválido."
        else:
            login(request, user)
            request.session.pop("username_otp", None)
            otp_obj.delete()
            return redirect("/panel")

        return render(request, "loginAdmin_2fa.html", {
            "error": error,
            "tiempo_restante": max(tiempo_restante, 0)
        })

    return render(request, "loginAdmin_2fa.html", {
        "error": None,
        "tiempo_restante": tiempo_restante
    })

def loginAdmin_2fa_reenviar(request):
    if request.method == "POST":
        username = request.session.get("username_otp")
        if not username:
            return JsonResponse({"success": False, "error": "Sesión inválida."})
        try:
            user = User.objects.get(username=username)
            nuevo_codigo = LoginOTP.generar_para_usuario(user)
            send_mail(
                "Código de verificación",
                f"Tu código para ingresar al panel administrativo es: {nuevo_codigo.codigo}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            return JsonResponse({"success": True, "tiempo_restante": 60})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Método no permitido."})

def verify_admin_link(request, uidb64, token):
    """
    Vista para verificar el enlace de inicio de sesión de administrador enviado por correo.
    (Actualmente no utilizada en el flujo principal de 2FA, pero mantenida si es necesaria).
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError):
        user = None

    if user is not None and email_link_token.check_token(user, token):
        login(request, user)
        messages.success(request, "Inicio de sesión exitoso a través del enlace.")
        return redirect('index')   # o la vista principal de admin
    else:
        messages.error(request, "El enlace de verificación es inválido o ha expirado.")
        return render(request, 'link_invalid.html')

################################################################################################################
# --- Vistas de Búsqueda y Detalle de Inmuebles/Cocheras ---
################################################################################################################

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

    return render(request, 'busqueda/buscar_inmuebles.html', {
        'inmuebles': inmuebles,
        'query': query,
        'provincias': provincias,
        'ciudades': ciudades,
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

    return render(request, 'busqueda/buscar_cocheras.html', {
        'cocheras': cocheras,
        'query': query,
        'provincias': provincias,
        'ciudades': ciudades,
    })

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

################################################################################################################
# --- Funciones para filtrar ---
################################################################################################################

def obtener_provincias_y_ciudades(tipo='inmueble', provincia_id=None):
    if tipo == 'inmueble':
        provincias = Provincia.objects.filter(ciudades__inmueble__isnull=False).distinct()
        if provincia_id:
            ciudades = Ciudad.objects.filter(
                provincia_id=provincia_id,
                inmueble__isnull=False
            ).distinct()
        else:
            ciudades = Ciudad.objects.filter(
                inmueble__isnull=False
            ).distinct()
    elif tipo == 'cochera':
        provincias = Provincia.objects.filter(ciudades__cochera__isnull=False).distinct()
        if provincia_id:
            ciudades = Ciudad.objects.filter(
                provincia_id=provincia_id,
                cochera__isnull=False
            ).distinct()
        else:
            ciudades = Ciudad.objects.filter(
                cochera__isnull=False
            ).distinct()
    else:
        provincias = Provincia.objects.none()
        ciudades = Ciudad.objects.none()
    return provincias, ciudades

# para cargar las ciudades en el formulario de registro
def cargar_ciudades(request):
    provincia_id = request.GET.get('provincia')
    ciudades = Ciudad.objects.filter(provincia_id=provincia_id).order_by('nombre')
    ciudades_list = [{'id': ciudad.id, 'nombre': ciudad.nombre} for ciudad in ciudades]
    return JsonResponse({'ciudades': ciudades_list})

def cargar_ciudades_filtro(request):
    provincia_id = request.GET.get('provincia')
    tipo = request.GET.get('tipo', 'inmueble')
    if tipo == 'inmueble':
        ciudades = Ciudad.objects.filter(
            provincia_id=provincia_id,
            inmueble__isnull=False
        ).distinct()
    else:
        ciudades = Ciudad.objects.filter(
            provincia_id=provincia_id,
            cochera__isnull=False
        ).distinct()
    data = {'ciudades': [{'id': c.id, 'nombre': c.nombre} for c in ciudades]}
    return JsonResponse(data)

################################################################################################################
# --- Funciones de Ayuda para Permisos ---
################################################################################################################

def is_admin(user):
    """Verifica si el usuario es un superusuario."""
    return user.is_authenticated and user.is_staff

def is_empleado(user):
    """Verifica si el usuario es un superusuario."""
    return user.is_authenticated and user.groups.filter(name="empleado").exists()

def is_admin_or_empleado(user):
    """Verifica si el usuario es un superusuario o pertenece al grupo 'empleado'."""
    return user.is_authenticated and (user.is_staff or user.groups.filter(name="empleado").exists())

def is_client(user):
    """Verifica si el usuario es un cliente."""
    return user.is_authenticated and user.groups.filter(name="cliente").exists()

################################################################################################################
# --- Vistas del Panel de Administración --- Gestion de Usuarios  --- 
################################################################################################################

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_panel(request):
    """
    Renderiza el panel principal de administración/empleado.
    """
    return render(request, 'admin/admin_base.html')

@login_required
@user_passes_test(is_admin)
def admin_alta_empleados(request):
    if request.method == "POST":
        form = EmpleadoAdminCreationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
            user = User.objects.create_user(
                username=data["email"],
                email=data["email"],
                password=password,
                first_name=data["first_name"].title(),
                last_name=data["last_name"].title(),
            )
            grupo_empleado, _ = Group.objects.get_or_create(name="empleado")
            firstlogin_empleado, _ = Group.objects.get_or_create(name="firstloginempleado")
            user.groups.add(grupo_empleado)
            user.groups.add(firstlogin_empleado)
            Perfil.objects.create(
                usuario=user,
                dni=form.cleaned_data['dni'],
                fecha_nacimiento=form.cleaned_data['fecha_nacimiento']
            )
            # Enviar mail con la contraseña
            try:
                send_mail(
                    "Bienvenido a AlquilerExpress - Acceso de Empleado",
                    f"Hola {user.first_name},\n\n"
                    f"Tu cuenta de empleado ha sido creada.\n"
                    f"Usuario: {user.email}\n"
                    f"Contraseña temporal: {password}\n\n"
                    f"Por favor, inicia sesión y cambia tu contraseña.",
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                message = f"Empleado registrado y correo enviado a {user.email}."
                icon = "success"
                status = "success"
            except Exception as e:
                message = f"Empleado creado, pero error enviando el correo: {e}"
                icon = "warning"
                status = "success"
            # AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    "status": status,
                    "message": message,
                    "icon": icon,
                })
            # Tradicional
            messages.success(request, message)
            return redirect('admin_alta_empleados')
        else:
            # Errores de formulario
            errors = {field: error[0] for field, error in form.errors.items()}
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    "status": "form_errors",
                    "errors": errors,
                    "icon": "error",
                    "message": "Corrige los errores del formulario."
                })
            messages.error(request, "Corrige los errores del formulario.")
    else:
        form = EmpleadoAdminCreationForm()
    return render(request, 'admin/admin_alta_empleados.html', {'form': form})

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_alta_cliente(request):
    """
    Permite a administradores y empleados dar de alta un cliente.
    El cliente es agregado al grupo 'cliente' y 'firstlogincliente' para forzar cambio de contraseña.
    """
    if request.method == "POST":
        form = ClienteAdminCreationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
            user = User.objects.create_user(
                username=data["email"],
                email=data["email"],
                password=password,
                first_name=data["first_name"].title(),
                last_name=data["last_name"].title(),
            )
            grupo_cliente, _ = Group.objects.get_or_create(name="cliente")
            firstlogin_cliente, _ = Group.objects.get_or_create(name="firstlogincliente")
            user.groups.add(grupo_cliente)
            user.groups.add(firstlogin_cliente)
            Perfil.objects.create(
                usuario=user,
                dni=form.cleaned_data['dni'],
                fecha_nacimiento=form.cleaned_data['fecha_nacimiento']
            )
            # Enviar mail con la contraseña
            try:
                send_mail(
                    "Bienvenido a AlquilerExpress - Acceso de Cliente",
                    f"Hola {user.first_name},\n\n"
                    f"Tu cuenta de cliente ha sido creada.\n"
                    f"Usuario: {user.email}\n"
                    f"Contraseña temporal: {password}\n\n"
                    f"Por favor, inicia sesión y cambia tu contraseña.",
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                message = f"Cliente registrado y correo enviado a {user.email}."
                icon = "success"
                status = "success"
            except Exception as e:
                message = f"Cliente creado, pero error enviando el correo: {e}"
                icon = "warning"
                status = "success"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': status, 'message': message, 'icon': icon})
            messages.success(request, message)
            return redirect('admin_alta_cliente')
        else:
            errors = {field: error[0] for field, error in form.errors.items()}
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'form_errors', 'errors': errors})
            messages.error(request, "Corrige los errores en el formulario.")
    else:
        form = ClienteAdminCreationForm()
    return render(request, 'admin/admin_alta_cliente.html', {'form': form})

##################
# Complementarias
##################

def _respuesta_empleado(request, status, message, icon, errors=None, form=None):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        resp = {'status': status, 'message': message, 'icon': icon}
        if errors:
            resp['errors'] = errors
        return JsonResponse(resp)
    else:
        if status == 'success':
            messages.success(request, message)
            return redirect('admin_alta_empleados')
        elif status == 'warning':
            messages.warning(request, message)
            return redirect('admin_alta_empleados')
        elif status == 'error':
            messages.error(request, message)
            return redirect('admin_alta_empleados')
        elif status == 'form_errors':
            return render(request, 'admin/admin_alta_empleados.html', {'form': form})

def _respuesta_cliente(request, status, message, icon, errors=None, form=None):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        resp = {'status': status, 'message': message, 'icon': icon}
        if errors:
            resp['errors'] = errors
        return JsonResponse(resp)
    else:
        if status == 'success':
            messages.success(request, message)
            return redirect('admin_alta_cliente')
        elif status == 'warning':
            messages.warning(request, message)
            return redirect('admin_alta_cliente')
        elif status == 'error':
            messages.error(request, message)
            return redirect('admin_alta_cliente')
        elif status == 'form_errors':
            return render(request, 'admin/admin_alta_cliente.html', {'form': form})

def generar_contraseña_segura():
    alphabet = string.ascii_letters + string.digits + string.punctuation
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(12))
        if (any(c.isupper() for c in password) and
            any(c.islower() for c in password) and
            any(c.isdigit() for c in password) and
            any(c in string.punctuation for c in password)):
            return password

################################################################################################################
# --- Vistas del Panel de Administración --- Gestion de Propiedades  --- 
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

    return render(request, 'admin/admin_inmuebles.html', {
        'inmuebles': inmuebles,
        'query': query,
        'empleados': empleados,
        'admins': admins
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

################################################################################################################
# --- Vistas del Panel de Administración --- Estadisticas  --- 
################################################################################################################

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_estadisticas_usuarios(request):
    """
    Muestra estadísticas relacionadas con los usuarios.
    """
    return render(request, 'admin/admin_estadisticas_usuarios.html')

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_estadisticas_empleados(request):
    """
    Muestra estadísticas relacionadas con los empleados.
    """
    return render(request, 'admin/admin_estadisticas_empleados.html')

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_estadisticas_cocheras(request):
    """
    Muestra estadísticas relacionadas con las cocheras.
    """
    return render(request, 'admin/admin_estadisticas_cocheras.html')

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_estadisticas_inmuebles(request):
    """
    Muestra estadísticas relacionadas con los inmuebles.
    """
    return render(request, 'admin/admin_estadisticas_inmuebles.html')

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
# --- Vistas de Notificaciones ---
################################################################################################################

@login_required
def marcar_notificacion(request, id_notificacion):
    """
    Marca una notificación específica como leída para el usuario actual.
    """
    notificacion = get_object_or_404(Notificacion, id=id_notificacion, usuario=request.user.perfil)
    if notificacion.leido:
        notificacion.leido = True
        notificacion.save()
        messages.info(request, "Notificación marcada como leída.")
    next_url = request.POST.get('next', '/')
    return redirect(next_url)

@login_required
def eliminar_notificacion(request, notificacion_id):
    """
    Elimina una notificación específica para el usuario actual.
    """
    notificacion = get_object_or_404(
        Notificacion, 
        id=notificacion_id, 
        usuario=request.user.perfil
    )
    notificacion.delete()
    return redirect(request.META.get('HTTP_REFERER', 'index'))

@require_POST
@login_required
def marcar_todas_leidas(request):
    """
    Marca todas las notificaciones no leídas del usuario actual como leídas.
    """
    try:
        request.user.perfil.notificacion_set.filter(leido=False).update(leido=True)
        return JsonResponse({'success': True})
    except Exception as e:
        messages.error(request, f"Error al marcar notificaciones: {e}")
        return JsonResponse({'success': False, 'error': str(e)}) 
    
################################################################################################################
# --- OTRAS VISTAS ---
################################################################################################################

@login_required
def cambiar_contrasena(request):
    if request.method == "POST":
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            new_password = form.cleaned_data["new_password1"]
            request.user.set_password(new_password)
            request.user.save()
            # Quitar de los grupos firstlogin
            for group_name in ["firstloginempleado", "firstlogincliente"]:
                group = Group.objects.filter(name=group_name).first()
                if group:
                    request.user.groups.remove(group)
            # Mantener sesión activa
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)
            messages.success(request, "Contraseña cambiada exitosamente. Ya puedes usar el sistema normalmente.")
            return redirect("index")
    else:
        form = ChangePasswordForm(request.user)
    return render(request, "cambiar_contrasena.html", {"form": form})

def simulador_mercadopago(request):
    saldo = request.GET.get('saldo', '0.00')
    precio = request.GET.get('precio', '0.00')
    id_reserva = request.GET.get('id_reserva')

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

            estado_pagada = Estado.objects.get(nombre='Pagada')
            reserva.estado = estado_pagada
            reserva.save()
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
    })

################################################################################################################
# --- NOTIFICACIONES ---
################################################################################################################

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_notificar_imprevisto(request):
    if request.method == "POST":
        form = NotificarImprevistoForm(request.POST)
        if form.is_valid():
            usuario = form.cleaned_data["usuario"]
            mensaje = form.cleaned_data["mensaje"]
            crear_notificacion(usuario, mensaje)
            messages.success(request, "Imprevisto notificado correctamente.")
            return redirect('admin_panel')
    else:
        form = NotificarImprevistoForm()
    return render(request, "admin/admin_notificar_imprevisto.html", {"form": form})


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



def agregar_tarjeta(request):
    from .forms import TarjetaForm
    if request.method == 'POST':
        form = TarjetaForm(request.POST)
        if form.is_valid():
            tarjeta = form.save(commit=False)
            tarjeta.saldo = 0  # Saldo inicial ficticio
            tarjeta.save()
            messages.success(request, "Tarjeta agregada correctamente.")
            return redirect('pagar_reserva', id_reserva=request.GET.get('id_reserva'))
    else:
        form = TarjetaForm()
    return render(request, 'agregar_tarjeta.html', {'form': form})

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

################################################################################################################
# --- MERCADO PAGO  ---
################################################################################################################


def crear_preferencia_mp(request):
    if request.method == "POST":
        import mercadopago
        import json
        from django.conf import settings
        from django.http import JsonResponse

        data = json.loads(request.body)
        monto = data.get('monto', 1000)
        descripcion = data.get('descripcion', 'Reserva Alquiler Express')
        id_reserva = data.get('id_reserva')

        # Verificar que la reserva esté en estado "Aprobada"
        try:
            reserva = Reserva.objects.get(id_reserva=id_reserva)
        except Reserva.DoesNotExist:
            return JsonResponse({"error": "Reserva no encontrada."}, status=404)

        if reserva.estado.nombre != "Aprobada":
            return JsonResponse({"error": "Solo se puede pagar una reserva en estado Aprobada."}, status=400)

        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        preference_data = {
            "items": [
                {
                    "title": descripcion,
                    "quantity": 1,
                    "unit_price": float(monto),
                }
            ],
            "back_urls": {
                "success": "https://reptile-genuine-redbird.ngrok-free.app/reservas/",
                "failure": "https://reptile-genuine-redbird.ngrok-free.app/reservas/",
                "pending": "https://reptile-genuine-redbird.ngrok-free.app/reservas/",
            },
            "auto_return": "approved",
            "external_reference": str(id_reserva),
            "notification_url": "https://reptile-genuine-redbird.ngrok-free.app/mercadopago/webhook/",
        }
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response.get("response", {})
        if "id" in preference:
            return JsonResponse({
                "id": preference["id"],
                "init_point": preference.get("init_point")
            })
        else:
            return JsonResponse({"error": preference.get("message", "Error al crear preferencia"), "detalle": preference}, status=400)

def probar_mp(request):
    return render(request, 'probar_mp.html', {
        'MERCADOPAGO_PUBLIC_KEY': settings.MERCADOPAGO_PUBLIC_KEY,
        'precio': 1000,  # o el valor que quieras probar
    })



@csrf_exempt
def mercadopago_webhook(request):
    import mercadopago
    import json

    payment_id = None

    # Solo procesar si es topic=payment
    if request.GET.get("topic") == "payment" and request.GET.get("id"):
        payment_id = request.GET.get("id")
    elif request.GET.get("type") == "payment" and request.GET.get("data.id"):
        payment_id = request.GET.get("data.id")
    elif request.body:
        try:
            data = json.loads(request.body)
            payment_id = (
                data.get("data", {}).get("id")
                or data.get("id")
                or data.get("payment_id")
            )
        except Exception:
            pass

    if not payment_id:
        # Si no es un pago, simplemente responde 200 OK para otros topics
        return JsonResponse({"success": True})

    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
    payment_info = sdk.payment().get(payment_id)
    payment = payment_info.get("response", {})

    if payment.get("status") == "approved":
        reserva_id = payment.get("external_reference")
        if reserva_id:
            try:
                reserva = Reserva.objects.get(id_reserva=reserva_id)
                estado_pagada = Estado.objects.get(nombre="Pagada")
                reserva.estado = estado_pagada
                reserva.save()
                return JsonResponse({"success": True})
            except Reserva.DoesNotExist:
                return JsonResponse({"error": "Reserva no encontrada"}, status=404)
    return JsonResponse({"success": False})