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
    path('register/', views.register, name='register'),
    # Busquedas
    path('buscar-inmuebles/', views.buscar_inmuebles, name='buscar_inmuebles'),
    path('buscar-inmuebles/<int:id_inmueble>/', views.detalle_inmueble, name='detalle_inmueble'),
    path('buscar-cocheras/', views.buscar_cocheras, name='buscar_cocheras'),
    path('buscar-cocheras/<int:id_cochera>/', views.detalle_cochera, name='detalle_cochera'),
    
    #########################################################################################################
    # URLs del Panel de Administración                                                                       
    #########################################################################################################
    path('panel/', views.admin_panel, name='admin_panel'),
    # Gestión de usuarios
    path('panel/alta-empleados/', views.admin_alta_empleados, name='admin_alta_empleados'),
    
    # Gestión de inmuebles
    path('panel/inmuebles/', views.admin_inmuebles, name='admin_inmuebles'),
    path('panel/inmuebles/alta/', views.admin_inmuebles_alta, name='admin_inmuebles_alta'), # Mantener la alta separada o como parte del CRUD
    path('panel/inmuebles/editar/<int:id_inmueble>/', views.admin_inmuebles_editar, name='admin_inmuebles_editar'),
    path('panel/inmuebles/eliminar/<int:id_inmueble>/', views.admin_inmuebles_eliminar, name='admin_inmuebles_eliminar'),
    path('panel/inmuebles/estado/<int:id_inmueble>/', views.admin_inmuebles_estado, name='admin_inmuebles_estado'),
    path('panel/inmuebles/historial/<int:id_inmueble>/', views.admin_inmuebles_historial, name='admin_inmuebles_historial'),
    path('eliminar-imagen-inmueble/<int:imagen_id>/', views.eliminar_imagen_inmueble, name='eliminar_imagen_inmueble'),

    # Gestión de cocheras
    path('panel/cocheras/', views.admin_cocheras, name='admin_cocheras'),
    path('panel/cocheras/alta/', views.admin_cocheras_alta, name='admin_cocheras_alta'), # Mantener la alta separada o como parte del CRUD
    path('panel/cocheras/editar/<int:id_cochera>/', views.admin_cocheras_editar, name='admin_cocheras_editar'),
    path('panel/cocheras/eliminar/<int:id_cochera>/', views.admin_cocheras_eliminar, name='admin_cocheras_eliminar'),
    path('panel/cocheras/estado/<int:id_cochera>/', views.admin_cocheras_estado, name='admin_cocheras_estado'),
    path('panel/cocheras/historial/<int:id_cochera>/', views.admin_cocheras_historial, name='admin_cocheras_historial'),
    
    # Estadísiticas
    path('panel/estadisticas-empleados/', views.admin_estadisticas_empleados, name='admin_estadisticas_empleados'),
    path('panel/estadisticas-usuarios/', views.admin_estadisticas_usuarios, name='admin_estadisticas_usuarios'),
    path('panel/estadisticas-inmuebles/', views.admin_estadisticas_inmuebles, name='admin_estadisticas_inmuebles'),
    path('panel/estadisticas-cocheras/', views.admin_estadisticas_cocheras, name='admin_estadisticas_cocheras'),
    
    # Reservas
    path('crear-reserva/<int:id_inmueble>/', views.crear_reserva, name='crear_reserva'),
    path('crear-reserva-cochera/<int:id_cochera>/', views.crear_reserva_cochera, name='crear_reserva_cochera'),
    path('panel/reserva/<int:id_reserva>/cambiar-estado/', views.cambiar_estado_reserva, name='cambiar_estado_reserva'),

    # URL para cargar ciudades cuando se selecciona una provincia
    path('ajax/cargar-ciudades/', views.cargar_ciudades, name='ajax_cargar_ciudades'),

    # Notificaciones
    path('notificaciones/marcar/<int:id_notificacion>/', views.marcar_notificacion, name='marcar_notificacion'),
    path('notificaciones/eliminar/<int:notificacion_id>/', views.eliminar_notificacion, name='eliminar_notificacion'),
    path('notificaciones/marcar-todas-leidas/', views.marcar_todas_leidas, name='marcar_todas_leidas'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


