from django.conf import settings
from django.urls import path, include
from rest_framework import routers

from geotrek.api.mobile import views as api_mobile
from geotrek.api.mobile.views_sync import SyncMobileRedirect, sync_mobile_view, sync_mobile_update_json

router = routers.DefaultRouter()
if 'geotrek.flatpages' in settings.INSTALLED_APPS:
    router.register('flatpages', api_mobile.FlatPageViewSet, base_name='flatpage')
if 'geotrek.trekking' in settings.INSTALLED_APPS:
    router.register('treks', api_mobile.TrekViewSet, base_name='treks')
app_name = 'apimobile'
urlpatterns = [
    path('', api_mobile.SwaggerSchemaView.as_view(), name="schema"),
    path('', include(router.urls)),
    path('settings/', api_mobile.SettingsView.as_view(), name='settings'),
    path('commands/sync', SyncMobileRedirect.as_view(), name='sync_mobiles'),
    path('commands/syncview', sync_mobile_view, name='sync_mobiles_view'),
    path('commands/statesync/', sync_mobile_update_json, name='sync_mobiles_state'),
]
