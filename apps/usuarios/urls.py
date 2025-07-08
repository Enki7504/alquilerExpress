from django.urls import path
from ..usuarios import viewsLogin
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [

    # Index
    path('', viewsLogin.index, name='index'),
    
    # Login y Logout
    path('login/', viewsLogin.login_view, name='login'),
    path('logout/', viewsLogin.logout_view, name='logout'),
    path("loginAdmin/", viewsLogin.loginAdmin, name="loginAdmin"), # lo dejo para poder testear el login de admin solo, pero se puede eliminar
    path("loginAdmin/2fa/", viewsLogin.loginAdmin_2fa, name="loginAdmin_2fa"),
    path('loginAdmin/2fa/reenviar/', viewsLogin.loginAdmin_2fa_reenviar, name='loginAdmin_2fa_reenviar'),
    path('register/', viewsLogin.register, name='register'),

]


