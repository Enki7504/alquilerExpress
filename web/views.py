from django.shortcuts import render
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.forms import UserCreationForm
from .models import Inmueble
from .forms import RegistroUsuarioForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .utils import email_link_token  # Ya tienes un token generator
from django.urls import reverse
from django.conf import settings
#from .models import LoginOTP
#import random
from django.utils import timezone




from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, render, redirect
from .models import Inmueble, Resenia, Comentario
from .forms import RegistroUsuarioForm, ComentarioForm, LoginForm
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
                    # Generar link seguro y mostrarlo en pantalla
                    uid = urlsafe_base64_encode(force_bytes(user_auth.pk))
                    token = email_link_token.make_token(user_auth)
                    link = request.build_absolute_uri(
                        reverse('verify_admin_link', kwargs={'uidb64': uid, 'token': token})
                    )
                    # Mostrar el link en pantalla (no enviar mail)
                    return render(request, 'login_link_sent.html', {
                        'email': user_auth.email,
                        'link': link
                    })
                else:
                    login(request, user_auth)
                    return redirect('index')
            else:
                messages.error(request, 'Usuario o contraseña inválidos.')
    return render(request, 'login.html', {'form': form})


from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

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
        return redirect('/admin/')   # o la vista principal de admin
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


# Funcionalidades del Admin
def is_admin(user):
    return user.is_authenticated and user.is_staff

@login_required
@user_passes_test(is_admin)
def admin_panel(request):
    return render(request, 'admin/admin_base.html')

@login_required
@user_passes_test(is_admin)
def admin_alta_inmuebles(request):
    return render(request, 'admin/admin_alta_inmuebles.html')

@login_required
@user_passes_test(is_admin)
def admin_alta_cocheras(request):
    return render(request, 'admin/admin_alta_cocheras.html')

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