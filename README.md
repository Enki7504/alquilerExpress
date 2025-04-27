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
```

## Paginas HTML
Por ejemplo (index.html)
```bash
alquilerExpress
└──web
    └──templates
      └──index.html
```
Para agregar más paginas ir a web/views.py y agregar la view
```python
def otra_pagina(request):
    return render(request, 'otra_pagina.html')
```

Luego crear el HTML en web/templates/

y agregar la nueva URL en web/urls.py

```python
urlpatterns = [
    path('', views.home, name='home'),
    path('otra/', views.otra_pagina, name='otra_pagina'),
]
```

y ya se puede referenciar en HTML
```HTML
<a href="/otra/">Ir a otra página</a>
```
