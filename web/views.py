from django.contrib import messages
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Inmueble, InmuebleImagen, Resenia, LoginOTP, CocheraImagen
from .forms import RegistroUsuarioForm, InmuebleForm, CocheraForm
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.core.mail import send_mail
<<<<<<< HEAD
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .utils import email_link_token  # Ya tienes un token generator
from django.urls import reverse
from django.conf import settings
#from .models import LoginOTP
#import random
=======
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.urls import reverse
from django.conf import settings
from .utils import email_link_token
import random
>>>>>>> fd88279700f7f702891059572ca6b7cc8c258698
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
<<<<<<< HEAD
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
=======
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
>>>>>>> fd88279700f7f702891059572ca6b7cc8c258698
                else:
                    login(request, user_auth)
                    return redirect('index')
            else:
                messages.error(request, 'Usuario o contraseña inválidos.')
    return render(request, 'login.html', {'form': form})


<<<<<<< HEAD
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

=======
>>>>>>> fd88279700f7f702891059572ca6b7cc8c258698
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
<<<<<<< HEAD
        return redirect('/admin/')   # o la vista principal de admin
=======
        return redirect('index')   # o la vista principal de admin
>>>>>>> fd88279700f7f702891059572ca6b7cc8c258698
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


<<<<<<< HEAD
# Funcionalidades del Admin
=======
# Funcionalidades del Panel de Admin
>>>>>>> fd88279700f7f702891059572ca6b7cc8c258698
def is_admin(user):
    return user.is_authenticated and user.is_staff

@login_required
@user_passes_test(is_admin)
def admin_panel(request):
    return render(request, 'admin/admin_base.html')

<<<<<<< HEAD
@login_required
@user_passes_test(is_admin)
def admin_alta_inmuebles(request):
    return render(request, 'admin/admin_alta_inmuebles.html')
=======
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

>>>>>>> fd88279700f7f702891059572ca6b7cc8c258698

@login_required
@user_passes_test(is_admin)
def admin_alta_cocheras(request):
<<<<<<< HEAD
    return render(request, 'admin/admin_alta_cocheras.html')
=======
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
>>>>>>> fd88279700f7f702891059572ca6b7cc8c258698

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