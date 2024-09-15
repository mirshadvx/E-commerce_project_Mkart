from django import template

register = template.Library()

@register.filter
def get_attribute(obj, attr):
    return getattr(obj, attr)

@register.filter
def get_image_attribute(obj, index):
    return getattr(obj, f'image_{index}', None)