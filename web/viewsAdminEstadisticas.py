import datetime
import random
import json
import secrets
import string
import mercadopago

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST
from django.db import IntegrityError, transaction
from django.db.models import Q
from datetime import timedelta
from django.template.loader import render_to_string
# mercado pago
from django.views.decorators.csrf import csrf_exempt


# Importaciones de formularios locales
from .forms import (
    RegistroUsuarioForm,
    InmuebleForm,
    CocheraForm,
    ComentarioForm,
    LoginForm,
    ClienteCreationForm,
    EmpleadoCreationForm,
    EmpleadoAdminCreationForm,
    ClienteAdminCreationForm,
    ChangePasswordForm,
    ReseniaForm,
    RespuestaComentarioForm,
    NotificarImprevistoForm,
)

# Importaciones de modelos locales
from .models import (
    Inmueble,
    InmuebleImagen,
    InmuebleEstado,
    CocheraEstado,
    CocheraImagen,
    Notificacion,
    Resenia,
    Comentario,
    LoginOTP,
    Reserva,
    ClienteInmueble,
    Estado,
    Cochera,
    Perfil,
    ReservaEstado,
    Ciudad,
    Provincia,
    Cochera,
    RespuestaComentario,
    Huesped,
    Tarjeta
)

# Importaciones de utilidades locales
from .utils import (
    email_link_token,
    crear_notificacion,
    cambiar_estado_inmueble,
    is_admin,
    is_admin_or_empleado,
)

# para enviar correos a empleados sobre reservas
from .utils import enviar_mail_a_empleados_sobre_reserva

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_estadisticas_usuarios(request):
    """
    Muestra estadísticas relacionadas con los usuarios.
    """
    return render(request, 'admin/admin_estadisticas_usuarios.html')

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_estadisticas_empleados(request):
    """
    Muestra estadísticas relacionadas con los empleados.
    """
    return render(request, 'admin/admin_estadisticas_empleados.html')

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_estadisticas_cocheras(request):
    """
    Muestra estadísticas relacionadas con las cocheras.
    """
    return render(request, 'admin/admin_estadisticas_cocheras.html')

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_estadisticas_inmuebles(request):
    """
    Muestra estadísticas relacionadas con los inmuebles.
    """
    return render(request, 'admin/admin_estadisticas_inmuebles.html')