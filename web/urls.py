from django.urls import path
from .views import (
  views, 
  viewsAdminPropiedades, 
  viewsLogin, 
  viewsBusquedas,
  viewsDetalles,
  viewsAdmin, 
  viewsAdminEstadisticas,
  viewsNotificaciones, 
  viewsReservas, 
  viewsMercadoPago
)
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
    path('buscar-cocheras/', viewsBusquedas.buscar_cocheras, name='buscar_cocheras'),

    # Detalles, Comentarios y Reseñas
    path('buscar-inmuebles/<int:id_inmueble>/', viewsDetalles.detalle_inmueble, name='detalle_inmueble'),
    path('buscar-cocheras/<int:id_cochera>/', viewsDetalles.detalle_cochera, name='detalle_cochera'),
    path('comentario/eliminar/<int:id_comentario>/', viewsDetalles.eliminar_comentario, name='eliminar_comentario'),
    path('resenias/eliminar/<int:id_resenia>/', viewsDetalles.eliminar_resenia, name='eliminar_resenia'),

    # Filtros de busqueda
    path('ajax/cargar-ciudades-filtro/', views.cargar_ciudades_filtro, name='ajax_cargar_ciudades_filtro'),
    
    #########################################################################################################
    # URLs del Panel de Administración                                                                       
    #########################################################################################################

    # URL Base del Panel de Administración
    path('panel/', viewsAdmin.admin_panel, name='admin_panel'),

    # Gestión de usuarios
    path('panel/alta-empleados/', viewsAdmin.admin_alta_empleados, name='admin_alta_empleados'),
    path('panel/alta-cliente/', viewsAdmin.admin_alta_cliente, name='admin_alta_cliente'),
    path('panel/bloquear-cliente/', viewsAdmin.admin_bloquear_cliente, name='admin_bloquear_cliente'),
    
    # Gestión de inmuebles
    path('panel/inmuebles/', viewsAdminPropiedades.admin_inmuebles, name='admin_inmuebles'),
    path('panel/inmuebles/<int:id_inmueble>/cambiar-empleado/', viewsAdminPropiedades.cambiar_empleado_inmueble, name='cambiar_empleado_inmueble'),    
    path('panel/inmuebles/alta/', views.admin_inmuebles_alta, name='admin_inmuebles_alta'), # Mantener la alta separada o como parte del CRUD
    path('panel/inmuebles/editar/<int:id_inmueble>/', viewsAdminPropiedades.admin_inmuebles_editar, name='admin_inmuebles_editar'),
    path('panel/inmuebles/eliminar/<int:id_inmueble>/', viewsAdminPropiedades.admin_inmuebles_eliminar, name='admin_inmuebles_eliminar'),
    path('panel/inmuebles/reservas/<int:id_inmueble>/', viewsAdminPropiedades.admin_inmuebles_reservas, name='admin_inmuebles_reservas'),
    path('panel/inmuebles/historial/<int:id_inmueble>/', viewsAdminPropiedades.admin_inmuebles_historial, name='admin_inmuebles_historial'),
    path('eliminar-imagen-inmueble/<int:imagen_id>/', viewsAdminPropiedades.eliminar_imagen_inmueble, name='eliminar_imagen_inmueble'),
    path('panel/inmuebles/<int:id_inmueble>/cambiar-estado/', viewsAdminPropiedades.cambiar_estado_inmueble, name='cambiar_estado_inmueble'),

    # Gestión de cocheras
    path('panel/cocheras/', viewsAdminPropiedades.admin_cocheras, name='admin_cocheras'),
    path('panel/cocheras/<int:id_cochera>/cambiar-empleado/', viewsAdminPropiedades.cambiar_empleado_cochera, name='cambiar_empleado_cochera'),
    path('panel/cocheras/alta/', viewsAdminPropiedades.admin_cocheras_alta, name='admin_cocheras_alta'), # Mantener la alta separada o como parte del CRUD
    path('panel/cocheras/editar/<int:id_cochera>/', viewsAdminPropiedades.admin_cocheras_editar, name='admin_cocheras_editar'),
    path('panel/cocheras/eliminar/<int:id_cochera>/', viewsAdminPropiedades.admin_cocheras_eliminar, name='admin_cocheras_eliminar'),
    path('panel/cocheras/reservas/<int:id_cochera>/', viewsAdminPropiedades.admin_cocheras_reservas, name='admin_cocheras_reservas'),
    path('panel/cocheras/historial/<int:id_cochera>/', viewsAdminPropiedades.admin_cocheras_historial, name='admin_cocheras_historial'),
    path('eliminar-imagen-cochera/<int:id_imagen>/', viewsAdminPropiedades.eliminar_imagen_cochera, name='eliminar_imagen_cochera'),
    path('panel/cocheras/<int:id_cochera>/cambiar-estado/', viewsAdminPropiedades.cambiar_estado_cochera, name='cambiar_estado_cochera'),

    # Estadísiticas
    path('panel/estadisticas-empleados/', viewsAdminEstadisticas.admin_estadisticas_empleados, name='admin_estadisticas_empleados'),
    path('panel/estadisticas-usuarios/', viewsAdminEstadisticas.admin_estadisticas_usuarios, name='admin_estadisticas_usuarios'),
    path('panel/estadisticas-inmuebles/', viewsAdminEstadisticas.admin_estadisticas_inmuebles, name='admin_estadisticas_inmuebles'),
    path('panel/estadisticas-cocheras/', viewsAdminEstadisticas.admin_estadisticas_cocheras, name='admin_estadisticas_cocheras'),

    # Notificar Imprevisto
    path('panel/notificar-imprevisto/', viewsNotificaciones.admin_notificar_imprevisto, name='admin_notificar_imprevisto'),
    
    # Reservas
    path('crear-reserva/<int:id_inmueble>/', viewsReservas.crear_reserva_inmueble, name='crear_reserva_inmueble'),
    path('crear-reserva-cochera/<int:id_cochera>/', viewsReservas.crear_reserva_cochera, name='crear_reserva_cochera'),
    path('panel/reserva-inmueble/<int:id_reserva>/cambiar-estado/', viewsReservas.cambiar_estado_reserva, name='cambiar_estado_reserva_inmueble'),
    path('panel/reserva-cochera/<int:id_reserva>/cambiar-estado/', viewsReservas.cambiar_estado_reserva, name='cambiar_estado_reserva'),
    
    # Reservas del usuario autenticado
    path('reservas/', viewsReservas.reservas_usuario, name='reservas_usuario'),
    path('reservas/<int:id_reserva>/detalle/', viewsReservas.ver_detalle_reserva, name='ver_detalle_reserva'),
    path('reservas/<int:id_reserva>/cancelar/', viewsReservas.cancelar_reserva, name='cancelar_reserva'),
    path('reservas/<int:id_reserva>/pagar/', viewsReservas.pagar_reserva, name='pagar_reserva'),
    path('reservas/<int:id_reserva>/completar-huespedes/', viewsReservas.completar_huespedes, name='completar_huespedes'),
    # guardar_patente
    path('reservas/<int:id_reserva>/guardar-patente/', viewsReservas.guardar_patente, name='guardar_patente'),
    path('cochera/<int:id_cochera>/horarios/', viewsReservas.obtener_horarios_ocupados, name='obtener_horarios_ocupados'),

    # URL para cargar ciudades cuando se selecciona una provincia
    path('ajax/cargar-ciudades/', views.cargar_ciudades, name='ajax_cargar_ciudades'),

    # Notificaciones
    path('notificaciones/marcar/<int:id_notificacion>/', viewsNotificaciones.marcar_notificacion, name='marcar_notificacion'),
    path('notificaciones/eliminar/<int:notificacion_id>/', viewsNotificaciones.eliminar_notificacion, name='eliminar_notificacion'),
    path('notificaciones/marcar-todas-leidas/', viewsNotificaciones.marcar_todas_leidas, name='marcar_todas_leidas'),

    # Cambiar contraseña
    path('cambiar-contrasena/', views.cambiar_contrasena, name='cambiar_contrasena'),

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


