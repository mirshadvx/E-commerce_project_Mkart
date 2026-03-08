from django.db import migrations


def seed_colors(apps, schema_editor):
    Color = apps.get_model('products', 'Color')
    colors = [
        # Basics
        {'name': 'Black',       'hex_code': '#000000'},
        {'name': 'White',       'hex_code': '#FFFFFF'},
        {'name': 'Grey',        'hex_code': '#808080'},
        {'name': 'Silver',      'hex_code': '#C0C0C0'},
        # Warm tones
        {'name': 'Red',         'hex_code': '#FF0000'},
        {'name': 'Brown',       'hex_code': '#8B4513'},
        {'name': 'Orange',      'hex_code': '#FF8C00'},
        {'name': 'Yellow',      'hex_code': '#FFD700'},
        {'name': 'Cream',       'hex_code': '#FFFDD0'},
        # Cool tones
        {'name': 'Blue',        'hex_code': '#0000FF'},
        {'name': 'Navy Blue',   'hex_code': '#001F5B'},
        {'name': 'Sky Blue',    'hex_code': '#87CEEB'},
        {'name': 'Green',       'hex_code': '#008000'},
        {'name': 'Olive',       'hex_code': '#808000'},
        # Watch / premium tones
        {'name': 'Gold',        'hex_code': '#FFD700'},
        {'name': 'Rose Gold',   'hex_code': '#B76E79'},
        {'name': 'Gunmetal',    'hex_code': '#2C3539'},
        {'name': 'Midnight Blue','hex_code': '#191970'},
        # Fashion
        {'name': 'Pink',        'hex_code': '#FFC0CB'},
        {'name': 'Purple',      'hex_code': '#800080'},
        {'name': 'Maroon',      'hex_code': '#800000'},
        {'name': 'Beige',       'hex_code': '#F5F5DC'},
    ]
    for c in colors:
        Color.objects.get_or_create(hex_code=c['hex_code'], defaults={'name': c['name']})


def reverse_seed_colors(apps, schema_editor):
    Color = apps.get_model('products', 'Color')
    hex_codes = [
        '#000000', '#FFFFFF', '#808080', '#C0C0C0',
        '#FF0000', '#8B4513', '#FF8C00', '#FFD700', '#FFFDD0',
        '#0000FF', '#001F5B', '#87CEEB', '#008000', '#808000',
        '#FFD700', '#B76E79', '#2C3539', '#191970',
        '#FFC0CB', '#800080', '#800000', '#F5F5DC',
    ]
    Color.objects.filter(hex_code__in=hex_codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0007_seed_gender_data'),
    ]

    operations = [
        migrations.RunPython(seed_colors, reverse_seed_colors),
    ]
