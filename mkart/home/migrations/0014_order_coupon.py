# Generated by Django 5.0.7 on 2024-08-29 05:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0013_delete_coupon'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='coupon',
            field=models.CharField(max_length=50, null=True, unique=True),
        ),
    ]
