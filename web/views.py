from django.shortcuts import render
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.forms import UserCreationForm
from .models import Inmueble, Resenia
from .forms import RegistroUsuarioForm
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.urls import reverse
from django.conf import settings
from .utils import email_link_token
from .forms import AdminLoginForm






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

    resenias = Resenia.objects.filter(
        inmueble=inmueble
    )

    return render(request, 'inmueble.html', {
        'inmueble': inmueble,
        'resenias': resenias
    })


def login_admin_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # validamos que exista y sea staff
        try:
            user = User.objects.get(email=email)
            if not user.is_staff:
                messages.error(request, 'No tienes permisos de administrador.')
                return redirect('login_admin')
        except User.DoesNotExist:
            messages.error(request, 'Usuario no registrado.')
            return redirect('login_admin')

        user_auth = authenticate(request, username=user.username, password=password)
        if user_auth is not None:
            # generamos UID y token
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = email_link_token.make_token(user)
            # construimos la URL de verificación
            verify_url = request.build_absolute_uri(
                reverse('verify_admin_link', kwargs={'uidb64': uidb64, 'token': token})
            )
            # enviamos el correo
            send_mail(
                subject='Verifica tu inicio de sesión',
                message=f'Haz clic en este enlace para completar tu login:\n\n{verify_url}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
            return render(request, 'login_link_sent.html', {'email': user.email})
        else:
            messages.error(request, 'Credenciales incorrectas.')
    return render(request, 'login_admin.html')


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