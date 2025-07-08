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
from ..web.forms import (
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
from ..web.models import (
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
from ..web.utils import (
    email_link_token,
    crear_notificacion,
    cambiar_estado_inmueble
)

# para enviar correos a empleados sobre reservas
from ..web.utils import enviar_mail_a_empleados_sobre_reserva

def obtener_provincias_y_ciudades(tipo='inmueble', provincia_id=None):
    from ..web.models import Provincia, Ciudad
    if tipo == 'inmueble':
        provincias = Provincia.objects.filter(ciudades__inmueble__isnull=False).distinct()
        if provincia_id:
            ciudades = Ciudad.objects.filter(
                provincia_id=provincia_id,
                inmueble__isnull=False
            ).distinct()
        else:
            ciudades = Ciudad.objects.filter(
                inmueble__isnull=False
            ).distinct()
    elif tipo == 'cochera':
        provincias = Provincia.objects.filter(ciudades__cochera__isnull=False).distinct()
        if provincia_id:
            ciudades = Ciudad.objects.filter(
                provincia_id=provincia_id,
                cochera__isnull=False
            ).distinct()
        else:
            ciudades = Ciudad.objects.filter(
                cochera__isnull=False
            ).distinct()
    else:
        provincias = Provincia.objects.none()
        ciudades = Ciudad.objects.none()
    return provincias, ciudades

# para cargar las ciudades en el formulario de registro
def cargar_ciudades(request):
    provincia_id = request.GET.get('provincia')
    ciudades = Ciudad.objects.filter(provincia_id=provincia_id).order_by('nombre')
    ciudades_list = [{'id': ciudad.id, 'nombre': ciudad.nombre} for ciudad in ciudades]
    return JsonResponse({'ciudades': ciudades_list})

def cargar_ciudades_filtro(request):
    provincia_id = request.GET.get('provincia')
    tipo = request.GET.get('tipo', 'inmueble')
    if tipo == 'inmueble':
        ciudades = Ciudad.objects.filter(
            provincia_id=provincia_id,
            inmueble__isnull=False
        ).distinct()
    else:
        ciudades = Ciudad.objects.filter(
            provincia_id=provincia_id,
            cochera__isnull=False
        ).distinct()
    data = {'ciudades': [{'id': c.id, 'nombre': c.nombre} for c in ciudades]}
    return JsonResponse(data)