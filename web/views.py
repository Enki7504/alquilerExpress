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
from django.db import IntegrityError, transaction
from django.db.models import Q
from datetime import timedelta
from django.template.loader import render_to_string


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
)

# Importaciones de utilidades locales
from .utils import (
    email_link_token,
    crear_notificacion
)

# para enviar correos a empleados sobre reservas
from .utils import enviar_mail_a_empleados_sobre_reserva


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
    if request.method == "POST":
        codigo_ingresado = request.POST.get("codigo")
        username = request.session.get("username_otp")

        if not username:
            messages.error(request, 'Sesión 2FA inválida o expirada. Por favor, inicia sesión de nuevo.')
            return redirect("login") # Redirigir a login en lugar de loginAdmin

        try:
            user = User.objects.get(username=username)
            otp_obj = LoginOTP.objects.get(user=user)
        except (User.DoesNotExist, LoginOTP.DoesNotExist):
            # Si no encuentra el usuario o el OTP, significa que no hay sesión válida para 2FA
            messages.error(request, 'Sesión 2FA inválida o expirada. Por favor, inicia sesión de nuevo.')
            return redirect("login")

        if otp_obj.is_valido() and otp_obj.codigo == codigo_ingresado:
            login(request, user)
            request.session.pop("username_otp", None) # Usar .pop() para evitar KeyError
            otp_obj.delete()
            messages.success(request, "Inicio de sesión exitoso en el panel administrativo.")
            return redirect("/panel")
        else:
            messages.error(request, "Código inválido o expirado.")
            return render(request, "loginAdmin_2fa.html", {"error": "Código inválido o expirado"})

    return render(request, "loginAdmin_2fa.html")

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
    provincia_id = request.GET.get('provincia')
    ciudad_id = request.GET.get('ciudad')
    precio = request.GET.get('precio')
    ubicacion = request.GET.get('ubicacion')
    huespedes = request.GET.get('huespedes')
    ambientes = request.GET.get('ambientes')
    camas = request.GET.get('camas')
    banios = request.GET.get('banios')

    inmuebles = Inmueble.objects.all()
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
    
    if query:
        # Búsqueda solo por nombre para cocheras
        cocheras = Cochera.objects.filter(nombre__icontains=query)
    else:
        cocheras = Cochera.objects.all()
    
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
                messages.success(request, "Respuesta publicada.")
                return redirect('detalle_inmueble', id_inmueble=id_inmueble)

        elif request.user.is_authenticated:
            comentario_form = ComentarioForm(request.POST)
            if comentario_form.is_valid():
                comentario = comentario_form.save(commit=False)
                comentario.usuario = perfil
                comentario.inmueble = inmueble
                comentario.save()
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

################################################################################################################
# --- Funciones para filtrar ---
################################################################################################################

# def cargar_ciudades_filtro(request):
#     provincia_id = request.GET.get('provincia')
#     # Solo ciudades de la provincia seleccionada que tengan al menos un inmueble
#     ciudades = Ciudad.objects.filter(
#         provincia_id=provincia_id,
#         inmueble__isnull=False
#     ).distinct().order_by('nombre')
#     ciudades_list = [{'id': ciudad.id, 'nombre': ciudad.nombre} for ciudad in ciudades]
#     return JsonResponse({'ciudades': ciudades_list})

def cargar_ciudades_filtro(request):
    provincia_id = request.GET.get('provincia')
    tipo = request.GET.get('tipo')
    if tipo == 'cochera':
        ciudades = Ciudad.objects.filter(
            provincia_id=provincia_id,
            cochera__isnull=False
        ).distinct().order_by('nombre')
    else:
        ciudades = Ciudad.objects.filter(
            provincia_id=provincia_id,
            inmueble__isnull=False
        ).distinct().order_by('nombre')
    ciudades_list = [{'id': ciudad.id, 'nombre': ciudad.nombre} for ciudad in ciudades]
    return JsonResponse({'ciudades': ciudades_list})

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
            Perfil.objects.create(usuario=user, dni=data["dni"])
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
@user_passes_test(is_admin)
def admin_alta_cliente(request):
    """
    Permite a administradores y empleados dar de alta un cliente.
    El cliente es agregado al grupo 'cliente' y 'firstlogincliente' para forzar cambio de contraseña.
    """
    from django.contrib.auth.models import Group
    from .forms import ClienteAdminCreationForm
    import secrets, string

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
            Perfil.objects.create(usuario=user, dni=data["dni"])
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
    return render(request, 'admin/admin_inmuebles.html', {
        'inmuebles': inmuebles,
        'query': query,
        'empleados': empleados,
    })

