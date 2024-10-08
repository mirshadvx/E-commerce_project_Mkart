from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def sub(value, arg):
    try:
        return Decimal(value) - Decimal(arg)
    except:
        return value
    
    
@register.filter
def subtract(first, second):
    return first - second