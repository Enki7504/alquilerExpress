# Generated by Django 5.2 on 2025-07-10 14:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0033_alter_reserva_fecha_fin_alter_reserva_fecha_inicio'),
    ]

    operations = [
        migrations.AddField(
            model_name='reserva',
            name='patente',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='Patente del vehículo'),
        ),
    ]