@login_required
@user_passes_test(is_admin)
def cambiar_empleado_inmueble(request, id_inmueble):
    if request.method == "POST":
        inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
        empleado_id = request.POST.get("empleado")
        if empleado_id:
            empleado = Perfil.objects.get(id_perfil=empleado_id)
            inmueble.empleado = empleado
        else:
            inmueble.empleado = None
        inmueble.save()
        messages.success(request, "Empleado asignado actualizado.")
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
    return render(request, 'admin/admin_cocheras.html', {
        'cocheras': cocheras,
        'query': query,
        'empleados': empleados,
    })

@login_required
@user_passes_test(is_admin)
def cambiar_empleado_cochera(request, id_cochera):
    if request.method == "POST":
        cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
        empleado_id = request.POST.get("empleado")
        if empleado_id:
            empleado = Perfil.objects.get(id_perfil=empleado_id)
            cochera.empleado = empleado
        else:
            cochera.empleado = None
        cochera.save()
        messages.success(request, "Empleado asignado actualizado.")
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

        # Eliminar el inmueble (cambiar estado)
        estado_eliminado, _ = Estado.objects.get_or_create(nombre='Eliminado')
        inmueble.estado = estado_eliminado
        inmueble.save()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Vivienda marcada como eliminada. Reservas pendientes a futuro canceladas.'})

        messages.success(request, 'Vivienda marcada como eliminada. Reservas pendientes a futuro canceladas.')
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
    Muestra el historial de estados de un inmueble específico.
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
    reservas = Reserva.objects.filter(inmueble=inmueble).order_by('-fecha_inicio')
    return render(request, 'admin/admin_inmuebles_reservas.html', {'inmueble': inmueble, 'reservas': reservas})

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

        # Eliminar la cochera (cambiar estado)
        estado_eliminado, _ = Estado.objects.get_or_create(nombre='Eliminado')
        cochera.estado = estado_eliminado
        cochera.save()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Cochera marcada como eliminada. Reservas pendientes a futuro canceladas.'})

        messages.success(request, 'Cochera marcada como eliminada. Reservas pendientes a futuro canceladas.')
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
    Muestra el historial de estados de una cochera específica.
    """
    cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
    historial = CocheraEstado.objects.filter(cochera=cochera).order_by('-fecha_inicio')
    return render(request, 'admin/admin_cocheras_historial.html', {'cochera': cochera, 'historial': historial})

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_cocheras_reservas(request, id_cochera):
    """
    Muestra el estado actual y las reservas de una cochera específica.
    """
    cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
    reservas = Reserva.objects.filter(cochera=cochera).order_by('-fecha_inicio')
    return render(request, 'admin/admin_cocheras_reservas.html', {'cochera': cochera, 'reservas': reservas})

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

# crear reserva para inmuebles y cocheras
@login_required
def crear_reserva(request, id_inmueble):
    """
    Permite a los usuarios crear una reserva para un inmueble.
    Valida las fechas y calcula el precio total.
    """
    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
    
    if request.method == 'POST':
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        
        if not fecha_inicio or not fecha_fin:
            messages.error(request, 'Debes ingresar ambas fechas.')
            return redirect('detalle_inmueble', id_inmueble=id_inmueble)
            
        try:
            fecha_inicio = datetime.datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin = datetime.datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            
            if fecha_inicio >= fecha_fin:
                messages.error(request, 'La fecha de salida debe ser posterior a la de llegada.')
                return redirect('detalle_inmueble', id_inmueble=id_inmueble)

            dias = (fecha_fin - fecha_inicio).days
            if dias < inmueble.minimo_dias_alquiler:
                messages.error(request, f"El mínimo de noches de alquiler para esta vivienda es {inmueble.minimo_dias_alquiler}.")
                return redirect('detalle_inmueble', id_inmueble=id_inmueble)
            
            # --- VALIDACIÓN DE RESERVA SUPERPUESTA DEL USUARIO ---
            perfil = request.user.perfil
            reserva_superpuesta_usuario = Reserva.objects.filter(
                clienteinmueble__cliente=perfil,
                inmueble__isnull=False,
                estado__nombre__in=['Confirmada', 'Pagada', 'Aprobada'],
                fecha_inicio__lt=fecha_fin,
                fecha_fin__gt=fecha_inicio
            ).exists()
            if reserva_superpuesta_usuario:
                messages.error(request, "Ya tenés una reserva de vivienda que se superpone con las fechas seleccionadas.")
                return redirect('detalle_inmueble', id_inmueble=id_inmueble)
            # -----------------------------------------------------

            # --- VALIDACIÓN DE RESERVAS SUPERPUESTAS EN EL INMUEBLE ---
            reservas_superpuestas = Reserva.objects.filter(
                inmueble=inmueble,
                estado__nombre__in=['Confirmada', 'Pagada', 'Aprobada'],
                fecha_inicio__lt=fecha_fin,
                fecha_fin__gt=fecha_inicio
            )
            if reservas_superpuestas.exists():
                messages.error(request, "La vivienda ya está reservada en esas fechas.")
                return redirect('detalle_inmueble', id_inmueble=id_inmueble)
            # ---------------------------------------------------------


            # Calcular días y precio total
            dias = (fecha_fin - fecha_inicio).days
            precio_total = dias * inmueble.precio_por_dia
            
            # Crear la reserva
            reserva = Reserva.objects.create(
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                precio_total=precio_total,
                inmueble=inmueble,
                estado=Estado.objects.get(nombre='Pendiente'),  # Asegúrate de que este estado exista
                descripcion=f"Reserva para {inmueble.nombre} del {fecha_inicio} al {fecha_fin}"
            )
            
            # Relacionar el cliente con la reserva
            if request.user.is_authenticated:
                ClienteInmueble.objects.create(
                    cliente=request.user.perfil,
                    inmueble=inmueble,
                    reserva=reserva
                )

            # Enviar notificación a todos los empleados
            # usando enviar_mail_a_empleados_sobre_reserva(id_reserva) de utils.py
            enviar_mail_a_empleados_sobre_reserva(reserva.id_reserva)            
            
            messages.success(request, 'Reserva creada exitosamente!')
            return redirect('detalle_inmueble', id_inmueble=id_inmueble)
            
        except ValueError:
            messages.error(request, 'Formato de fecha inválido.')
            return redirect('detalle_inmueble', id_inmueble=id_inmueble)
    
    # Si no es POST, redirigir al detalle del inmueble
    return redirect('detalle_inmueble', id_inmueble=id_inmueble)

@login_required
def crear_reserva_cochera(request, id_cochera):
    """
    Permite a los usuarios crear una reserva para una cochera.
    Valida las fechas y calcula el precio total.
    """
    cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
    
    if request.method == 'POST':
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        
        if not fecha_inicio or not fecha_fin:
            messages.error(request, 'Debes ingresar ambas fechas.')
            return redirect('detalle_cochera', id_cochera=id_cochera)
            
        try:
            fecha_inicio = datetime.datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin = datetime.datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            
            if fecha_inicio >= fecha_fin:
                messages.error(request, 'La fecha de fin debe ser posterior a la de inicio.')
                return redirect('detalle_cochera', id_cochera=id_cochera)
                
            dias = (fecha_fin - fecha_inicio).days
            if dias < cochera.minimo_dias_alquiler:
                messages.error(request, f"El mínimo de noches de alquiler para esta cochera es {cochera.minimo_dias_alquiler}.")
                return redirect('detalle_cochera', id_cochera=id_cochera)
            
            # --- VALIDACIÓN DE RESERVA SUPERPUESTA DEL USUARIO ---
            perfil = request.user.perfil
            reserva_superpuesta_usuario = Reserva.objects.filter(
                clienteinmueble__cliente=perfil,
                cochera__isnull=False,
                estado__nombre__in=['Confirmada', 'Pagada', 'Aprobada'],
                fecha_inicio__lt=fecha_fin,
                fecha_fin__gt=fecha_inicio
            ).exists()
            if reserva_superpuesta_usuario:
                messages.error(request, "Ya tenés una reserva de cochera que se superpone con las fechas seleccionadas.")
                return redirect('detalle_cochera', id_cochera=id_cochera)
            # -----------------------------------------------------

            # --- Validar que no haya reservas superpuestas ---
            reservas_superpuestas = Reserva.objects.filter(
                cochera=cochera,
                estado__nombre__in=['Confirmada', 'Pagada', 'Aprobada'],
                fecha_inicio__lt=fecha_fin,
                fecha_fin__gt=fecha_inicio
            )
            if reservas_superpuestas.exists():
                messages.error(request, "La cochera ya está reservada en esas fechas.")
                return redirect('detalle_cochera', id_cochera=id_cochera)
            # ------------------------------------------------------
                
            # Calcular días y precio total
            dias = (fecha_fin - fecha_inicio).days
            precio_total = dias * cochera.precio_por_dia
            
            # Crear la reserva
            reserva = Reserva.objects.create(
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                precio_total=precio_total,
                cochera=cochera,
                estado=Estado.objects.get(nombre='Pendiente'),
                descripcion=f"Reserva para {cochera.nombre} del {fecha_inicio} al {fecha_fin}"
            )
            
            # Relacionar el cliente con la reserva
            if request.user.is_authenticated:
                ClienteInmueble.objects.create(
                    cliente=request.user.perfil,
                    cochera=cochera,
                    reserva=reserva
                )

            # Enviar notificación a todos los empleados
            # usando enviar_mail_a_empleados_sobre_reserva(id_reserva) de utils.py
            enviar_mail_a_empleados_sobre_reserva(reserva.id_reserva)    
            
            messages.success(request, 'Reserva creada exitosamente!')
            return redirect('detalle_cochera', id_cochera=id_cochera)
            
        except ValueError:
            messages.error(request, 'Formato de fecha inválido.')
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
            'Pendiente': ['Aprobada', 'Rechazada', 'Cancelada'],
            'Aprobada': ['Pagada', 'Cancelada', 'Rechazada'],
            'Pagada': ['Confirmada', 'Cancelada'],
            'Confirmada': ['Finalizada', 'Cancelada']
        }
        
        if (reserva.estado and 
            reserva.estado.nombre in transiciones_permitidas and 
            nuevo_estado in transiciones_permitidas[reserva.estado.nombre]):
            
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
                    if nuevo_estado == "Aprobada":
                        cuerpo += f"\nAhora debe abonar la reserva, el total es de ${reserva.precio_total}.\n"
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


                    cuerpo += f"\nGracias por usar Alquiler Express."

                    crear_notificacion(
                        usuario=cliente_rel.cliente,
                        mensaje=f"El estado de tu reserva #{reserva.id_reserva} ha cambiado a: {estado.nombre}" + (f" (Comentario: {comentario})" if comentario else "") + "."
                    )
                    
                    send_mail(
                        subject=asunto,
                        message=cuerpo,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email_cliente],
                        fail_silently=False,
                    )
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
                    if nuevo_estado == "Aprobada":
                        cuerpo += f"\nAhora debe abonar la reserva, el total es de ${reserva.precio_total}.\n"
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
                    
                    crear_notificacion(
                        usuario=cliente_rel.cliente,
                        mensaje=f"El estado de tu reserva #{reserva.id_reserva} ha cambiado a: {estado.nombre}"
                    )

                    send_mail(
                        subject=asunto,
                        message=cuerpo,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email_cliente],
                        fail_silently=False,
                    )
            
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
    messages.success(request, "Notificación eliminada.")
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

# para cargar las ciudades en el formulario de registro
def cargar_ciudades(request):
    provincia_id = request.GET.get('provincia')
    ciudades = Ciudad.objects.filter(provincia_id=provincia_id).order_by('nombre')
    ciudades_list = [{'id': ciudad.id, 'nombre': ciudad.nombre} for ciudad in ciudades]
    return JsonResponse({'ciudades': ciudades_list})

@login_required
def cambiar_contrasena(request):
    from django.contrib.auth.models import Group
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

@login_required
def eliminar_comentario(request, id_comentario):
    if request.method == "POST" and is_admin_or_empleado(request.user):
        comentario = get_object_or_404(Comentario, id_comentario=id_comentario)
        comentario.delete()
        messages.success(request, "Comentario eliminado correctamente.")
    return redirect(request.META.get('HTTP_REFERER', 'index'))


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