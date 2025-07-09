from django.shortcuts import render

from ..models import (
    Inmueble,
    Cochera,
    Cochera,
)

from ..utils import (
    obtener_provincias_y_ciudades
)

################################################################################################################
# --- Vistas de Busquedas ---
################################################################################################################

def buscar_inmuebles(request):
    query = request.GET.get('q', '').strip()
    precio_min = request.GET.get('precio_min')
    precio_max = request.GET.get('precio_max')
    direccion = request.GET.get('direccion')
    huespedes = request.GET.get('huespedes')
    ambientes = request.GET.get('ambientes')
    camas = request.GET.get('camas')
    banios = request.GET.get('banios')
    provincia_id = request.GET.get('provincia')
    ciudad_id = request.GET.get('ciudad')
    provincias, ciudades = obtener_provincias_y_ciudades('inmueble', provincia_id)

    # Solo mostrar inmuebles que NO estén en estado Eliminado ni Oculto
    inmuebles = Inmueble.objects.exclude(estado__nombre__in=['Oculto','Eliminado'])

    if query:
        inmuebles = inmuebles.filter(nombre__icontains=query)
    if provincia_id:
        inmuebles = inmuebles.filter(provincia_id=provincia_id)
    if ciudad_id:
        inmuebles = inmuebles.filter(ciudad_id=ciudad_id)
    if precio_min:
        try:
            inmuebles = inmuebles.filter(precio_por_dia__gte=float(precio_min))
        except ValueError:
            pass
    if precio_max:
        try:
            inmuebles = inmuebles.filter(precio_por_dia__lte=float(precio_max))
        except ValueError:
            pass
    if direccion:
        inmuebles = inmuebles.filter(direccion__icontains=direccion)
    if huespedes:
        inmuebles = inmuebles.filter(cantidad_huespedes__gte=huespedes)
    if ambientes:
        if ambientes.endswith('+'):
            inmuebles = inmuebles.filter(cantidad_ambientes__gte=int(ambientes[:-1]))
        else:
            inmuebles = inmuebles.filter(cantidad_ambientes=int(ambientes))
    if camas:
        if camas.endswith('+'):
            inmuebles = inmuebles.filter(cantidad_camas__gte=int(camas[:-1]))
        else:
            inmuebles = inmuebles.filter(cantidad_camas=int(camas))
    if banios:
        if banios.endswith('+'):
            inmuebles = inmuebles.filter(cantidad_banios__gte=int(banios[:-1]))
        else:
            inmuebles = inmuebles.filter(cantidad_banios=int(banios))

    # Add a variable to check if any provinces were found
    no_provinces_found = not provincias.exists()

    return render(request, 'busqueda/buscar_inmuebles.html', {
        'inmuebles': inmuebles,
        'query': query,
        'provincias': provincias,
        'ciudades': ciudades,
        'no_provinces_found': no_provinces_found, # Pass this to the template
    })

def buscar_cocheras(request):
    query = request.GET.get('q', '').strip()
    precio_min = request.GET.get('precio_min')
    precio_max = request.GET.get('precio_max')
    direccion = request.GET.get('direccion')
    cantidad_vehiculos = request.GET.get('cantidad_vehiculos')
    ancho = request.GET.get('ancho')
    largo = request.GET.get('largo')
    alto = request.GET.get('alto')
    con_techo = request.GET.get('con_techo')
    provincia_id = request.GET.get('provincia')
    ciudad_id = request.GET.get('ciudad')
    provincias, ciudades = obtener_provincias_y_ciudades('cochera', provincia_id)

    cocheras = Cochera.objects.exclude(estado__nombre__in=['Oculto','Eliminado'])

    if query:
        cocheras = cocheras.filter(nombre__icontains=query)
    if provincia_id:
        cocheras = cocheras.filter(provincia_id=provincia_id)
    if ciudad_id:
        cocheras = cocheras.filter(ciudad_id=ciudad_id)
    if precio_min:
        try:
            cocheras = cocheras.filter(precio_por_dia__gte=float(precio_min))
        except ValueError:
            pass
    if precio_max:
        try:
            cocheras = cocheras.filter(precio_por_dia__lte=float(precio_max))
        except ValueError:
            pass
    if direccion:
        cocheras = cocheras.filter(direccion__icontains=direccion)
    if cantidad_vehiculos:
        try:
            if cantidad_vehiculos.endswith('+'):
                cocheras = cocheras.filter(cantidad_vehiculos__gte=int(cantidad_vehiculos[:-1]))
            else:
                cocheras = cocheras.filter(cantidad_vehiculos=int(cantidad_vehiculos))
        except ValueError:
            pass
    if ancho:
        try:
            cocheras = cocheras.filter(ancho__gte=float(ancho))
        except ValueError:
            pass
    if largo:
        try:
            cocheras = cocheras.filter(largo__gte=float(largo))
        except ValueError:
            pass
    if alto:
        try:
            cocheras = cocheras.filter(alto__gte=float(alto))
        except ValueError:
            pass
    if con_techo:
        cocheras = cocheras.filter(con_techo=True)

    # Add a variable to check if any provinces were found
    no_provinces_found = not provincias.exists()

    return render(request, 'busqueda/buscar_cocheras.html', {
        'cocheras': cocheras,
        'query': query,
        'provincias': provincias,
        'ciudades': ciudades,
        'no_provinces_found': no_provinces_found, # Pass this to the template
    })
