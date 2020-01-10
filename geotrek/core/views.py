import json
import logging
from collections import defaultdict

from django.contrib.auth.decorators import permission_required
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.shortcuts import redirect
from django.views.decorators.http import last_modified as cache_last_modified
from django.views.decorators.cache import cache_control
from django.views.generic import View, TemplateView
from django.utils.translation import ugettext as _
from django.core.cache import caches
from django.views.generic.detail import BaseDetailView
from django.http import HttpResponseRedirect

from mapentity.serializers import GPXSerializer
from mapentity.views import (MapEntityLayer, MapEntityList, MapEntityJsonList,
                             MapEntityDetail, MapEntityDocument, MapEntityCreate, MapEntityUpdate,
                             MapEntityDelete, MapEntityFormat, HttpJSONResponse, LastModifiedMixin,)


from geotrek.authent.decorators import same_structure_required
from geotrek.common.utils import classproperty
from geotrek.common.views import PublicOrReadPermMixin
from geotrek.core.models import AltimetryMixin

from .models import Path, Trail, Topology
from .forms import PathForm, TrailForm
from .filters import PathFilterSet, TrailFilterSet
from . import graph as graph_lib
from django.http.response import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Sum
from geotrek.api.v2.functions import Length
from django.db.models.fields import FloatField


logger = logging.getLogger(__name__)


class CreateFromTopologyMixin(object):
    def on_topology(self):
        pk = self.request.GET.get('topology')
        if pk:
            try:
                return Topology.objects.existing().get(pk=pk)
            except Topology.DoesNotExist:
                logger.warning("Intervention on unknown topology %s" % pk)
        return None

    def get_initial(self):
        initial = super(CreateFromTopologyMixin, self).get_initial()
        # Create intervention with an existing topology as initial data
        topology = self.on_topology()
        if topology:
            initial['topology'] = topology.serialize(with_pk=False)
        return initial


class PathLayer(MapEntityLayer):
    properties = ['name', 'draft']
    queryset = Path.objects.all()

    def get_queryset(self):
        qs = super(PathLayer, self).get_queryset()
        if self.request.GET.get('no_draft'):
            qs = qs.exclude(draft=True)
        return qs

    def view_cache_key(self):
        """Used by the ``view_cache_response_content`` decorator.
        """
        language = self.request.LANGUAGE_CODE
        latest_saved = Path.latest_updated()
        if latest_saved:
            geojson_lookup = '%s_path_%s%s_json_layer' % (
                language,
                latest_saved.strftime('%y%m%d%H%M%S%f'),
                '_nodraft' if self.request.GET.get('no_draft') == 'true' else ''
            )
        else:
            geojson_lookup = None

        return geojson_lookup


class PathList(MapEntityList):
    queryset = Path.objects
    filterform = PathFilterSet

    @classproperty
    def columns(cls):
        columns = ['id', 'checkbox', 'name', 'length', 'length_2d']
        return columns

    def get_template_names(self):
        return ("core/path_list.html",)


class PathJsonList(MapEntityJsonList, PathList):
    def get_context_data(self, **kwargs):
        context = super(PathJsonList, self).get_context_data(**kwargs)
        context["sumPath"] = round((self.object_list.aggregate(
            sumPath=Sum(Length('geom'), output_field=FloatField())
        ).get('sumPath') or 0) / 1000, 1)
        return context


class PathFormatList(MapEntityFormat, PathList):
    columns = [
        'id', 'structure', 'valid', 'visible', 'name', 'comments', 'departure', 'arrival',
        'comfort', 'source', 'stake', 'usages', 'networks',
        'date_insert', 'date_update',
        'cities', 'districts', 'areas', 'length_2d'
    ] + AltimetryMixin.COLUMNS


class PathDetail(MapEntityDetail):
    model = Path

    def get_context_data(self, *args, **kwargs):
        context = super(PathDetail, self).get_context_data(*args, **kwargs)
        context['can_edit'] = self.get_object().same_structure(self.request.user)
        return context


class PathGPXDetail(LastModifiedMixin, PublicOrReadPermMixin, BaseDetailView):
    queryset = Path.objects.all()

    def render_to_response(self, context):
        gpx_serializer = GPXSerializer()
        response = HttpResponse(content_type='application/gpx+xml')
        response['Content-Disposition'] = 'attachment; filename="%s.gpx"' % self.object
        gpx_serializer.serialize([self.object], stream=response, geom_field='geom')
        return response


