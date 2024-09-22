from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('social_django.urls', namespace='social')),
    path('',include('home.urls')),
    path('admin_panel/',include('Admin.urls')),
]  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 


if settings.DEBUG:
    import debug_toolbar
    urlpatterns += path('__debug__/',include(debug_toolbar.urls)),
    
from django.conf.urls import handler404, handler500
from home.views import custom_404, custom_500

handler404 = custom_404
handler500 = custom_500