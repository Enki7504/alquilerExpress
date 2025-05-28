from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('buscar-inmuebles/', views.buscar_inmuebles, name='buscar_inmuebles'),
    path('buscar-inmuebles/<int:id_inmueble>/', views.detalle_inmueble, name='detalle_inmueble'),
    path("loginAdmin/2fa/", views.loginAdmin_2fa, name="loginAdmin_2fa"),
    # URLs de administración
    path('panel/', views.admin_panel, name='admin_panel'),
    path('panel/alta-empleados/', views.admin_alta_empleados, name='admin_alta_empleados'),
    path('panel/alta-inmuebles/', views.admin_alta_inmuebles, name='admin_alta_inmuebles'),
    path('panel/alta-cocheras/', views.admin_alta_cocheras, name='admin_alta_cocheras'),
    path('panel/estadisticas-usuarios/', views.admin_estadisticas_usuarios, name='admin_estadisticas_usuarios'),
    path('panel/estadisticas-empleados/', views.admin_estadisticas_empleados, name='admin_estadisticas_empleados'),
    path('panel/estadisticas-cocheras/', views.admin_estadisticas_cocheras, name='admin_estadisticas_cocheras'),
    path('panel/estadisticas-inmuebles/', views.admin_estadisticas_inmuebles, name='admin_estadisticas_inmuebles'),
    # registrar empleado y cliente
    path("registrar-empleado/", views.registrar_empleado, name="registrar_empleado"),
    path("registrar-cliente/", views.registrar_cliente, name="registrar_cliente"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