class PathKMLDetail(LastModifiedMixin, PublicOrReadPermMixin, BaseDetailView):
    queryset = Path.objects.all()

    def render_to_response(self, context):
        response = HttpResponse(self.object.kml(),
                                content_type='application/vnd.google-earth.kml+xml')
        response['Content-Disposition'] = 'attachment; filename="%s.kml"' % self.object
        return response


class PathDocument(MapEntityDocument):
    model = Path

    def get_context_data(self, *args, **kwargs):
        language = self.request.LANGUAGE_CODE
        self.get_object().prepare_elevation_chart(language, self.request.build_absolute_uri('/'))
        return super(PathDocument, self).get_context_data(*args, **kwargs)


class PathCreate(MapEntityCreate):
    model = Path
    form_class = PathForm

    def dispatch(self, *args, **kwargs):
        if self.request.user.has_perm('core.add_path') or self.request.user.has_perm('core.add_draft_path'):
            return super(MapEntityCreate, self).dispatch(*args, **kwargs)
        return super(PathCreate, self).dispatch(*args, **kwargs)


class PathUpdate(MapEntityUpdate):
    model = Path
    form_class = PathForm

    @same_structure_required('core:path_detail')
    def dispatch(self, *args, **kwargs):
        path = self.get_object()
        if path.draft and not self.request.user.has_perm('core.change_draft_path'):
            messages.warning(self.request, _(
                'Access to the requested resource is restricted. You have been redirected.'))
            return redirect('core:path_detail', **kwargs)
        if not path.draft and not self.request.user.has_perm('core.change_path'):
            messages.warning(self.request, _(
                'Access to the requested resource is restricted. You have been redirected.'))
            return redirect('core:path_detail', **kwargs)
        if path.draft and self.request.user.has_perm('core.change_draft_path'):
            return super(MapEntityUpdate, self).dispatch(*args, **kwargs)
        return super(PathUpdate, self).dispatch(*args, **kwargs)


class MultiplePathDelete(TemplateView):
    template_name = "core/multiplepath_confirm_delete.html"
    model = Path
    success_url = "core:path_list"

    def dispatch(self, *args, **kwargs):
        self.paths_pk = self.kwargs['pk'].split(',')
        self.paths = []
        for pk in self.paths_pk:
            path = Path.objects.get(pk=pk)
            self.paths.append(path)
            if path.draft and not self.request.user.has_perm('core.delete_draft_path'):
                messages.warning(self.request, _(
                    'Access to the requested resource is restricted. You have been redirected.'))
                return redirect('core:path_list')
            if not path.draft and not self.request.user.has_perm('core.delete_path'):
                messages.warning(self.request, _(
                    'Access to the requested resource is restricted. You have been redirected.'))
                return redirect('core:path_list')
            if not path.same_structure(self.request.user):
                messages.warning(self.request, _('Access to the requested resource is restricted by structure. '
                                                 'You have been redirected.'))
                return redirect('core:path_list')
        return super(MultiplePathDelete, self).dispatch(*args, **kwargs)

    # Add support for browsers which only accept GET and POST for now.
    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        for path in self.paths:
            path.delete()
        return HttpResponseRedirect(reverse(self.success_url))

    def get_context_data(self, **kwargs):
        context = super(MultiplePathDelete, self).get_context_data(**kwargs)
        topologies_by_model = defaultdict(list)
        for path in self.paths:
            path.topologies_by_path(topologies_by_model)
        context['topologies_by_model'] = dict(topologies_by_model)
        return context


