from django.contrib import admin

# Register your models here.
from .models import Cliente, Propiedad

admin.site.register(Cliente)
admin.site.register(Propiedad)
