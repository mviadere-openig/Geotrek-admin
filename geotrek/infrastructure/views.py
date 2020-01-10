from django.conf import settings
from django.contrib.gis.db.models.functions import Transform

from mapentity.views import (MapEntityLayer, MapEntityList, MapEntityJsonList, MapEntityFormat,
                             MapEntityDetail, MapEntityDocument, MapEntityCreate, MapEntityUpdate, MapEntityDelete)

from geotrek.authent.decorators import same_structure_required
from geotrek.core.models import AltimetryMixin
from geotrek.core.views import CreateFromTopologyMixin

from .filters import InfrastructureFilterSet
from .forms import InfrastructureForm
from .models import Infrastructure
from .serializers import InfrastructureSerializer

from rest_framework import permissions as rest_permissions
from mapentity.views import MapEntityViewSet


class InfrastructureLayer(MapEntityLayer):
    queryset = Infrastructure.objects.existing()
    properties = ['name', 'published']


class InfrastructureList(MapEntityList):
    queryset = Infrastructure.objects.existing()
    filterform = InfrastructureFilterSet
    columns = ['id', 'name', 'type', 'condition', 'cities']


class InfrastructureJsonList(MapEntityJsonList, InfrastructureList):
    pass


class InfrastructureFormatList(MapEntityFormat, InfrastructureList):
    columns = [
        'id', 'name', 'type', 'condition', 'description',
        'implantation_year', 'published', 'publication_date', 'structure', 'date_insert',
        'date_update', 'cities', 'districts', 'areas',
    ] + AltimetryMixin.COLUMNS


class InfrastructureDetail(MapEntityDetail):
    queryset = Infrastructure.objects.existing()

    def get_context_data(self, *args, **kwargs):
        context = super(InfrastructureDetail, self).get_context_data(*args, **kwargs)
        context['can_edit'] = self.get_object().same_structure(self.request.user)
        return context


class InfrastructureDocument(MapEntityDocument):
    model = Infrastructure


class InfrastructureCreate(CreateFromTopologyMixin, MapEntityCreate):
    model = Infrastructure
    form_class = InfrastructureForm


class InfrastructureUpdate(MapEntityUpdate):
    queryset = Infrastructure.objects.existing()
    form_class = InfrastructureForm

    @same_structure_required('infrastructure:infrastructure_detail')
    def dispatch(self, *args, **kwargs):
        return super(InfrastructureUpdate, self).dispatch(*args, **kwargs)


class InfrastructureDelete(MapEntityDelete):
    model = Infrastructure

    @same_structure_required('infrastructure:infrastructure_detail')
    def dispatch(self, *args, **kwargs):
        return super(InfrastructureDelete, self).dispatch(*args, **kwargs)


class InfrastructureViewSet(MapEntityViewSet):
    model = Infrastructure
    serializer_class = InfrastructureSerializer
    permission_classes = [rest_permissions.DjangoModelPermissionsOrAnonReadOnly]

    def get_queryset(self):
        return Infrastructure.objects.existing().filter(published=True).annotate(transform=Transform("geom", settings.API_SRID))
