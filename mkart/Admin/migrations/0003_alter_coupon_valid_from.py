# Generated by Django 5.0.7 on 2024-08-29 16:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Admin', '0002_alter_coupon_valid_from'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coupon',
            name='valid_from',
            field=models.DateTimeField(),
        ),
    ]
