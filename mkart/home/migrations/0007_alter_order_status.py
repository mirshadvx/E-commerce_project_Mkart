# Generated by Django 5.0.7 on 2024-09-06 03:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0006_alter_order_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('completed', 'Completed'), ('incomplete', 'InComplete')], default='incomplete', max_length=20),
        ),
    ]
