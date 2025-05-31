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
    # URLs de administración
    path('panel/', views.admin_panel, name='admin_panel'),
    path('panel/alta-empleados/', views.admin_alta_empleados, name='admin_alta_empleados'),
    path('panel/alta-inmuebles/', views.admin_alta_inmuebles, name='admin_alta_inmuebles'),
    path('panel/alta-cocheras/', views.admin_alta_cocheras, name='admin_alta_cocheras'),
    path('panel/estadisticas-usuarios/', views.admin_estadisticas_usuarios, name='admin_estadisticas_usuarios'),
    path('panel/estadisticas-empleados/', views.admin_estadisticas_empleados, name='admin_estadisticas_empleados'),
    path('panel/estadisticas-cocheras/', views.admin_estadisticas_cocheras, name='admin_estadisticas_cocheras'),
    path('panel/estadisticas-inmuebles/', views.admin_estadisticas_inmuebles, name='admin_estadisticas_inmuebles'),
    # Reservs
    path('crear-reserva/<int:id_inmueble>/', views.crear_reserva, name='crear_reserva'),
    path('crear-reserva-cochera/<int:id_cochera>/', views.crear_reserva_cochera, name='crear_reserva_cochera'),
    path('panel/reserva/<int:id_reserva>/cambiar-estado/', views.cambiar_estado_reserva, name='cambiar_estado_reserva'),
    # path('panel/inmuebles/', views.admin_editar_inmueble, name='admin_editar_inmueble'),
    # path('panel/inmuebles/editar-inmueble/<int:id_inmueble>/', views.admin_inmueble_editar, name='admin_inmueble_editar'),
    # path('panel/inmuebles/eliminar-inmueble/<int:id_inmueble>/', views.admin_inmueble_eliminar, name='admin_inmueble_eliminar'),
    # path('panel/inmuebles/historial-inmueble/<int:id_inmueble>/', views.admin_inmueble_historial, name='admin_inmueble_historial'),
    # path('panel/inmuebles/reservas-inmueble/<int:id_inmueble>/', views.admin_inmueble_reservas, name='admin_inmueble_reservas'),
    # path('panel/inmuebles/crear-reserva/<int:id_inmueble>/', views.crear_reserva, name='crear_reserva'),
    
    # Gestion de inmuebles
    path('panel/editar-inmueble/<int:id_inmueble>/', views.admin_inmueble_editar, name='admin_inmueble_editar'),
    path('panel/eliminar-inmueble/<int:id_inmueble>/', views.admin_inmueble_eliminar, name='admin_inmueble_eliminar'),
    path('panel/historial-inmueble/<int:id_inmueble>/', views.admin_inmueble_historial, name='admin_inmueble_historial'),
    path('panel/estado-inmueble/<int:id_inmueble>/', views.admin_inmueble_estado, name='admin_inmueble_estado'),

    # Gestion de cocheras
    path('panel/editar-cochera/<int:id_cochera>/', views.admin_cochera_editar, name='admin_cochera_editar'),
    path('panel/eliminar-cochera/<int:id_cochera>/', views.admin_cochera_eliminar, name='admin_cochera_eliminar'),
    path('panel/historial-cochera/<int:id_cochera>/', views.admin_cochera_historial, name='admin_cochera_historial'),
    path('panel/estado-cochera/<int:id_cochera>/', views.admin_cochera_estado, name='admin_cochera_estado'),
    path('panel/reserva-cochera/<int:id_reserva>/cambiar-estado/', views.cambiar_estado_reserva_cochera, name='cambiar_estado_reserva_cochera'),

    # registrar empleado y cliente
    path("registrar-empleado/", views.registrar_empleado, name="registrar_empleado"),
    path("registrar-cliente/", views.registrar_cliente, name="registrar_cliente"),

    # Notificaciones
    path('notificaciones/marcar/<int:id_notificacion>/', views.marcar_notificacion, name='marcar_notificacion'),
    path('notificaciones/eliminar/<int:notificacion_id>/', views.eliminar_notificacion, name='eliminar_notificacion'),
    path('notificaciones/marcar-todas-leidas/', views.marcar_todas_leidas, name='marcar_todas_leidas'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


