from django.conf import settings
from django.conf.urls import url

from mapentity.registry import registry

from . import models
from geotrek.trekking.views import TrekSignageViewSet

app_name = 'signage'
urlpatterns = registry.register(models.Signage, menu=settings.SIGNAGE_MODEL_ENABLED)
urlpatterns += registry.register(models.Blade, menu=False)
urlpatterns += [
    url(r'^api/(?P<lang>\w\w)/treks/(?P<pk>\d+)/signages\.geojson$',
        TrekSignageViewSet.as_view({'get': 'list'}), name="trek_signage_geojson"),
]
