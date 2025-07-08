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
from django.urls import reverse
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

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_panel(request):
    """
    Renderiza el panel principal de administración/empleado.
    """
    return render(request, 'admin/admin_base.html')

##################
# Gestion de Usuarios
##################

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

from django.contrib import messages

@login_required
@user_passes_test(is_admin)
def admin_bloquear_cliente(request):
    query = request.GET.get('q', '').strip()

    clientes_activos = User.objects.filter(is_active=True, is_staff=False)
    if query:
        clientes_activos = clientes_activos.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query)
        )

    clientes_bloqueados = User.objects.filter(is_active=False, is_staff=False)

    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')
        accion = request.POST.get('accion')

        cliente = get_object_or_404(User, id=cliente_id)

        if accion == 'bloquear':
            cliente.is_active = False
            messages.success(request, 'Cliente bloqueado correctamente.')
        elif accion == 'desbloquear':
            cliente.is_active = True
            messages.success(request, 'Cliente desbloqueado correctamente.')

        cliente.save()
        return redirect('admin_bloquear_cliente')

    return render(request, 'admin/admin_bloquear_cliente.html', {
        'clientes_activos': clientes_activos,
        'clientes_bloqueados': clientes_bloqueados,
        'query': query
    })


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