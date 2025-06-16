from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('', views.index, name='index'),
    # Login y Logout
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path("loginAdmin/", views.loginAdmin, name="loginAdmin"), # lo dejo para poder testear el login de admin solo, pero se puede eliminar
    path("loginAdmin/2fa/", views.loginAdmin_2fa, name="loginAdmin_2fa"),
    path('loginAdmin/2fa/reenviar/', views.loginAdmin_2fa_reenviar, name='loginAdmin_2fa_reenviar'),
    path('register/', views.register, name='register'),
    # Busquedas
    path('buscar-inmuebles/', views.buscar_inmuebles, name='buscar_inmuebles'),
    path('buscar-inmuebles/<int:id_inmueble>/', views.detalle_inmueble, name='detalle_inmueble'),
    path('buscar-cocheras/', views.buscar_cocheras, name='buscar_cocheras'),
    path('buscar-cocheras/<int:id_cochera>/', views.detalle_cochera, name='detalle_cochera'),

    # Filtros de busqueda
    path('ajax/cargar-ciudades-filtro/', views.cargar_ciudades_filtro, name='ajax_cargar_ciudades_filtro'),
    
    #########################################################################################################
    # URLs del Panel de Administración                                                                       
    #########################################################################################################
    path('panel/', views.admin_panel, name='admin_panel'),
    # Gestión de usuarios
    path('panel/alta-empleados/', views.admin_alta_empleados, name='admin_alta_empleados'),
    path('panel/alta-cliente/', views.admin_alta_cliente, name='admin_alta_cliente'),
    
    # Gestión de inmuebles
    path('panel/inmuebles/', views.admin_inmuebles, name='admin_inmuebles'),
    path('panel/inmuebles/<int:id_inmueble>/cambiar-empleado/', views.cambiar_empleado_inmueble, name='cambiar_empleado_inmueble'),    path('panel/inmuebles/alta/', views.admin_inmuebles_alta, name='admin_inmuebles_alta'), # Mantener la alta separada o como parte del CRUD
    path('panel/inmuebles/editar/<int:id_inmueble>/', views.admin_inmuebles_editar, name='admin_inmuebles_editar'),
    path('panel/inmuebles/eliminar/<int:id_inmueble>/', views.admin_inmuebles_eliminar, name='admin_inmuebles_eliminar'),
    path('panel/inmuebles/reservas/<int:id_inmueble>/', views.admin_inmuebles_reservas, name='admin_inmuebles_reservas'),
    path('panel/inmuebles/historial/<int:id_inmueble>/', views.admin_inmuebles_historial, name='admin_inmuebles_historial'),
    path('eliminar-imagen-inmueble/<int:imagen_id>/', views.eliminar_imagen_inmueble, name='eliminar_imagen_inmueble'),

    # Gestión de cocheras
    path('panel/cocheras/', views.admin_cocheras, name='admin_cocheras'),
    path('panel/cocheras/<int:id_cochera>/cambiar-empleado/', views.cambiar_empleado_cochera, name='cambiar_empleado_cochera'),
    path('panel/cocheras/alta/', views.admin_cocheras_alta, name='admin_cocheras_alta'), # Mantener la alta separada o como parte del CRUD
    path('panel/cocheras/editar/<int:id_cochera>/', views.admin_cocheras_editar, name='admin_cocheras_editar'),
    path('panel/cocheras/eliminar/<int:id_cochera>/', views.admin_cocheras_eliminar, name='admin_cocheras_eliminar'),
    path('panel/cocheras/reservas/<int:id_cochera>/', views.admin_cocheras_reservas, name='admin_cocheras_reservas'),
    path('panel/cocheras/historial/<int:id_cochera>/', views.admin_cocheras_historial, name='admin_cocheras_historial'),
    path('eliminar-imagen-cochera/<int:id_imagen>/', views.eliminar_imagen_cochera, name='eliminar_imagen_cochera'),

    # Estadísiticas
    path('panel/estadisticas-empleados/', views.admin_estadisticas_empleados, name='admin_estadisticas_empleados'),
    path('panel/estadisticas-usuarios/', views.admin_estadisticas_usuarios, name='admin_estadisticas_usuarios'),
    path('panel/estadisticas-inmuebles/', views.admin_estadisticas_inmuebles, name='admin_estadisticas_inmuebles'),
    path('panel/estadisticas-cocheras/', views.admin_estadisticas_cocheras, name='admin_estadisticas_cocheras'),

    # Gestion de Notificaciones
    path('panel/notificar-imprevisto/', views.admin_notificar_imprevisto, name='admin_notificar_imprevisto'),
    
    # Reservas
    path('crear-reserva/<int:id_inmueble>/', views.crear_reserva, name='crear_reserva'),
    path('crear-reserva-cochera/<int:id_cochera>/', views.crear_reserva_cochera, name='crear_reserva_cochera'),
    path('panel/reserva-inmueble/<int:id_reserva>/cambiar-estado/', views.cambiar_estado_reserva, name='cambiar_estado_reserva_inmueble'),
    path('panel/reserva-cochera/<int:id_reserva>/cambiar-estado/', views.cambiar_estado_reserva, name='cambiar_estado_reserva'),
    
    # Reservas del usuario autenticado
    path('reservas/', views.reservas_usuario, name='reservas_usuario'),
    path('reservas/<int:id_reserva>/detalle/', views.ver_detalle_reserva, name='ver_detalle_reserva'),
    path('reservas/<int:id_reserva>/cancelar/', views.cancelar_reserva, name='cancelar_reserva'),
    path('reservas/<int:id_reserva>/pagar/', views.pagar_reserva, name='pagar_reserva'),

    # URL para cargar ciudades cuando se selecciona una provincia
    path('ajax/cargar-ciudades/', views.cargar_ciudades, name='ajax_cargar_ciudades'),

    # Notificaciones
    path('notificaciones/marcar/<int:id_notificacion>/', views.marcar_notificacion, name='marcar_notificacion'),
    path('notificaciones/eliminar/<int:notificacion_id>/', views.eliminar_notificacion, name='eliminar_notificacion'),
    path('notificaciones/marcar-todas-leidas/', views.marcar_todas_leidas, name='marcar_todas_leidas'),

    # Cambiar contraseña
    path('cambiar-contrasena/', views.cambiar_contrasena, name='cambiar_contrasena'),

    # Reseñas y comentarios
    path('comentario/eliminar/<int:id_comentario>/', views.eliminar_comentario, name='eliminar_comentario'),

    # Mercado Pago
    path('simulador-mercadopago/', views.simulador_mercadopago, name='simulador_mercadopago'),
    path('tarjetas/agregar/', views.agregar_tarjeta, name='agregar_tarjeta'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


