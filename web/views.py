from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, render, redirect
from .models import Inmueble, Resenia
from .forms import RegistroUsuarioForm
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