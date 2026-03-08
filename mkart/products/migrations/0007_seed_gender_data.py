from django.db import migrations


def seed_genders(apps, schema_editor):
    Gender = apps.get_model('products', 'Gender')
    genders = [
        {'name': 'Men',   'slug': 'men'},
        {'name': 'Women', 'slug': 'women'},
        {'name': 'Kids',  'slug': 'kids'},
    ]
    for g in genders:
        Gender.objects.get_or_create(slug=g['slug'], defaults={'name': g['name']})


def reverse_seed_genders(apps, schema_editor):
    Gender = apps.get_model('products', 'Gender')
    Gender.objects.filter(slug__in=['men', 'women', 'kids']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0006_remove_category_logo'),
    ]

    operations = [
        migrations.RunPython(seed_genders, reverse_seed_genders),
    ]
