from django.urls import path

from ..usuarios import viewsLogin

from ..reservas import viewsReservas

from ..pagos import viewsMercadoPago
from . import views, viewsAdmin, viewsAdminInmuebles, viewsAdminEstadisticas
from ..core import viewsBusquedas, viewsFiltros, viewsNotificaciones
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('', views.index, name='index'),
    # Login y Logout
    path('login/', viewsLogin.login_view, name='login'),
    path('logout/', viewsLogin.logout_view, name='logout'),
    path("loginAdmin/", viewsLogin.loginAdmin, name="loginAdmin"), # lo dejo para poder testear el login de admin solo, pero se puede eliminar
    path("loginAdmin/2fa/", viewsLogin.loginAdmin_2fa, name="loginAdmin_2fa"),
    path('loginAdmin/2fa/reenviar/', viewsLogin.loginAdmin_2fa_reenviar, name='loginAdmin_2fa_reenviar'),
    path('register/', viewsLogin.register, name='register'),

    # Busquedas
    path('buscar-inmuebles/', viewsBusquedas.buscar_inmuebles, name='buscar_inmuebles'),
    path('buscar-inmuebles/<int:id_inmueble>/', viewsBusquedas.detalle_inmueble, name='detalle_inmueble'),
    path('buscar-cocheras/', viewsBusquedas.buscar_cocheras, name='buscar_cocheras'),
    path('buscar-cocheras/<int:id_cochera>/', viewsBusquedas.detalle_cochera, name='detalle_cochera'),

    # Filtros de busqueda
    path('ajax/cargar-ciudades-filtro/', views.cargar_ciudades_filtro, name='ajax_cargar_ciudades_filtro'),
    
    # Reservas
    path('crear-reserva/<int:id_inmueble>/', viewsReservas.crear_reserva, name='crear_reserva'),
    path('crear-reserva-cochera/<int:id_cochera>/', viewsReservas.crear_reserva_cochera, name='crear_reserva_cochera'),
    
    # Reservas del usuario autenticado
    path('reservas/', viewsReservas.reservas_usuario, name='reservas_usuario'),
    path('reservas/<int:id_reserva>/detalle/', viewsReservas.ver_detalle_reserva, name='ver_detalle_reserva'),
    path('reservas/<int:id_reserva>/cancelar/', viewsReservas.cancelar_reserva, name='cancelar_reserva'),
    path('reservas/<int:id_reserva>/pagar/', viewsReservas.pagar_reserva, name='pagar_reserva'),
    path('reservas/<int:id_reserva>/completar-huespedes/', viewsReservas.completar_huespedes, name='completar_huespedes'),

    # URL para cargar ciudades cuando se selecciona una provincia
    path('ajax/cargar-ciudades/', views.cargar_ciudades, name='ajax_cargar_ciudades'),

    # Notificaciones
    path('notificaciones/marcar/<int:id_notificacion>/', viewsNotificaciones.marcar_notificacion, name='marcar_notificacion'),
    path('notificaciones/eliminar/<int:notificacion_id>/', viewsNotificaciones.eliminar_notificacion, name='eliminar_notificacion'),
    path('notificaciones/marcar-todas-leidas/', viewsNotificaciones.marcar_todas_leidas, name='marcar_todas_leidas'),

    # Cambiar contraseña
    path('cambiar-contrasena/', views.cambiar_contrasena, name='cambiar_contrasena'),

    # Reseñas y comentarios
    path('comentario/eliminar/<int:id_comentario>/', views.eliminar_comentario, name='eliminar_comentario'),
    path('resenias/eliminar/<int:id_resenia>/', views.eliminar_resenia, name='eliminar_resenia'),

    # Mercado Pago
    path('simulador-mercadopago/', views.simulador_mercadopago, name='simulador_mercadopago'),
    path('tarjetas/agregar/', views.agregar_tarjeta, name='agregar_tarjeta'),

    # Chequea reservas vencidas
    path('reservas/cancelar-vencidas/', viewsReservas.cancelar_reservas_vencidas, name='cancelar_reservas_vencidas'),

    # Mercado Pago
    path('mercadopago/crear-preferencia/', viewsMercadoPago.crear_preferencia_mp, name='crear_preferencia_mp'),
    path('probar-mp/', viewsMercadoPago.probar_mp, name='probar_mp'),
    path('mercadopago/webhook/', viewsMercadoPago.mercadopago_webhook, name='mercadopago_webhook'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


