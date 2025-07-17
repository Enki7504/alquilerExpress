from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone

# Importaciones de formularios locales
from ..forms import (
    NotificarImprevistoForm,
)

# Importaciones de modelos locales
from ..models import (
    Notificacion,
    Reserva,
    Inmueble,
    Cochera,
    ClienteInmueble
)

# Importaciones de utilidades locales
from ..utils import (
    crear_notificacion,
    is_admin_or_empleado,
)

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_notificar_imprevisto(request):
    inmuebles = Inmueble.objects.all()
    cocheras = Cochera.objects.all()
    estados_activos = ["Pendiente", "Pagada", "Confirmada", "Aceptada"]

    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        form = NotificarImprevistoForm(request.POST)
        if form.is_valid():
            objeto = form.cleaned_data["objeto"]
            mensaje = form.cleaned_data["mensaje"]

            empleado = None
            if objeto.startswith("Vivienda #"):
                try:
                    id_inmueble = int(objeto.split("#")[1].split("-")[0].strip())
                    inmueble = Inmueble.objects.get(id_inmueble=id_inmueble)
                    empleado = inmueble.empleado
                except (ValueError, Inmueble.DoesNotExist):
                    empleado = None
            elif objeto.startswith("Cochera #"):
                try:
                    id_cochera = int(objeto.split("#")[1].split("-")[0].strip())
                    cochera = Cochera.objects.get(id_cochera=id_cochera)
                    empleado = cochera.empleado
                except (ValueError, Cochera.DoesNotExist):
                    empleado = None

            if empleado:

                nombre_objeto = ""

                # Notificar a todos los clientes con reservas a futuro
                hoy_datetime = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                if objeto.startswith("Vivienda #"):
                    reservas_futuras = Reserva.objects.filter(
                        inmueble=inmueble,
                        fecha_inicio__gte=hoy_datetime,  # ← Cambio aquí
                        estado__nombre__in=estados_activos
                    )
                    nombre_objeto = inmueble.nombre
                elif objeto.startswith("Cochera #"):
                    reservas_futuras = Reserva.objects.filter(
                        cochera=cochera,
                        fecha_inicio__gte=hoy_datetime,  # ← Cambio aquí
                        estado__nombre__in=estados_activos
                    )
                    nombre_objeto = cochera.nombre
                else:
                    reservas_futuras = Reserva.objects.none()

                # ✅ CÓDIGO CORREGIDO - Sin duplicados
                clientes_notificados = set()  # Para evitar duplicados

                for reserva in reservas_futuras:
                    rel = ClienteInmueble.objects.filter(reserva=reserva).first()
                    if rel and rel.cliente.pk not in clientes_notificados:
                        cliente = rel.cliente
                        
                        # Contar cuántas reservas tiene este cliente
                        num_reservas = reservas_futuras.filter(
                            clienteinmueble__cliente=cliente
                        ).count()
                        
                        # Personalizar el mensaje según el número de reservas
                        if num_reservas == 1:
                            mensaje_personalizado = f"Imprevisto reportado en {nombre_objeto} donde tenes una reserva: '{mensaje}'"
                        else:
                            mensaje_personalizado = f"Imprevisto reportado en {nombre_objeto} donde tenes {num_reservas} reservas: '{mensaje}'"
                        
                        crear_notificacion(
                            usuario=cliente,
                            mensaje=mensaje_personalizado
                        )
                        
                        # Marcar cliente como notificado
                        clientes_notificados.add(cliente.pk)

                # Notificar al empleado asignado
                crear_notificacion(
                    usuario=empleado,
                    mensaje=f"Imprevisto reportado en {nombre_objeto}: '{mensaje}'"
                )
                        
                return JsonResponse({
                    "success": True,
                    "icon": "success",
                    "title": "¡Listo!",
                    "text": "Imprevisto notificado correctamente al empleado y a los clientes con reservas a futuro."
                })
            else:
                return JsonResponse({
                    "success": False,
                    "icon": "warning",
                    "title": "Atención",
                    "text": "No se encontró un empleado asignado a la vivienda o cochera seleccionada."
                })
        else:
            # Errores de validación
            errores = []
            for field, error_list in form.errors.items():
                for error in error_list:
                    errores.append(error)
            return JsonResponse({
                "success": False,
                "icon": "error",
                "title": "Error",
                "text": " ".join(errores)
            })
    else:
        form = NotificarImprevistoForm()
    return render(request, "admin/admin_notificar_imprevisto.html", {
        "form": form,
        "inmuebles": inmuebles,
        "cocheras": cocheras,
    })

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