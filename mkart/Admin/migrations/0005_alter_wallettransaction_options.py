# Generated by Django 5.0.7 on 2024-09-15 04:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Admin', '0004_user_coupon_limit_admin_user__user_id_21b081_idx'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='wallettransaction',
            options={'ordering': ['-timestamp']},
        ),
    ]
