from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.db.models import Count
from datetime import timedelta, date
# mercado pago
from collections import Counter


# Importaciones de formularios locales

# Importaciones de modelos locales
from ..models import (
    Reserva,
    Estado,
    Cochera,
    Cochera,
    RespuestaComentario,
    Perfil,
    User, 
    Perfil, 
    Resenia, 
    Comentario,
    Inmueble
)

# Importaciones de utilidades locales
from ..utils import (
    is_admin_or_empleado,
)

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_estadisticas_usuarios(request):
    total_usuarios = User.objects.count()
    total_clientes = Perfil.objects.filter(usuario__groups__name="cliente").count()
    total_empleados = Perfil.objects.filter(usuario__groups__name="empleado").count()
    total_reservas = Reserva.objects.count()
    total_resenias = Resenia.objects.count()
    total_comentarios = Comentario.objects.count()
    return render(request, 'admin/admin_estadisticas_usuarios.html', {
        'total_usuarios': total_usuarios,
        'total_clientes': total_clientes,
        'total_empleados': total_empleados,
        'total_reservas': total_reservas,
        'total_resenias': total_resenias,
        'total_comentarios': total_comentarios,
    })

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_estadisticas_empleados(request):
    empleados = Perfil.objects.filter(usuario__groups__name="empleado")
    empleados_stats = []
    for emp in empleados:
        cantidad_inmuebles = Inmueble.objects.filter(empleado=emp).count()
        cantidad_cocheras = Cochera.objects.filter(empleado=emp).count()
        respuestas = RespuestaComentario.objects.filter(usuario=emp).count()
        fecha_alta = emp.usuario.date_joined
        ultimo_acceso = emp.usuario.last_login
        empleados_stats.append({
            'nombre': emp.usuario.get_full_name(),
            'email': emp.usuario.email,
            'cantidad_inmuebles': cantidad_inmuebles,
            'cantidad_cocheras': cantidad_cocheras,
            'respuestas': respuestas,
            'fecha_alta': fecha_alta,
            'ultimo_acceso': ultimo_acceso,
        })
    return render(request, 'admin/admin_estadisticas_empleados.html', {
        'empleados_stats': empleados_stats
    })

@login_required
@user_passes_test(is_admin_or_empleado)
def admin_estadisticas_inmuebles(request):
    total_inmuebles = Inmueble.objects.count()

    # Estadísticas por estado
    estados_nombres = list(Estado.objects.values_list('nombre', flat=True))
    estados_inmuebles = Inmueble.objects.values('estado__nombre').annotate(cantidad=Count('id_inmueble'))
    estados_inmuebles_dict = {e['estado__nombre']: e['cantidad'] for e in estados_inmuebles}
    estados_labels = []
    estados_data = []
    for nombre in estados_nombres:
        total = estados_inmuebles_dict.get(nombre, 0)
        if total > 0:
            estados_labels.append(nombre)
            estados_data.append(total)

    # --- Reservas por día (últimos 30 días, incluyendo días sin reservas) ---
    reservas = Reserva.objects.filter(inmueble__isnull=False)
    reservas_por_dia = Counter(r.fecha_inicio for r in reservas if r.fecha_inicio)
    hoy = date.today()
    dias_ordenados = [hoy - timedelta(days=i) for i in reversed(range(30))]
    reservas_dias_labels = [d.strftime('%d/%m/%Y') for d in dias_ordenados]
    reservas_dias_data = [reservas_por_dia.get(d, 0) for d in dias_ordenados]

    # --- Reservas por mes (últimos 12 meses, incluyendo meses sin reservas) ---
    reservas_por_mes = Counter(r.fecha_inicio.strftime('%m/%Y') for r in reservas if r.fecha_inicio)
    meses_ordenados = []
    for i in range(12):
        mes = (hoy.replace(day=1) - timedelta(days=30*(11-i)))
        meses_ordenados.append(mes.strftime('%m/%Y'))
    reservas_meses_labels = meses_ordenados
    reservas_meses_data = [reservas_por_mes.get(m, 0) for m in reservas_meses_labels]

    return render(request, 'admin/admin_estadisticas_inmuebles.html', {
        'total_inmuebles': total_inmuebles,
        'estados_labels': estados_labels,
        'estados_data': estados_data,
        'reservas_dias_labels': reservas_dias_labels,
        'reservas_dias_data': reservas_dias_data,
        'reservas_meses_labels': reservas_meses_labels,
        'reservas_meses_data': reservas_meses_data,
    })
    
@login_required
@user_passes_test(is_admin_or_empleado)
def admin_estadisticas_cocheras(request):

    total_cocheras = Cochera.objects.count()

    # Estadísticas por estado
    estados_nombres = list(Estado.objects.values_list('nombre', flat=True))
    estados_cocheras = Cochera.objects.values('estado__nombre').annotate(cantidad=Count('id_cochera'))
    estados_cocheras_dict = {e['estado__nombre']: e['cantidad'] for e in estados_cocheras}
    estados_labels = []
    estados_data = []
    for nombre in estados_nombres:
        total = estados_cocheras_dict.get(nombre, 0)
        if total > 0:
            estados_labels.append(nombre)
            estados_data.append(total)

    # --- Reservas por día (últimos 30 días, incluyendo días sin reservas) ---
    reservas = Reserva.objects.filter(cochera__isnull=False)
    reservas_por_dia = Counter(r.fecha_inicio for r in reservas if r.fecha_inicio)
    hoy = date.today()
    dias_ordenados = [hoy - timedelta(days=i) for i in reversed(range(30))]
    reservas_dias_labels = [d.strftime('%d/%m/%Y') for d in dias_ordenados]
    reservas_dias_data = [reservas_por_dia.get(d, 0) for d in dias_ordenados]

    # --- Reservas por mes (últimos 12 meses, incluyendo meses sin reservas) ---
    reservas_por_mes = Counter(r.fecha_inicio.strftime('%m/%Y') for r in reservas if r.fecha_inicio)
    meses_ordenados = []
    for i in (range(12)):
        mes = (hoy.replace(day=1) - timedelta(days=30*i))
        meses_ordenados.append(mes.strftime('%m/%Y'))
    meses_ordenados = list((sorted(set(meses_ordenados), key=lambda x: (int(x.split('/')[1]), int(x.split('/')[0])))))
    reservas_meses_labels = meses_ordenados
    reservas_meses_data = [reservas_por_mes.get(m, 0) for m in reservas_meses_labels]

    return render(request, 'admin/admin_estadisticas_cocheras.html', {
        'total_cocheras': total_cocheras,
        'estados_labels': estados_labels,
        'estados_data': estados_data,
        'reservas_dias_labels': reservas_dias_labels,
        'reservas_dias_data': reservas_dias_data,
        'reservas_meses_labels': reservas_meses_labels,
        'reservas_meses_data': reservas_meses_data,
    })