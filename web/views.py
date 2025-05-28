import datetime
import random
import json

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST


from .forms import (
    RegistroUsuarioForm,
    InmuebleForm,
    CocheraForm,
    ComentarioForm,
    LoginForm,
)
from .models import (
    Inmueble,
    InmuebleImagen,
    InmuebleEstado,
    InmuebleCochera,
    CocheraImagen,
    Resenia,
    Comentario,
    LoginOTP,
    Reserva,
    ClienteInmueble,
    Estado,
    Perfil,
    ReservaEstado,
)
from .utils import email_link_token

# Create your views here.

def index(request):
    return render(request, 'index.html')

def logout_view(request):
    """Sólo procesa POST para cerrar sesión y redirige a login"""
    if request.method == 'POST':
        logout(request)
        messages.success(request, "Has cerrado sesión correctamente.")
        return redirect('login')
    # si alguien entra por GET, lo mandamos al index
    return redirect('index')

def register(request):
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = RegistroUsuarioForm()
    return render(request, 'register.html', {'form': form})

def lista_inmuebles(request):
    inmuebles = Inmueble.objects.all()
    return render(request, 'lista_inmuebles.html', {'inmuebles': inmuebles})

def buscar_inmuebles(request):
    inmuebles = Inmueble.objects.all()
    return render(request, 'buscar_inmuebles.html', {'inmuebles': inmuebles})

def detalle_inmueble(request, id_inmueble):
    inmueble = get_object_or_404(
        Inmueble.objects.select_related('estado'),
        id_inmueble=id_inmueble
    )
    resenias = Resenia.objects.filter(inmueble=inmueble)
    comentarios = Comentario.objects.filter(inmueble=inmueble).order_by('-fecha_creacion')
    # Obtener reservas activas
    reservas = Reserva.objects.filter(inmueble=inmueble, estado__nombre__in=['Confirmada', 'Pendiente']).order_by('-fecha_inicio')
    # Obtener historial de estados (ajustado para manejar casos sin InmuebleCochera)
    historial = InmuebleEstado.objects.filter(inmueble_cochera__inmueble=inmueble).order_by('-fecha_inicio') if InmuebleCochera.objects.filter(inmueble=inmueble).exists() else []

    if request.method == 'POST' and request.user.is_authenticated:
        comentario_form = ComentarioForm(request.POST)
        if comentario_form.is_valid():
            comentario = comentario_form.save(commit=False)
            comentario.usuario = request.user.perfil
            comentario.inmueble = inmueble
            comentario.save()
            return redirect('detalle_inmueble', id_inmueble=id_inmueble)
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


def login_view(request):
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
                    # Si es admin, inicia 2FA
                    codigo = f"{random.randint(0, 999999):06d}"
                    LoginOTP.objects.update_or_create(
                        user=user_auth,
                        defaults={"codigo": codigo, "creado_en": timezone.now()},
                    )
                    send_mail(
                        "Código de verificación",
                        f"Tu código para ingresar al panel administrativo es: {codigo}",
                        "admin@tusitio.com",
                        [user_auth.email],
                        fail_silently=False,
                    )
                    request.session["username_otp"] = user_auth.username
                    return redirect("loginAdmin_2fa")
                else:
                    login(request, user_auth)
                    return redirect('index')
            else:
                messages.error(request, 'Usuario o contraseña inválidos.')
    return render(request, 'login.html', {'form': form})


