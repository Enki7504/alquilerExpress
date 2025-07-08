from django.urls import path
from .views import viewsGeneral, viewsAdmin, viewsAdminInmuebles, viewsAdminEstadisticas, viewsAdminNotificaciones, viewsAdminReservas

urlpatterns = [
    # Página principal del panel
    path('', viewsAdmin.admin_panel, name='admin_panel'),

    # Gestión de usuarios
    path('alta-empleados/', viewsAdmin.admin_alta_empleados, name='admin_alta_empleados'),
    path('alta-cliente/', viewsAdmin.admin_alta_cliente, name='admin_alta_cliente'),

    # Gestión de inmuebles
    path('inmuebles/', viewsAdminInmuebles.admin_inmuebles, name='admin_inmuebles'),
    path('inmuebles/alta/', viewsAdminInmuebles.admin_inmuebles_alta, name='admin_inmuebles_alta'),
    path('inmuebles/editar/<int:id_inmueble>/', viewsAdminInmuebles.admin_inmuebles_editar, name='admin_inmuebles_editar'),
    path('inmuebles/eliminar/<int:id_inmueble>/', viewsAdminInmuebles.admin_inmuebles_eliminar, name='admin_inmuebles_eliminar'),
    path('inmuebles/reservas/<int:id_inmueble>/', viewsAdminInmuebles.admin_inmuebles_reservas, name='admin_inmuebles_reservas'),
    path('inmuebles/historial/<int:id_inmueble>/', viewsAdminInmuebles.admin_inmuebles_historial, name='admin_inmuebles_historial'),
    path('inmuebles/<int:id_inmueble>/cambiar-estado/', viewsAdminInmuebles.cambiar_estado_inmueble, name='cambiar_estado_inmueble'),
    path('inmuebles/<int:id_inmueble>/cambiar-empleado/', viewsAdminInmuebles.cambiar_empleado_inmueble, name='cambiar_empleado_inmueble'),

    # Gestión de cocheras
    path('cocheras/', viewsAdminInmuebles.admin_cocheras, name='admin_cocheras'),
    path('cocheras/alta/', viewsAdminInmuebles.admin_cocheras_alta, name='admin_cocheras_alta'),
    path('cocheras/editar/<int:id_cochera>/', viewsAdminInmuebles.admin_cocheras_editar, name='admin_cocheras_editar'),
    path('cocheras/eliminar/<int:id_cochera>/', viewsAdminInmuebles.admin_cocheras_eliminar, name='admin_cocheras_eliminar'),
    path('cocheras/reservas/<int:id_cochera>/', viewsAdminInmuebles.admin_cocheras_reservas, name='admin_cocheras_reservas'),
    path('cocheras/historial/<int:id_cochera>/', viewsAdminInmuebles.admin_cocheras_historial, name='admin_cocheras_historial'),
    path('cocheras/<int:id_cochera>/cambiar-estado/', viewsAdminInmuebles.cambiar_estado_cochera, name='cambiar_estado_cochera'),
    path('cocheras/<int:id_cochera>/cambiar-empleado/', viewsAdminInmuebles.cambiar_empleado_cochera, name='cambiar_empleado_cochera'),

    # Eliminar imágenes
    path('eliminar-imagen-inmueble/<int:imagen_id>/', viewsAdminInmuebles.eliminar_imagen_inmueble, name='eliminar_imagen_inmueble'),
    path('eliminar-imagen-cochera/<int:id_imagen>/', viewsAdminInmuebles.eliminar_imagen_cochera, name='eliminar_imagen_cochera'),

    # Estadísticas
    path('estadisticas-empleados/', viewsAdminEstadisticas.admin_estadisticas_empleados, name='admin_estadisticas_empleados'),
    path('estadisticas-usuarios/', viewsAdminEstadisticas.admin_estadisticas_usuarios, name='admin_estadisticas_usuarios'),
    path('estadisticas-inmuebles/', viewsAdminEstadisticas.admin_estadisticas_inmuebles, name='admin_estadisticas_inmuebles'),
    path('estadisticas-cocheras/', viewsAdminEstadisticas.admin_estadisticas_cocheras, name='admin_estadisticas_cocheras'),

    # Notificar Imprevisto
    path('notificar-imprevisto/', viewsAdminNotificaciones.admin_notificar_imprevisto, name='admin_notificar_imprevisto'),

    # Cambiar estado reserva (desde el panel)
    path('reserva-inmueble/<int:id_reserva>/cambiar-estado/', viewsAdminReservas.cambiar_estado_reserva, name='cambiar_estado_reserva_inmueble'),
    path('reserva-cochera/<int:id_reserva>/cambiar-estado/', viewsAdminReservas.cambiar_estado_reserva, name='cambiar_estado_reserva_cochera'),
]