class PathDelete(MapEntityDelete):
    model = Path

    @same_structure_required('core:path_detail')
    def dispatch(self, *args, **kwargs):
        path = self.get_object()
        if path.draft and not self.request.user.has_perm('core.delete_draft_path'):
            messages.warning(self.request, _(
                'Access to the requested resource is restricted. You have been redirected.'))
            return redirect('core:path_detail', **kwargs)
        if not path.draft and not self.request.user.has_perm('core.delete_path'):
            messages.warning(self.request, _(
                'Access to the requested resource is restricted. You have been redirected.'))
            return redirect('core:path_detail', **kwargs)
        if path.draft and self.request.user.has_perm('core.delete_draft_path'):
            return super(MapEntityDelete, self).dispatch(*args, **kwargs)
        return super(PathDelete, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(PathDelete, self).get_context_data(**kwargs)
        topologies_by_model = defaultdict(list)
        self.object.topologies_by_path(topologies_by_model)
        context['topologies_by_model'] = dict(topologies_by_model)
        return context


@login_required
@cache_control(max_age=0, must_revalidate=True)
@cache_last_modified(lambda x: Path.latest_updated())
def get_graph_json(request):
    cache = caches['fat']
    key = 'path_graph_json'

    result = cache.get(key)
    latest = Path.latest_updated()

    if result and latest:
        cache_latest, json_graph = result
        # Not empty and still valid
        if cache_latest and cache_latest >= latest:
            return HttpJSONResponse(json_graph)

    # cache does not exist or is not up to date
    # rebuild the graph and cache the json
    graph = graph_lib.graph_edges_nodes_of_qs(Path.objects.exclude(draft=True))
    json_graph = json.dumps(graph)

    cache.set(key, (latest, json_graph))
    return HttpJSONResponse(json_graph)


class TrailLayer(MapEntityLayer):
    queryset = Trail.objects.existing()
    properties = ['name']


class TrailList(MapEntityList):
    queryset = Trail.objects.existing()
    filterform = TrailFilterSet
    columns = ['id', 'name', 'departure', 'arrival', 'length']


class TrailJsonList(MapEntityJsonList, TrailList):
    pass


class TrailFormatList(MapEntityFormat, TrailList):
    columns = [
        'id', 'structure', 'name', 'comments', 'departure', 'arrival',
        'date_insert', 'date_update',
        'cities', 'districts', 'areas',
    ] + AltimetryMixin.COLUMNS


class TrailDetail(MapEntityDetail):
    queryset = Trail.objects.existing()

    def get_context_data(self, *args, **kwargs):
        context = super(TrailDetail, self).get_context_data(*args, **kwargs)
        context['can_edit'] = self.get_object().same_structure(self.request.user)
        return context


class TrailGPXDetail(LastModifiedMixin, PublicOrReadPermMixin, BaseDetailView):
    queryset = Trail.objects.existing()

    def render_to_response(self, context):
        gpx_serializer = GPXSerializer()
        response = HttpResponse(content_type='application/gpx+xml')
        response['Content-Disposition'] = 'attachment; filename="%s.gpx"' % self.object
        gpx_serializer.serialize([self.object], stream=response, geom_field='geom')
        return response


class TrailKMLDetail(LastModifiedMixin, PublicOrReadPermMixin, BaseDetailView):
    queryset = Trail.objects.existing()

    def render_to_response(self, context):
        response = HttpResponse(self.object.kml(),
                                content_type='application/vnd.google-earth.kml+xml')
        response['Content-Disposition'] = 'attachment; filename="%s.kml"' % self.object
        return response


class TrailDocument(MapEntityDocument):
    queryset = Trail.objects.existing()


class TrailCreate(CreateFromTopologyMixin, MapEntityCreate):
    model = Trail
    form_class = TrailForm


class TrailUpdate(MapEntityUpdate):
    queryset = Trail.objects.existing()
    form_class = TrailForm

    @same_structure_required('core:trail_detail')
    def dispatch(self, *args, **kwargs):
        return super(TrailUpdate, self).dispatch(*args, **kwargs)


class TrailDelete(MapEntityDelete):
    queryset = Trail.objects.existing()

    @same_structure_required('core:trail_detail')
    def dispatch(self, *args, **kwargs):
        return super(TrailDelete, self).dispatch(*args, **kwargs)


@permission_required('core.change_path')
def merge_path(request):
    """
    Path merging view
    """
    response = {}

    if request.method == 'POST':
        try:
            ids_path_merge = request.POST.getlist('path[]')

            if len(ids_path_merge) != 2:
                raise Exception(_("You should select two paths"))

            path_a = Path.objects.get(pk=ids_path_merge[0])
            path_b = Path.objects.get(pk=ids_path_merge[1])

            if not path_a.same_structure(request.user) or not path_b.same_structure(request.user):
                raise Exception(_("You don't have the right to change these paths"))

            if path_a.draft != path_b.draft:
                raise Exception(_("You can't merge 1 draft path with 1 normal path"))

            result = path_a.merge_path(path_b)

            if result == 2:
                raise Exception(_("You can't merge 2 paths with a 3rd path in the intersection"))

            elif result == 0:
                raise Exception(_("No matching points to merge paths found"))

            else:
                response = {'success': _("Paths merged successfully")}
                messages.success(request, response['success'])

        except Exception as exc:
            response = {'error': '%s' % exc, }

    return JsonResponse(response)


class ParametersView(View):
    def get(request, *args, **kwargs):
        response = {
            'geotrek_admin_version': settings.VERSION,
        }
        return JsonResponse(response)
