from django.http import JsonResponse

from ..models import (
    Provincia,
    Ciudad,
)

def obtener_provincias_y_ciudades(tipo='inmueble', provincia_id=None):
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