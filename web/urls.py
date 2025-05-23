from django.urls import path
from . import views
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView
from django.contrib.auth.views import LoginView

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
]

