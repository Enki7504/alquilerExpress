from django.contrib.auth.models import AnonymousUser
from .models import Notificacion
from .utils import is_client


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

def is_client_context(request):
    return {'is_client': is_client(request.user)}