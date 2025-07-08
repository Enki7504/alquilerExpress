from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

# Importaciones de formularios locales
from ..forms import (
    NotificarImprevistoForm,
)

# Importaciones de modelos locales
from ..models import (
    Notificacion,
    Reserva
)

# Importaciones de utilidades locales
from ..utils import (
    crear_notificacion,
    is_admin_or_empleado,
)

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_notificar_imprevisto(request):
    if request.method == 'POST':
        form = NotificarImprevistoForm(request.POST)
        if form.is_valid():
            inmueble = form.cleaned_data['inmueble']
            mensaje = form.cleaned_data['mensaje']

            # Notificar al empleado asignado
            if hasattr(inmueble, 'empleado_asignado') and inmueble.empleado_asignado:
                crear_notificacion(inmueble.empleado_asignado, f"Imprevisto en {inmueble}: {mensaje}")

            # Notificar a todos los clientes con reservas activas
            reservas_activas = Reserva.objects.filter(inmueble=inmueble, estado='Pagada')
            for reserva in reservas_activas:
                crear_notificacion(reserva.cliente, f"Imprevisto en {inmueble}: {mensaje}")

            messages.success(request, "Se notificó al empleado y a los clientes con reservas activas.")
            return redirect('admin_notificar_imprevisto')
    else:
        form = NotificarImprevistoForm()

    return render(request, 'admin/admin_notificar_imprevisto.html', {'form': form})


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