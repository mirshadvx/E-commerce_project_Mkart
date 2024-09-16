from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static
from home.views import google_login_success

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',include('home.urls')),
    path('admin_panel/',include('Admin.urls')),
    path('accounts/', include('allauth.urls')),
    path('accounts/google/login/callback/', google_login_success, name='google_login_success'),
]  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 


if settings.DEBUG:
    import debug_toolbar
    urlpatterns += path('__debug__/',include(debug_toolbar.urls)),
