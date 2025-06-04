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
)

# Importaciones de modelos locales
from .models import (
    Inmueble,
    InmuebleImagen,
    InmuebleEstado,
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
)

# Importaciones de utilidades locales
from .utils import email_link_token


################################################################################################################
# --- Vistas Públicas Generales ---
################################################################################################################

def index(request):
    """
    Renderiza la página de inicio de la aplicación.
    """
    return render(request, 'index.html')

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
                if user_auth.is_staff or user_auth.groups.filter(name="empleado").exists():
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
    """
    Permite buscar inmuebles por nombre y muestra todos si no hay consulta.
    """
    query = request.GET.get('q', '').strip() # Elimina espacios en blanco
    
    if query:
        # Búsqueda solo por nombre (insensible a mayúsculas/minúsculas)
        inmuebles = Inmueble.objects.filter(nombre__icontains=query)
    else:
        # Si no hay query, mostrar todos los inmuebles
        inmuebles = Inmueble.objects.all()
    
    return render(request, 'buscar_inmuebles.html', {
        'inmuebles': inmuebles,
        'query': query
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
    """
    Muestra los detalles de un inmueble específico, incluyendo reseñas, comentarios,
    reservas activas e historial de estados. Permite añadir comentarios.
    """
    inmueble = get_object_or_404(
        Inmueble.objects.select_related('estado'),
        id_inmueble=id_inmueble
    )
    resenias = Resenia.objects.filter(inmueble=inmueble)
    comentarios = Comentario.objects.filter(inmueble=inmueble).order_by('-fecha_creacion')
    # Obtener reservas activas
    reservas = Reserva.objects.filter(inmueble=inmueble, estado__nombre__in=['Confirmada', 'Pendiente']).order_by('-fecha_inicio')
    # Eliminar referencia a InmuebleCochera
    historial = InmuebleEstado.objects.filter(inmueble=inmueble).order_by('-fecha_inicio')

    if request.method == 'POST' and request.user.is_authenticated:
        comentario_form = ComentarioForm(request.POST)
        if comentario_form.is_valid():
            comentario = comentario_form.save(commit=False)
            comentario.usuario = request.user.perfil
            comentario.inmueble = inmueble
            comentario.save()
            messages.success(request, "Comentario añadido exitosamente.")
            return redirect('detalle_inmueble', id_inmueble=id_inmueble)
        else:
            messages.error(request, "Error al añadir el comentario.")
    else:
        comentario_form = ComentarioForm()

    return render(request, 'inmueble.html', {
        'inmueble': inmueble,
        'resenias': resenias,
        'comentarios': comentarios,
        'comentario_form': comentario_form,
        'reservas': reservas,
        'historial': historial,
    })

def detalle_cochera(request, id_cochera):
    """
    Muestra los detalles de una cochera específica, incluyendo reservas activas
    e historial de estados.
    """
    cochera = get_object_or_404(
        Cochera.objects.select_related('estado'),
        id_cochera=id_cochera
    )
    # Obtener reservas activas
    reservas = Reserva.objects.filter(cochera=cochera, estado__nombre__in=['Confirmada', 'Pendiente']).order_by('-fecha_inicio')
    
    # Obtener historial de estados
    historial = InmuebleEstado.objects.filter(inmueble_cochera__cochera=cochera).order_by('-fecha_inicio') if InmuebleCochera.objects.filter(cochera=cochera).exists() else []
    
    return render(request, 'cochera.html', {
        'cochera': cochera,
        'reservas': reservas,
        'historial': historial,
    })


################################################################################################################
# --- Funciones de Ayuda para Permisos ---
################################################################################################################

def is_admin(user):
    """Verifica si el usuario es un superusuario."""
    return user.is_authenticated and user.is_staff

def is_admin_or_empleado(user):
    """Verifica si el usuario es un superusuario o pertenece al grupo 'empleado'."""
    return user.is_authenticated and (user.is_staff or user.groups.filter(name="empleado").exists())


################################################################################################################
# --- Vistas del Panel de Administración/Empleado ---
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
def admin_alta_empleados(request):
    """
    Permite a los administradores dar de alta nuevos empleados.
    Genera una contraseña temporal y la envía por correo electrónico.
    """
    mensaje = None
    error = None
    if request.method == "POST":
        form = EmpleadoAdminCreationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            # Generar contraseña aleatoria segura
            password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
            
            # Crear usuario
            user = User.objects.create_user(
                username=data["email"],
                email=data["email"],
                password=password,
                first_name=data["first_name"].title(),
                last_name=data["last_name"].title(),
            )
            # Asignar grupo "empleado"
            grupo_empleado, _ = Group.objects.get_or_create(name="empleado")
            user.groups.add(grupo_empleado)
            # Crear perfil
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
                mensaje = f"Empleado registrado y correo enviado a {user.email}."
            except Exception as e:
                error = f"Empleado creado, pero error enviando el correo: {e}"
        else:
            error = "Corrige los errores del formulario."
    else:
        form = EmpleadoAdminCreationForm()
    return render(request, 'admin/admin_alta_empleados.html', {
        'form': form,
        'mensaje': mensaje,
        'error': error,
    })

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_inmuebles(request):
    """
    Lista todos los inmuebles y permite la búsqueda.
    Incluye botones para acciones rápidas (ver, editar, eliminar, estado, historial).
    """
    query = request.GET.get('q', '').strip()
    inmuebles = Inmueble.objects.all().order_by('nombre') # Ordenar para una mejor visualización

    if query:
        # Búsqueda por nombre o descripción
        inmuebles = inmuebles.filter(
            Q(nombre__icontains=query) | Q(descripcion__icontains=query)
        ).distinct() # Usar distinct por si hay duplicados en el join de Q

    return render(request, 'admin/admin_inmuebles.html', {
        'inmuebles': inmuebles,
        'query': query
    })

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_cocheras(request):
    """
    Lista todas las cocheras y permite la búsqueda.
    Incluye botones para acciones rápidas (ver, editar, eliminar, estado, historial).
    """
    query = request.GET.get('q', '').strip()
    cocheras = Cochera.objects.all().order_by('nombre') # Ordenar para una mejor visualización

    if query:
        # Búsqueda por nombre o descripción
        cocheras = cocheras.filter(
            Q(nombre__icontains=query) | Q(descripcion__icontains=query)
        ).distinct()

    return render(request, 'admin/admin_cocheras.html', {
        'cocheras': cocheras,
        'query': query
    })


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
# --- Vistas de Gestión de Inmuebles (Admin/Empleado) ---
################################################################################################################

@login_required
@user_passes_test(is_admin)
def admin_inmuebles_editar(request, id_inmueble):
    """
    Permite a los administradores editar la información de un inmueble existente.
    """
    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
    imagenes = InmuebleImagen.objects.filter(inmueble=inmueble)
    
    if request.method == 'POST':
        form = InmuebleForm(request.POST, request.FILES, instance=inmueble)
        if form.is_valid():
            inmueble = form.save()
            
            # Manejar múltiples imágenes
            for img in request.FILES.getlist('imagenes'):
                InmuebleImagen.objects.create(
                    inmueble=inmueble,
                    imagen=img,
                    descripcion="Imagen del inmueble"
                )
                
            messages.success(request, 'Inmueble actualizado exitosamente.')
            return redirect('detalle_inmueble', id_inmueble=id_inmueble)
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = InmuebleForm(instance=inmueble)
    
    return render(request, 'admin/admin_inmuebles_editar.html', {
        'form': form, 
        'inmueble': inmueble,
        'imagenes': imagenes
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
    Permite a los administradores eliminar un inmueble existente.
    """
    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
    if request.method == 'POST':
        inmueble.delete()
        messages.success(request, 'Inmueble eliminado exitosamente.')
        return redirect('buscar_inmuebles')
    messages.info(request, "Confirmación de eliminación de inmueble.")
    return redirect('detalle_inmueble', id_inmueble=id_inmueble)

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_inmuebles_historial(request, id_inmueble):
    """
    Muestra el historial de estados de un inmueble específico.
    """
    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
    # Eliminar referencia a InmuebleCochera
    historial = InmuebleEstado.objects.filter(inmueble=inmueble).order_by('-fecha_inicio')
    return render(request, 'admin/admin_inmueble_historial.html', {'inmueble': inmueble, 'historial': historial})

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_inmuebles_estado(request, id_inmueble):
    """
    Muestra el estado actual y las reservas de un inmueble específico.
    """
    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
    reservas = Reserva.objects.filter(inmueble=inmueble).order_by('-fecha_inicio')
    return render(request, 'admin/admin_inmuebles_estado.html', {'inmueble': inmueble, 'reservas': reservas})


################################################################################################################
# --- Vistas de Gestión de Cocheras (Admin) ---
################################################################################################################

@login_required
@user_passes_test(is_admin)
def admin_cocheras_editar(request, id_cochera):
    """
    Permite a los administradores editar la información de una cochera existente.
    """
    cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
    if request.method == 'POST':
        form = CocheraForm(request.POST, request.FILES, instance=cochera)
        if form.is_valid():
            cochera = form.save()
            if form.cleaned_data.get('imagen'):
                CocheraImagen.objects.create(
                    cochera=cochera,
                    imagen=form.cleaned_data['imagen'],
                    descripcion="Imagen actualizada"
                )
            messages.success(request, 'Cochera actualizada exitosamente.')
            return redirect('detalle_cochera', id_cochera=id_cochera)
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = CocheraForm(instance=cochera)
    return render(request, 'admin/admin_cocheras_editar.html', {'form': form, 'cochera': cochera})

@login_required
@user_passes_test(is_admin)
def admin_cocheras_eliminar(request, id_cochera):
    """
    Permite a los administradores eliminar una cochera existente.
    """
    cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
    if request.method == 'POST':
        cochera.delete()
        messages.success(request, 'Cochera eliminada exitosamente.')
        return redirect('buscar_cocheras')
    messages.info(request, "Confirmación de eliminación de cochera.")
    return redirect('detalle_cochera', id_cochera=id_cochera)

@login_required
@user_passes_test(is_admin)
def admin_cocheras_historial(request, id_cochera):
    """
    Muestra el historial de estados de una cochera específica.
    """
    cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
    historial = InmuebleEstado.objects.filter(inmueble_cochera__cochera=cochera).order_by('-fecha_inicio') if InmuebleCochera.objects.filter(cochera=cochera).exists() else []
    return render(request, 'admin/admin_cocheras_historial.html', {'cochera': cochera, 'historial': historial})

@login_required
@user_passes_test(is_admin)
def admin_cocheras_estado(request, id_cochera):
    """
    Muestra el estado actual y las reservas de una cochera específica.
    """
    cochera = get_object_or_404(Cochera, id_cochera=id_cochera)
    reservas = Reserva.objects.filter(cochera=cochera).order_by('-fecha_inicio')
    return render(request, 'admin/admin_cocheras_estado.html', {'cochera': cochera, 'reservas': reservas})


################################################################################################################
# --- Vistas de Gestión de Reservas ---
################################################################################################################

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
            
            messages.success(request, 'Reserva creada exitosamente!')
            return redirect('detalle_inmueble', id_inmueble=id_inmueble)
            
        except ValueError:
            messages.error(request, 'Formato de fecha inválido.')
            return redirect('detalle_inmueble', id_inmueble=id_inmueble)
    
    # Si no es POST, redirigir al detalle del inmueble
    return redirect('detalle_inmueble', id_inmueble=id_inmueble)

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
            
            messages.success(request, 'Reserva creada exitosamente!')
            return redirect('detalle_cochera', id_cochera=id_cochera)
            
        except ValueError:
            messages.error(request, 'Formato de fecha inválido.')
            return redirect('detalle_cochera', id_cochera=id_cochera)
    
    return redirect('detalle_cochera', id_cochera=id_cochera)

@require_POST
@login_required
@user_passes_test(is_admin)
def cambiar_estado_reserva(request, id_reserva):
    """
    Permite a los administradores cambiar el estado de una reserva de inmueble.
    Valida las transiciones de estado permitidas.
    """
    reserva = get_object_or_404(Reserva, id_reserva=id_reserva)
    
    try:
        # Parsear el cuerpo JSON de la solicitud
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
        
        # Validar transición de estados permitida
        transiciones_permitidas = {
            'Pendiente': ['Aprobada', 'Rechazada', 'Cancelada'],
            'Aprobada': ['Pagada', 'Cancelada', 'Rechazada'],
            'Pagada': ['Confirmada', 'Cancelada'],
            'Confirmada': ['Finalizada', 'Cancelada']
        }
        
        if (reserva.estado and # Asegurarse de que reserva.estado no sea None
            reserva.estado.nombre in transiciones_permitidas and 
            nuevo_estado in transiciones_permitidas[reserva.estado.nombre]):
            
            reserva.estado = estado
            reserva.save()
            
            # Registrar en historial (descomentar si la funcionalidad está activa)
            # HistorialEstadoReserva.objects.create(
            #     reserva=reserva,
            #     estado=estado,
            #     usuario=request.user,
            #     comentario=comentario
            # )
            
            return JsonResponse({'success': True})
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
        

@require_POST
@login_required
@user_passes_test(is_admin)
def cambiar_estado_reserva_cochera(request, id_reserva):
    """
    Permite a los administradores cambiar el estado de una reserva de cochera.
    Valida las transiciones de estado permitidas.
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
        
        # Validar transición de estados permitida (misma lógica que para inmuebles)
        transiciones_permitidas = {
            'Pendiente': ['Aprobada', 'Rechazada', 'Cancelada'],
            'Aprobada': ['Pagada', 'Cancelada', 'Rechazada'],
            'Pagada': ['Confirmada', 'Cancelada'],
            'Confirmada': ['Finalizada', 'Cancelada']
        }
        
        if (reserva.estado and # Asegurarse de que reserva.estado no sea None
            reserva.estado.nombre in transiciones_permitidas and 
            nuevo_estado in transiciones_permitidas[reserva.estado.nombre]):
            
            reserva.estado = estado
            reserva.save()
            
            return JsonResponse({'success': True})
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
# --- Vistas de Registro de Clientes/Empleados (por Admin) ---
################################################################################################################

def registrar_empleado(request):
    """
    Permite a los administradores registrar un nuevo empleado.
    (Esta vista parece ser una alternativa a admin_alta_empleados, revisar si ambas son necesarias).
    """
    if request.method == "POST":
        form = EmpleadoCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Empleado registrado exitosamente.")
            return redirect("login")  # o donde quieras
        else:
            messages.error(request, "Error al registrar el empleado. Por favor, corrige los errores.")
    else:
        form = EmpleadoCreationForm()
    return render(request, "registrar_empleado.html", {"form": form})

def registrar_cliente(request):
    """
    Permite a los administradores registrar un nuevo cliente.
    (Esta vista parece ser una alternativa a 'register', revisar si ambas son necesarias).
    """
    if request.method == "POST":
        form = ClienteCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente registrado exitosamente.")
            return redirect("login")  # o a donde quieras redirigir
        else:
            messages.error(request, "Error al registrar el cliente. Por favor, corrige los errores.")
    else:
        form = ClienteCreationForm()
    return render(request, "registrar_cliente.html", {"form": form})

# para cargar las ciudades en el formulario de registro
def cargar_ciudades(request):
    provincia_id = request.GET.get('provincia')
    ciudades = Ciudad.objects.filter(provincia_id=provincia_id).order_by('nombre')
    ciudades_list = [{'id': ciudad.id, 'nombre': ciudad.nombre} for ciudad in ciudades]
    return JsonResponse({'ciudades': ciudades_list})

################################################################################################################
# --- Vistas de Notificaciones ---
################################################################################################################

@login_required
def marcar_notificacion(request, id_notificacion):
    """
    Marca una notificación específica como leída para el usuario actual.
    """
    notificacion = get_object_or_404(Notificacion, id=id_notificacion, usuario=request.user.perfil)
    if not notificacion.leido:
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

