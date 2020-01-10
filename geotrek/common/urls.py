from django.urls import path
from mapentity.registry import MapEntityOptions

from .views import (JSSettings, admin_check_extents, DocumentPublic, import_view, import_update_json,
                    ThemeViewSet, MarkupPublic)


app_name = 'common'
urlpatterns = [
    path('api/settings.json', JSSettings.as_view(), name='settings_json'),
    path('tools/extents/', admin_check_extents, name='check_extents'),
    path('commands/import-update.json', import_update_json, name='import_update_json'),
    path('commands/import', import_view, name='import_dataset'),
    path('api/<str:lang>/themes.json', ThemeViewSet.as_view({'get': 'list'}), name="themes_json"),
]


class PublishableEntityOptions(MapEntityOptions):
    document_public_view = DocumentPublic
    markup_public_view = MarkupPublic

    def scan_views(self, *args, **kwargs):
        """ Adds the URLs of all views provided by ``PublishableMixin`` models.
        """
        views = super(PublishableEntityOptions, self).scan_views(*args, **kwargs)
        publishable_views = [
            path('api/<str:lang>/{name}s/<int:pk>/<slug:slug>.pdf'.format(name=self.modelname),
                 self.document_public_view.as_view(model=self.model),
                 name="%s_printable" % self.modelname),
            path('api/<str:lang>/{name}s/<int:pk>/<slug:slug>.html'.format(name=self.modelname),
                 self.markup_public_view.as_view(model=self.model)),
        ]
        return publishable_views + views
