# Generated by Django 5.0.7 on 2024-09-05 17:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0004_remove_orderitem_discount_amount_coupon'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='orderItem_coupon_discount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]