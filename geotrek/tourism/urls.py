from django.conf import settings
from django.urls import path, re_path

from mapentity.registry import registry

from geotrek.common.urls import PublishableEntityOptions

from . import models
from . import views as tourism_views
from . import serializers as tourism_serializers


app_name = 'tourism'
urlpatterns = [
    re_path(r'^api/(?P<lang>\w\w)/information_desks.(?P<format>geojson)$', tourism_views.InformationDeskViewSet.as_view({'get': 'list'}), name="information_desk_geojson"),
    re_path(r'^api/(?P<lang>\w\w)/information_desks-(?P<type>\d+).(?P<format>geojson)$', tourism_views.InformationDeskViewSet.as_view({'get': 'list'})),
    re_path(r'^api/treks/(?P<pk>\d+)/information_desks.(?P<format>geojson)$', tourism_views.TrekInformationDeskViewSet.as_view({'get': 'list'}), name="trek_information_desk_geojson"),
    re_path(r'^api/(?P<lang>\w\w)/treks/(?P<pk>\d+)/touristicevents\.(?P<format>geojson)$', tourism_views.TrekTouristicEventViewSet.as_view({'get': 'list'}), name="trek_events_geojson"),
    re_path(r'^api/(?P<lang>\w\w)/treks/(?P<pk>\d+)/touristiccontents\.(?P<format>geojson)$', tourism_views.TrekTouristicContentViewSet.as_view({'get': 'list'}), name="trek_contents_geojson"),
    path('api/<str:lang>/touristiccategories.json', tourism_views.TouristicCategoryView.as_view(), name="touristic_categories_json"),
    path('api/<str:lang>/touristiccontents/<int:pk>/meta.html', tourism_views.TouristicContentMeta.as_view(), name="touristiccontent_meta"),
    path('api/<str:lang>/touristicevents/<int:pk>/meta.html', tourism_views.TouristicEventMeta.as_view(), name="touristicevent_meta"),
]


class TouristicContentEntityOptions(PublishableEntityOptions):
    document_public_view = tourism_views.TouristicContentDocumentPublic
    markup_public_view = tourism_views.TouristicContentMarkupPublic

    def get_serializer(self):
        return tourism_serializers.TouristicContentSerializer

    def get_queryset(self):
        return self.model.objects.existing()


if settings.TOURISM_ENABLED:
    urlpatterns += registry.register(models.TouristicContent, TouristicContentEntityOptions,
                                     menu=settings.TOURISTICCONTENT_MODEL_ENABLED)


class TouristicEventEntityOptions(PublishableEntityOptions):
    document_public_view = tourism_views.TouristicEventDocumentPublic
    markup_public_view = tourism_views.TouristicEventMarkupPublic

    def get_serializer(self):
        return tourism_serializers.TouristicEventSerializer

    def get_queryset(self):
        return self.model.objects.existing()


if settings.TOURISM_ENABLED:
    urlpatterns += registry.register(models.TouristicEvent, TouristicEventEntityOptions,
                                     menu=settings.TOURISTICEVENT_MODEL_ENABLED)
