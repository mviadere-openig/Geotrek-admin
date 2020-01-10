from django.conf import settings
from django.urls import include, path
from django.conf.urls import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin
from django.contrib.auth import views as auth_views

from mapentity.forms import AttachmentForm

from geotrek.common import views as common_views

from paperclip import views as paperclip_views


urlpatterns = [
    path('', common_views.home, name='home'),
    path('login/', auth_views.login, name='login'),
    path('logout/', auth_views.logout, {'next_page': settings.ROOT_URL + '/'}, name='logout',),

    path('', include('geotrek.common.urls', namespace='common')),
    path('', include('geotrek.altimetry.urls', namespace='altimetry')),

    path('', include(('mapentity.urls', 'mapentity'), namespace='mapentity')),
    path('paperclip/add-for/<str:app_label>/<str:model_name>/<int:pk>/',
         paperclip_views.add_attachment, kwargs={'attachment_form': AttachmentForm}, name="add_attachment"),
    path('paperclip/update/<int:attachment_pk>/', paperclip_views.update_attachment,
         kwargs={'attachment_form': AttachmentForm}, name="update_attachment"),
    path('paperclip/', include('paperclip.urls')),
    path('admin/doc/', include('django.contrib.admindocs.urls')),
    path('admin/', admin.site.urls),
]

if 'geotrek.core' in settings.INSTALLED_APPS:
    urlpatterns.append(path('', include('geotrek.core.urls', namespace='core')))
if 'geotrek.land' in settings.INSTALLED_APPS:
    urlpatterns.append(path('', include('geotrek.land.urls', namespace='land')))
if 'geotrek.zoning' in settings.INSTALLED_APPS:
    urlpatterns.append(path('', include('geotrek.zoning.urls', namespace='zoning')))
if 'geotrek.infrastructure' in settings.INSTALLED_APPS:
    urlpatterns.append(path('', include('geotrek.infrastructure.urls', namespace='infrastructure')))
if 'geotrek.signage' in settings.INSTALLED_APPS:
    urlpatterns.append(path('', include('geotrek.signage.urls', namespace='signage')))
if 'geotrek.maintenance' in settings.INSTALLED_APPS:
    urlpatterns.append(path('', include('geotrek.maintenance.urls', namespace='maintenance')))
if 'geotrek.trekking' in settings.INSTALLED_APPS:
    urlpatterns.append(path('', include('geotrek.trekking.urls', namespace='trekking')))
if 'geotrek.diving' in settings.INSTALLED_APPS:
    urlpatterns.append(path('', include('geotrek.diving.urls', namespace='diving')))
if 'geotrek.tourism' in settings.INSTALLED_APPS:
    urlpatterns.append(path('', include('geotrek.tourism.urls', namespace='tourism')))
if 'geotrek.flatpages' in settings.INSTALLED_APPS:
    urlpatterns.append(path('', include('geotrek.flatpages.urls', namespace='flatpages')))
if 'geotrek.feedback' in settings.INSTALLED_APPS:
    urlpatterns.append(path('', include('geotrek.feedback.urls', namespace='feedback')))
if 'geotrek.sensitivity' in settings.INSTALLED_APPS:
    urlpatterns.append(path('', include('geotrek.sensitivity.urls', namespace='sensitivity')))
if 'geotrek.api' in settings.INSTALLED_APPS:
    urlpatterns.append(path('api/v2/', include('geotrek.api.v2.urls', namespace='apiv2')))
    if 'geotrek.flatpages' in settings.INSTALLED_APPS and 'geotrek.trekking' in settings.INSTALLED_APPS and 'geotrek.tourism' in settings.INSTALLED_APPS:
        urlpatterns.append(path('api/mobile/', include('geotrek.api.mobile.urls', namespace='apimobile')))

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static.static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG or settings.TEST:
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
