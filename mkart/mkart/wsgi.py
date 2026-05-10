"""
WSGI config for mkart project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mkart.settings')

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mkart.mkart.settings.prod')

application = get_wsgi_application()