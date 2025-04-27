# AlquilerExpress

Proyecto Django para el desarrollo de una página web de alquiler de propiedades.

## Requisitos

- Python 3.12 o superior
- Git
- (Opcional) Visual Studio Code u otro editor

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/Enki7504/alquilerExpress.git
cd alquilerExpress

# Crear el entorno virtual
python -m venv env

# Activar el entorno virtual
# (en Windows)
.\env\Scripts\activate
# (en Linux/Mac)
source env/bin/activate

# Instalar las dependencias
pip install django

# Aplicar migraciones
python manage.py migrate

# Levantar el servidor de desarrollo
python manage.py runserver
##Para acceder a la pagina http://127.0.0.1:8000 para darle stop CTRL + C en consola
```

## Paginas HTML
Ubicacion, por ejemplo (index.html)
```bash
alquilerExpress
└──web
    └──templates
      └──index.html
```
Para agregar más paginas ir a **web/views.py** y agregar la view
```python
def otra_pagina(request):
    return render(request, 'otra_pagina.html')
```

Luego crear el HTML en **web/templates/** (con el mismo nombre que pusieron en la view)

y agregar la nueva URL en **web/urls.py**

```python
urlpatterns = [
    path('', views.home, name='home'),
    path('otra/', views.otra_pagina, name='otra_pagina'),
]
```

y ya se puede referenciar en HTML (con el nombre que pusieron en el primer parametro de path() en el paso anterior)
```HTML
<a href="/otra/">Ir a otra página</a>
```

## Crear tablas en la Base de Datos

En **web/models.py** agregar la clase (que es la tabla) por ejemplo, agregar tabla Clientes y Propiedades haciendo FK desde Propiedades a Clientes
```python
class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20)

    def __str__(self):
        return self.nombre

class Propiedad(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.TextField()
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    cliente = models.ForeignKey(Cliente, on_delete=PROTECT)

    def __str__(self):
        return self.nombre
```

Para hacer que Django cree las tablas en la base de datos, ejecutar en terminal (hacerlo siempre)
```bash
python manage.py makemigrations
python manage.py migrate
```

Registrar los modelos en **web/admin.py**
```python
from .models import Cliente, Propiedad

admin.site.register(Cliente)
admin.site.register(Propiedad)
```

Agregar los modelos para que se vean desde el panel de admin en **web/admin.py** (opcional, pero recomendable asi vemos todo desde admin)

```python
from .models import Cliente, Propiedad

admin.site.register(Cliente)
admin.site.register(Propiedad)
```

## Agregar usuario admin

Crear superusuario para acceder al panel de admin (http://127.0.0.1:8000/admin/)

```bash
python manage.py createsuperuser
#Va a pedir
# Nombre de usuario
# Email (podés poner uno inventado si querés)
# Contraseña
# Repetir contraseña
``` 
