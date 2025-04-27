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
