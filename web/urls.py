from django.urls import path
from . import views
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView
from django.contrib.auth.views import LoginView
from .views import login_admin_view


urlpatterns = [
    path('', views.index, name='index'),
    path('login/',  LoginView.as_view(
        template_name='login.html',
        redirect_authenticated_user=True
        ),                            name='login'),
    path('logout/',  views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('inmuebles/', views.lista_inmuebles, name='lista_inmuebles'),
    path('buscar-inmuebles/', views.buscar_inmuebles, name='buscar_inmuebles'),
    path('buscar-inmuebles/<int:id_inmueble>/', views.detalle_inmueble, name='detalle_inmueble'),
    path('admin-login/', views.login_admin_view,  name='login_admin'),
    path('admin-verify/<uidb64>/<token>/', views.verify_admin_link, name='verify_admin_link'),

]
