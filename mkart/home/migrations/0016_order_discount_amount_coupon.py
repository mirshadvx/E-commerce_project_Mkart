# Generated by Django 5.0.7 on 2024-08-31 06:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0015_alter_order_coupon'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='discount_amount_coupon',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
