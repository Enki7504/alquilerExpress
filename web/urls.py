from django.urls import path
from . import views
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView
from django.contrib.auth.views import LoginView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'),
    path('login/',  LoginView.as_view(
        template_name='login.html',
        redirect_authenticated_user=True
        ),                            name='login'),
    path('logout/',  views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('buscar-inmuebles/', views.buscar_inmuebles, name='buscar_inmuebles'),
    path('buscar-inmuebles/<int:id_inmueble>/', views.detalle_inmueble, name='detalle_inmueble'),
    # URLs de administración
    path('panel/', views.admin_panel, name='admin_panel'),
    path('panel/alta-empleados/', views.admin_alta_empleados, name='admin_alta_empleados'),
    path('panel/alta-inmuebles/', views.admin_alta_inmuebles, name='admin_alta_inmuebles'),
    path('panel/alta-cocheras/', views.admin_alta_cocheras, name='admin_alta_cocheras'),
    path('panel/estadisticas-usuarios/', views.admin_estadisticas_usuarios, name='admin_estadisticas_usuarios'),
    path('panel/estadisticas-empleados/', views.admin_estadisticas_empleados, name='admin_estadisticas_empleados'),
    path('panel/estadisticas-cocheras/', views.admin_estadisticas_cocheras, name='admin_estadisticas_cocheras'),
    path('panel/estadisticas-inmuebles/', views.admin_estadisticas_inmuebles, name='admin_estadisticas_inmuebles'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