def verify_admin_link(request, uidb64, token):
    """
    Vista que se accede haciendo clic en el email.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError):
        user = None

    if user is not None and email_link_token.check_token(user, token):
        login(request, user)
        return redirect('index')   # o la vista principal de admin
    else:
        return render(request, 'link_invalid.html')


def loginAdmin_2fa(request):
    if request.method == "POST":
        codigo_ingresado = request.POST.get("codigo")
        username = request.session.get("username_otp")

        if not username:
            return redirect("loginAdmin")

        try:
            user = User.objects.get(username=username)
            otp_obj = LoginOTP.objects.get(user=user)
        except (User.DoesNotExist, LoginOTP.DoesNotExist):
            return redirect("loginAdmin")

        if otp_obj.is_valido() and otp_obj.codigo == codigo_ingresado:
            login(request, user)
            del request.session["username_otp"]
            otp_obj.delete()
            return redirect("/admin/")
        else:
            return render(request, "loginAdmin_2fa.html", {"error": "Código inválido o expirado"})

    return render(request, "loginAdmin_2fa.html")
    ({
            'resenias': resenias,
            'comentarios': comentarios,
            'comentario_form': comentario_form,
        })


# Funcionalidades del Panel de Admin
def is_admin(user):
    return user.is_authenticated and user.is_staff

@login_required
@user_passes_test(is_admin)
def admin_panel(request):
    return render(request, 'admin/admin_base.html')

def admin_alta_inmuebles(request):
    if request.method == 'POST':
        form = InmuebleForm(request.POST, request.FILES)
        if form.is_valid():
            # Guardar el inmueble completamente
            inmueble = form.save(commit=False)
            inmueble.fecha_publicacion = timezone.now().date()
            inmueble.save()  # Guardar el inmueble en la base de datos
            form.save_m2m()  # Guardar relaciones many-to-many si las hay
            
            # Crear la imagen después de guardar el inmueble
            if form.cleaned_data.get('imagen'):
                InmuebleImagen.objects.create(
                    inmueble=inmueble,
                    imagen=form.cleaned_data['imagen'],
                    descripcion="Imagen principal"
                )
            
            messages.success(request, 'Inmueble creado exitosamente.')
            return redirect('admin_alta_inmuebles')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = InmuebleForm()
    
    return render(request, 'admin/admin_alta_inmuebles.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def admin_alta_cocheras(request):
    if request.method == 'POST':
        form = CocheraForm(request.POST, request.FILES)
        if form.is_valid():
            # Guardar la cochera completamente
            cochera = form.save(commit=False)
            cochera.fecha_publicacion = timezone.now().date()
            cochera.save()  # Guardar la cochera en la base de datos
            form.save_m2m()  # Guardar relaciones many-to-many si las hay
            
            # Crear la imagen después de guardar la cochera
            if form.cleaned_data.get('imagen'):
                CocheraImagen.objects.create(
                    cochera=cochera,
                    imagen=form.cleaned_data['imagen'],
                    descripcion="Imagen principal"
                )
            
            messages.success(request, 'Cochera creada exitosamente.')
            return redirect('admin_alta_cocheras')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = CocheraForm()
    
    return render(request, 'admin/admin_alta_cocheras.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def admin_alta_empleados(request):
    return render(request, 'admin/admin_alta_empleados.html')

@login_required
@user_passes_test(is_admin)
def admin_estadisticas_usuarios(request):
    return render(request, 'admin/admin_estadisticas_usuarios.html')

@login_required
@user_passes_test(is_admin)
def admin_estadisticas_empleados(request):
    return render(request, 'admin/admin_estadisticas_empleados.html')

@login_required
@user_passes_test(is_admin)
def admin_estadisticas_cocheras(request):
    return render(request, 'admin/admin_estadisticas_cocheras.html')

@login_required
@user_passes_test(is_admin)
def admin_estadisticas_inmuebles(request):
    return render(request, 'admin/admin_estadisticas_inmuebles.html')

# Cosas de los inmuebles
@login_required
@user_passes_test(is_admin)
def admin_inmueble_editar(request, id_inmueble):
    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
    if request.method == 'POST':
        form = InmuebleForm(request.POST, request.FILES, instance=inmueble)
        if form.is_valid():
            inmueble = form.save()
            if form.cleaned_data.get('imagen'):
                InmuebleImagen.objects.create(
                    inmueble=inmueble,
                    imagen=form.cleaned_data['imagen'],
                    descripcion="Imagen actualizada"
                )
            messages.success(request, 'Inmueble actualizado exitosamente.')
            return redirect('detalle_inmueble', id_inmueble=id_inmueble)
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = InmuebleForm(instance=inmueble)
    return render(request, 'admin/admin_inmueble_editar.html', {'form': form, 'inmueble': inmueble})

@login_required
@user_passes_test(is_admin)
def admin_inmueble_eliminar(request, id_inmueble):
    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
    if request.method == 'POST':
        inmueble.delete()
        messages.success(request, 'Inmueble eliminado exitosamente.')
        return redirect('buscar_inmuebles')
    return redirect('detalle_inmueble', id_inmueble=id_inmueble)

@login_required
@user_passes_test(is_admin)
def admin_inmueble_historial(request, id_inmueble):
    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
    historial = InmuebleEstado.objects.filter(inmueble_cochera__inmueble=inmueble).order_by('-fecha_inicio') if InmuebleCochera.objects.filter(inmueble=inmueble).exists() else []
    return render(request, 'admin/admin_inmueble_historial.html', {'inmueble': inmueble, 'historial': historial})

@login_required
@user_passes_test(is_admin)
def admin_inmueble_estado(request, id_inmueble):
    inmueble = get_object_or_404(Inmueble, id_inmueble=id_inmueble)
    reservas = Reserva.objects.filter(inmueble=inmueble).order_by('-fecha_inicio')
    return render(request, 'admin/admin_inmueble_estado.html', {'inmueble': inmueble, 'reservas': reservas})

def crear_reserva(request, id_inmueble):
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


@require_POST
@login_required
@user_passes_test(is_admin)
def cambiar_estado_reserva(request, id_reserva):
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
        
        if (reserva.estado.nombre in transiciones_permitidas and 
            nuevo_estado in transiciones_permitidas[reserva.estado.nombre]):
            
            reserva.estado = estado
            reserva.save()
            
            # # Registrar en historial
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