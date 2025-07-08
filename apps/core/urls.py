from django.urls import path
from .views import viewsGlobal
from .views import viewsNotificaciones

urlpatterns = [
  
    path('', viewsGlobal.index, name='index'),
    path('notificaciones/marcar/<int:id_notificacion>/', viewsNotificaciones.marcar_notificacion, name='marcar_notificacion'),
    path('notificaciones/eliminar/<int:notificacion_id>/', viewsNotificaciones.eliminar_notificacion, name='eliminar_notificacion'),
    path('notificaciones/marcar-todas-leidas/', viewsNotificaciones.marcar_todas_leidas, name='marcar_todas_leidas'),
]