# Generated by Django 5.0.7 on 2024-09-06 00:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0005_orderitem_orderitem_coupon_discount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('shipped', 'Shipped'), ('delivered', 'Delivered'), ('completed', 'Completed'), ('returned', 'Returned')], default='pending', max_length=20),
        ),
    ]
