# Generated by Django 5.0.7 on 2024-08-29 16:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0014_order_coupon'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='coupon',
            field=models.CharField(max_length=50, null=True),
        ),
    ]