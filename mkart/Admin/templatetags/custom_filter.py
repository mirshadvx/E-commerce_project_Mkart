from django import template

register = template.Library()

@register.filter
def get_attribute(obj, attr):
    return getattr(obj, attr)

@register.filter
def get_image_attribute(obj, index):
    return getattr(obj, f'image_{index}', None)

@register.filter
def get_image_url(obj, index):
    image = getattr(obj, f'image_{index}', None)
    if not image:
        return ''
    return getattr(image, 'url', str(image))
