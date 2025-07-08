from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render
from ..forms import NotificarImprevistoForm
from ..models import Notificacion
from ..utils import (
    is_admin_or_empleado,
)

def crear_notificacion(usuario, mensaje):
    """
    Crea una notificación para el usuario indicado.
    """
    notificacion = Notificacion.objects.create(
        usuario=usuario,
        mensaje=mensaje
    )
    print(f"Notificación creada para {usuario.usuario.username}: {mensaje}")
    return notificacion

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