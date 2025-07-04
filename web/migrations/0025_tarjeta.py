# Generated by Django 5.2 on 2025-06-12 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0024_reserva_aprobada_en'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tarjeta',
            fields=[
                ('id_tarjeta', models.AutoField(primary_key=True, serialize=False)),
                ('numero', models.CharField(max_length=16)),
                ('nombre', models.CharField(max_length=100)),
                ('vencimiento', models.CharField(max_length=5)),
                ('cvv', models.CharField(max_length=4)),
                ('saldo', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
            ],
        ),
    ]
