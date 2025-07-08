import random

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from datetime import timedelta

# Importaciones de formularios locales
from ..forms import (
    RegistroUsuarioForm,
    LoginForm,
)

# Importaciones de modelos locales
from ..models import (
    InmuebleImagen,
    LoginOTP,
)

# Importaciones de utilidades locales
from ..utils import (
    email_link_token
)

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