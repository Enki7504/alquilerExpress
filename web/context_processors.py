from django.contrib.auth.models import AnonymousUser
from .models import Notificacion

def notifications(request):
    if request.user.is_authenticated:
        try:
            return {
                'notificaciones': request.user.perfil.notificacion_set.order_by('-fecha_creacion')[:10],
                'notificaciones_no_leidas': request.user.perfil.notificacion_set.filter(leido=False).count()
            }
        except Exception:
            return {}
    return {}