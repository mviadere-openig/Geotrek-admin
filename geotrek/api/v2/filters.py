from datetime import date, datetime


import coreschema

from coreapi.document import Field
from django.conf import settings
from django.db.models import Exists, OuterRef
from django.db.models.query_utils import Q
from django.utils.translation import gettext as _
from rest_framework.filters import BaseFilterBackend
from rest_framework_gis.filters import DistanceToPointFilter, InBBOXFilter

from geotrek.common.utils import intersecting
from geotrek.core.models import Topology
if 'geotrek.outdoor' in settings.INSTALLED_APPS:
    from geotrek.outdoor.models import Course, Site
from geotrek.tourism.models import TouristicContent, TouristicContentType, TouristicEvent, TouristicEventType
from geotrek.trekking.models import ServiceType, Trek
from geotrek.zoning.models import City, District


class GeotrekQueryParamsFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset

    def get_schema_fields(self, view):
        return (
            Field(
                name='language', required=False, location='query', schema=coreschema.String(
                    title=_("Language"),
                    description=_("Set language for translation. Can be all or a two-letters language code.")
                )
            ), Field(
                name='fields', required=False, location='query', schema=coreschema.String(
                    title=_("Fields"),
                    description=_("Limit required fields to increase performances. Example: id,url,geometry.")
                )
            ), Field(
                name='omit', required=False, location='query', schema=coreschema.String(
                    title=_("Omit"),
                    description=_("Omit specified fields to increase performance. Example: url,category.")
                )
            ),
        )


class GeotrekQueryParamsDimensionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset

    def get_schema_fields(self, view):
        return (
            Field(
                name='format', required=False, location='query', schema=coreschema.String(
                    title=_("Format"),
                    description=_("Set output format (json / geojson). Default: json. Example: geojson.")
                )
            ),
        )


class GeotrekInBBoxFilter(InBBOXFilter):
    """
    Override DRF gis InBBOXFilter with coreapi field descriptors
    """

    def get_filter_bbox(self, request):
        """ Transform bbox to internal SRID to get working """
        bbox = super().get_filter_bbox(request)
        if bbox:
            bbox.srid = 4326
            bbox.transform(settings.SRID)
        return bbox

    def get_schema_fields(self, view):
        return (
            Field(
                name=self.bbox_param, required=False, location='query', schema=coreschema.String(
                    title=_("In bbox"),
                    description=_('Filter by a bounding box formatted like W-lng,S-lat,E-lng,N-lat (WGS84).'
                                  'Example: 1.15,46.1,1.56,47.6.')
                )
            ),
        )


class GeotrekDistanceToPointFilter(DistanceToPointFilter):
    """
    Override DRF gis DistanceToPointFilter with coreapi field descriptors
    """

    def get_filter_point(self, request, **kwargs):
        point = super().get_filter_point(request, **kwargs)
        if point:
            point.srid = 4326
            point.transform(settings.SRID)
        return point

    def get_schema_fields(self, view):
        return (
            Field(
                name=self.dist_param, required=False, location='query', schema=coreschema.Integer(
                    title=_("Distance"),
                    description=_('Filter by maximum distance in meters between a point and elements.')
                )
            ), Field(
                name=self.point_param, required=False, location='query', schema=coreschema.String(
                    title=_("Point"),
                    description=_('Reference point to compute distance (WGS84). Example: lng,lat.'),
                )
            ),
        )


class GeotrekPublishedFilter(BaseFilterBackend):
    """
    Filter with published state in combination with language
    """

    def filter_queryset(self, request, queryset, view):
        qs = queryset
        language = request.GET.get('language', 'all')
        associated_published_fields = [f.name for f in qs.model._meta.get_fields() if f.name.startswith('published')]

        # if the model of the queryset published field is not translated
        if len(associated_published_fields) == 1:
            qs = qs.filter(published=True)
        elif len(associated_published_fields) > 1:
            # the published field of the queryset model is translated
            if language == 'all':
                # no language specified. Check for all.
                q = Q()
                for lang in settings.MODELTRANSLATION_LANGUAGES:
                    field_name = 'published_{}'.format(lang)
                    if field_name in associated_published_fields:
                        q |= Q(**{field_name: True})
                qs = qs.filter(q)
            else:
                # one language is specified
                field_name = 'published_{}'.format(language)
                qs = qs.filter(**{field_name: True})

        return qs


class GeotrekSensitiveAreaFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        qs = queryset
        practices = request.GET.get('practices')
        if practices:
            qs = qs.filter(species__practices__id__in=practices.split(','))
        structures = request.GET.get('structures')
        if structures:
            qs = qs.filter(structure__in=structures.split(','))
        period = request.GET.get('period')
        if not period:
            qs = qs.filter(**{'species__period{:02}'.format(date.today().month): True})
        elif period == 'any':
            q = Q()
            for m in range(1, 13):
                q |= Q(**{'species__period{:02}'.format(m): True})
            qs = qs.filter(q)
        elif period == 'ignore':
            pass
        else:
            q = Q()
            for m in [int(m) for m in period.split(',')]:
                q |= Q(**{'species__period{:02}'.format(m): True})
            qs = qs.filter(q)
        trek = request.GET.get('trek')
        if trek:
            contents_intersecting = intersecting(qs, Trek.objects.get(pk=trek))
            qs = contents_intersecting.order_by('id')
        return qs.distinct()

    def get_schema_fields(self, view):
        return (
            Field(
                name='period', required=False, location='query', schema=coreschema.String(
                    title=_("Period"),
                    description=_('Filter by period of occupancy. Month numbers (1-12), comma-separated.'
                                  ' any = occupied at any time in the year. ignore = occupied or not.'
                                  ' Example: 7,8 for july and august.')
                )
            ), Field(
                name='practices', required=False, location='query', schema=coreschema.String(
                    title=_("Practices"),
                    description=_('Filter by one or more practice id, comma-separated.')
                )
            ), Field(
                name='structures', required=False, location='query', schema=coreschema.String(
                    title=_("Structures"),
                    description=_('Filter by one or more structure id, comma-separated.')
                )
            ), Field(
                name='trek', required=False, location='query', schema=coreschema.Integer(
                    title=_("Trek"),
                    description=_('Filter by a trek id. It will show only the sensitive areas related to this trek.')
                )
            ),
        )


class GeotrekPOIFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        qs = queryset
        types = request.GET.get('types', None)
        if types is not None:
            qs = qs.filter(type__in=types.split(','))
        trek = request.GET.get('trek', None)
        if trek is not None:
            t = Trek.objects.get(pk=trek)
            qs = Topology.overlapping(t, qs)
            qs = qs.exclude(pk__in=t.pois_excluded.all())
        return qs

    def get_schema_fields(self, view):
        return (
            Field(
                name='types', required=False, location='query', schema=coreschema.Integer(
                    title=_("Types"),
                    description=_("Filter by one or more type id, comma-separated.")
                )
            ), Field(
                name='trek', required=False, location='query', schema=coreschema.Integer(
                    title=_("Trek"),
                    description=_("Filter by a trek id. It will show only the POIs related to this trek.")
                )
            ),
        )


class NearbyContentFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        ordering = ("name",)
        if queryset.model.__name__ == "SensitiveArea":
            ordering = ("-area", "pk")
        elif queryset.model.__name__ == "Service":
            ordering = ("id",)
        qs = queryset
        near_touristicevent = request.GET.get('near_touristicevent')
        if near_touristicevent:
            contents_intersecting = intersecting(qs, TouristicEvent.objects.get(pk=near_touristicevent))
            qs = contents_intersecting.order_by(*ordering)
        near_touristiccontent = request.GET.get('near_touristiccontent')
        if near_touristiccontent:
            contents_intersecting = intersecting(qs, TouristicContent.objects.get(pk=near_touristiccontent))
            qs = contents_intersecting.order_by(*ordering)
        near_trek = request.GET.get('near_trek')
        if near_trek:
            contents_intersecting = intersecting(qs, Trek.objects.get(pk=near_trek))
            qs = contents_intersecting.order_by(*ordering)
        near_outdoorsite = request.GET.get('near_outdoorsite')
        if 'geotrek.outdoor' in settings.INSTALLED_APPS:
            if near_outdoorsite:
                contents_intersecting = intersecting(qs, Site.objects.get(pk=near_outdoorsite))
                qs = contents_intersecting.order_by(*ordering)
            near_outdoorcourse = request.GET.get('near_outdoorcourse')
            if near_outdoorcourse:
                contents_intersecting = intersecting(qs, Course.objects.get(pk=near_outdoorcourse))
                qs = contents_intersecting.order_by(*ordering)
        return qs

    def get_schema_fields(self, view):
        fields = (
            Field(
                name='near_trek', required=False, location='query',
                schema=coreschema.Integer(
                    title=_("Near trek"),
                    description=_("Filter by a trek id. It will only show the contents related to this trek.")
                )
            ),
            Field(
                name='near_touristiccontent', required=False, location='query',
                schema=coreschema.Integer(
                    title=_("Near touristic content"),
                    description=_("Filter by a touristic content id. It will only show the contents related to this touristic content.")
                )
            ),
            Field(
                name='near_touristicevent', required=False, location='query',
                schema=coreschema.Integer(
                    title=_("Near touristic event"),
                    description=_("Filter by a touristic event id. It will only show the contents related to this touristic event.")
                )
            ),
        )
        if 'geotrek.outdoor' in settings.INSTALLED_APPS:
            fields = fields + (
                Field(
                    name='near_outdoorsite', required=False, location='query',
                    schema=coreschema.Integer(
                        title=_("Near outdoor site"),
                        description=_("Filter by an outdoor course id. It will only show the contents related to this outdoor site.")
                    )
                ),
                Field(
                    name='near_outdoorcourse', required=False, location='query',
                    schema=coreschema.Integer(
                        title=_("Near outdoor course"),
                        description=_("Filter by a touristic event id. It will only show the contents related to this outdoor course.")
                    )
                )
            )
        return fields


class GeotrekTouristicModelFilter(NearbyContentFilter):
    def _filter_queryset(self, request, queryset, view):
        qs = queryset
        cities = request.GET.get('cities')
        if cities:
            qs = qs.filter(Exists(City.objects.filter(code__in=cities.split(","), geom__intersects=OuterRef('geom'))))
        districts = request.GET.get('districts')
        if districts:
            qs = qs.filter(Exists(District.objects.filter(pk__in=districts.split(","), geom__intersects=OuterRef('geom'))))
        structures = request.GET.get('structures')
        if structures:
            qs = qs.filter(structure__in=structures.split(','))
        themes = request.GET.get('themes')
        if themes:
            qs = qs.filter(themes__in=themes.split(','))
        portals = request.GET.get('portals')
        if portals:
            qs = qs.filter(portal__in=portals.split(','))
        q = request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(description__icontains=q) | Q(description_teaser__icontains=q)
            )
        return qs

    def _get_schema_fields(self, view):
        return (
            Field(
                name='cities', required=False, location='query', schema=coreschema.String(
                    title=_("Cities"),
                    description=_('Filter by one or more city id, comma-separated.')
                )
            ), Field(
                name='districts', required=False, location='query', schema=coreschema.String(
                    title=_("Districts"),
                    description=_('Filter by one or more district id, comma-separated.')
                )
            ), Field(
                name='structures', required=False, location='query', schema=coreschema.Integer(
                    title=_("Structures"),
                    description=_('Filter by one or more structure id, comma-separated.')
                )
            ), Field(
                name='themes', required=False, location='query', schema=coreschema.String(
                    title=_("Themes"),
                    description=_('Filter by one or more themes id, comma-separated.')
                )
            ), Field(
                name='portals', required=False, location='query', schema=coreschema.String(
                    title=_("Portals"),
                    description=_('Filter by one or more portal id, comma-separated.')
                )
            ), Field(
                name='q', required=False, location='query', schema=coreschema.String(
                    title=_("Query string"),
                    description=_('Filter by some case-insensitive text contained in name, description teaser or description.')
                )
            )
        )


class GeotrekTouristicContentFilter(GeotrekTouristicModelFilter):
    def filter_queryset(self, request, queryset, view):
        qs = queryset
        categories = request.GET.get('categories')
        if categories:
            qs = qs.filter(category__in=categories.split(','))
        types = request.GET.get('types')
        if types:
            types_id = types.split(',')
            if TouristicContentType.objects.filter(id__in=types_id, in_list=1).exists():
                qs = qs.filter(Q(type1__in=types_id))
            if TouristicContentType.objects.filter(id__in=types_id, in_list=2).exists():
                qs = qs.filter(Q(type2__in=types_id))
        return self._filter_queryset(request, qs, view)

    def get_schema_fields(self, view):
        return self._get_schema_fields(view) + (
            Field(
                name='categories', required=False, location='query', schema=coreschema.Integer(
                    title=_("Categories"),
                    description=_("Filter by one or more category id, comma-separated.")
                )
            ), Field(
                name='types', required=False, location='query', schema=coreschema.Integer(
                    title=_("Types"),
                    description=_("Filter by one or more types id, comma-separated. Logical OR for types in the same list, AND for types in different lists.")
                )
            )
        )


class GeotrekTouristicEventFilter(GeotrekTouristicModelFilter):
    def filter_queryset(self, request, queryset, view):
        qs = queryset
        # Don't filter on detail view
        if 'pk' not in view.kwargs:
            types = request.GET.get('types')
            if types:
                types_id = types.split(',')
                if TouristicEventType.objects.filter(id__in=types_id).exists():
                    qs = qs.filter(Q(type__in=types_id))
            dates_before = request.GET.get('dates_before')
            if dates_before:
                dates_before = datetime.strptime(dates_before, "%Y-%m-%d").date()
                qs = qs.filter(Q(begin_date__lte=dates_before))
            dates_after = request.GET.get('dates_after')
            if dates_after:
                dates_after = datetime.strptime(dates_after, "%Y-%m-%d").date()
            else:
                # Filter out past events by default
                dates_after = date.today()
            qs = qs.filter(Q(end_date__gte=dates_after))
        return self._filter_queryset(request, qs, view)

    def get_schema_fields(self, view):
        return (
            *self._get_schema_fields(view),
            Field(
                name="types",
                required=False,
                location="query",
                schema=coreschema.Integer(
                    title=_("Types"),
                    description=_(
                        "Filter by one or more types id, comma-separated. Logical OR for types in the same list, AND for types in different lists."
                    ),
                ),
            ), Field(
                name='dates_before',
                required=False,
                location='query',
                schema=coreschema.String(
                    title=_("Dates before"),
                    description=_("Filter events happening before or during date, format YYYY-MM-DD")
                )
            ), Field(
                name='dates_after',
                required=False,
                location='query',
                schema=coreschema.String(
                    title=_("Dates after"),
                    description=_("Filter events happening after or during date, format YYYY-MM-DD")
                )
            )
        )


class GeotrekServiceFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        qs = queryset
        types = request.GET.get('types')
        if types:
            types_id = types.split(',')
            if ServiceType.objects.filter(id__in=types_id).exists():
                qs = qs.filter(Q(type__in=types_id))
        return qs

    def get_schema_fields(self, view):
        return (
            Field(
                name='types', required=False, location='query', schema=coreschema.Integer(
                    title=_("Types"),
                    description=_("Filter by one or more types id, comma-separated. Logical OR for types in the same list, AND for types in different lists.")
                )
            ),
        )


class UpdateOrCreateDateFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        qs = queryset
        updated_before = request.GET.get('updated_before')
        if updated_before:
            updated_before = datetime.strptime(updated_before, "%Y-%m-%d").date()
            qs = qs.filter(Q(date_update__lte=updated_before))
        updated_after = request.GET.get('updated_after')
        if updated_after:
            updated_after = datetime.strptime(updated_after, "%Y-%m-%d").date()
            qs = qs.filter(Q(date_update__gte=updated_after))
        created_before = request.GET.get('created_before')
        if created_before:
            created_before = datetime.strptime(created_before, "%Y-%m-%d").date()
            qs = qs.filter(Q(date_insert__lte=created_before))
        created_after = request.GET.get('created_after')
        if created_after:
            created_after = datetime.strptime(created_after, "%Y-%m-%d").date()
            qs = qs.filter(Q(date_insert__gte=created_after))
        return qs

    def get_schema_fields(self, view):
        return (
            Field(
                name='updated_after',
                required=False,
                location='query',
                schema=coreschema.String(
                    title=_("Update date after"),
                    description=_("Filter objects updated after or during date, format YYYY-MM-DD")
                )
            ), Field(
                name='updated_before',
                required=False,
                location='query',
                schema=coreschema.String(
                    title=_("Update date before"),
                    description=_("Filter objects updated before or during date, format YYYY-MM-DD")
                )
            ),
            Field(
                name='created_after',
                required=False,
                location='query',
                schema=coreschema.String(
                    title=_("Create date after"),
                    description=_("Filter objects created after or during date, format YYYY-MM-DD")
                )
            ), Field(
                name='created_before',
                required=False,
                location='query',
                schema=coreschema.String(
                    title=_("Create date before"),
                    description=_("Filter objects created before or during date, format YYYY-MM-DD")
                )
            )
        )


class GeotrekTrekQueryParamsFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        qs = queryset
        duration_min = request.GET.get('duration_min')
        if duration_min:
            qs = qs.filter(duration__gte=duration_min)
        duration_max = request.GET.get('duration_max')
        if duration_max:
            qs = qs.filter(duration__lte=duration_max)
        length_min = request.GET.get('length_min')
        if length_min:
            qs = qs.filter(length__gte=length_min)
        length_max = request.GET.get('length_max')
        if length_max:
            qs = qs.filter(length__lte=length_max)
        difficulty_min = request.GET.get('difficulty_min')
        if difficulty_min:
            qs = qs.filter(difficulty__id__gte=difficulty_min)
        difficulty_max = request.GET.get('difficulty_max')
        if difficulty_max:
            qs = qs.filter(difficulty__id__lte=difficulty_max)
        ascent_min = request.GET.get('ascent_min')
        if ascent_min:
            qs = qs.filter(ascent__gte=ascent_min)
        ascent_max = request.GET.get('ascent_max')
        if ascent_max:
            qs = qs.filter(ascent__lte=ascent_max)
        cities = request.GET.get('cities')
        if cities:
            qs = qs.filter(Exists(City.objects.filter(code__in=cities.split(","), geom__intersects=OuterRef('geom'))))
        districts = request.GET.get('districts')
        if districts:
            qs = qs.filter(Exists(District.objects.filter(pk__in=districts.split(","), geom__intersects=OuterRef('geom'))))
        structures = request.GET.get('structures')
        if structures:
            qs = qs.filter(structure__in=structures.split(','))
        accessibilities = request.GET.get('accessibilities')
        if accessibilities:
            qs = qs.filter(accessibilities__in=accessibilities.split(','))
        themes = request.GET.get('themes')
        if themes:
            qs = qs.filter(themes__in=themes.split(','))
        portals = request.GET.get('portals')
        if portals:
            qs = qs.filter(portal__in=portals.split(','))
        route = request.GET.get('routes')
        if route:
            qs = qs.filter(route__in=route.split(','))
        labels = request.GET.get('labels')
        if labels:
            qs = qs.filter(portal__in=labels.split(','))
        practices = request.GET.get('practices')
        if practices:
            qs = qs.filter(practice__in=practices.split(','))
        q = request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(description__icontains=q)
                | Q(description_teaser__icontains=q) | Q(ambiance__icontains=q)
            )
        return qs

    def get_schema_fields(self, view):
        return (
            Field(
                name='duration_min', required=False, location='query', schema=coreschema.Number(
                    title=_("Duration min"),
                    description=_('Filter by minimum duration (hours).')
                )
            ), Field(
                name='duration_max', required=False, location='query', schema=coreschema.Number(
                    title=_("Duration max"),
                    description=_('Filter by maximum duration (hours).')
                )
            ), Field(
                name='length_min', required=False, location='query', schema=coreschema.Integer(
                    title=_("Length min"),
                    description=_('Filter by minimum length (meters).')
                )
            ), Field(
                name='length_max', required=False, location='query', schema=coreschema.Integer(
                    title=_("Length max"),
                    description=_('Filter by maximum length (meters).')
                )
            ), Field(
                name='difficulty_min', required=False, location='query', schema=coreschema.Integer(
                    title=_("Difficulty min"),
                    description=_('Filter by minimum difficulty level (id).')
                )
            ), Field(
                name='difficulty_max', required=False, location='query', schema=coreschema.Integer(
                    title=_("Difficulty max"),
                    description=_('Filter by maximum difficulty level (id).')
                )
            ), Field(
                name='ascent_min', required=False, location='query', schema=coreschema.Integer(
                    title=_("Ascent min"),
                    description=_('Filter by minimum ascent (meters).')
                )
            ), Field(
                name='ascent_max', required=False, location='query', schema=coreschema.Integer(
                    title=_("Ascent max"),
                    description=_('Filter by maximum ascent (meters).')
                )
            ), Field(
                name='cities', required=False, location='query', schema=coreschema.String(
                    title=_("Cities"),
                    description=_('Filter by one or more city id, comma-separated.')
                )
            ), Field(
                name='districts', required=False, location='query', schema=coreschema.String(
                    title=_("Districts"),
                    description=_('Filter by one or more district id, comma-separated.')
                )
            ), Field(
                name='structures', required=False, location='query', schema=coreschema.Integer(
                    title=_("Structures"),
                    description=_('Filter by one or more structure id, comma-separated.')
                )
            ), Field(
                name='accessibilities', required=False, location='query', schema=coreschema.String(
                    title=_("Accessibilities"),
                    description=_('Filter by one or more accessibility id, comma-separated.')
                )
            ), Field(
                name='themes', required=False, location='query', schema=coreschema.String(
                    title=_("Themes"),
                    description=_('Filter by one or more theme id, comma-separated.')
                )
            ), Field(
                name='portals', required=False, location='query', schema=coreschema.String(
                    title=_("Portals"),
                    description=_('Filter by one or more portal id, comma-separateds.')
                )
            ), Field(
                name='routes', required=False, location='query', schema=coreschema.Integer(
                    title=_("Routes"),
                    description=_('Filter by one or more route id, comma-separated.')
                )
            ), Field(
                name='labels', required=False, location='query', schema=coreschema.String(
                    title=_("Labels"),
                    description=_('Filter by one or more label id, comma-separated.')
                )
            ), Field(
                name='practices', required=False, location='query', schema=coreschema.String(
                    title=_("Practices"),
                    description=_('Filter by one or more practice id, comma-separated.')
                )
            ), Field(
                name='q', required=False, location='query', schema=coreschema.String(
                    title=_("Query string"),
                    description=_('Filter by some case-insensitive text contained in name, description, description teaser or ambiance.')
                )
            ),
        )


class GeotrekSiteFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        q = request.GET.get('q')
        if q:
            queryset = queryset.filter(name__icontains=q)
        return queryset

    def get_schema_fields(self, view):
        return (
            Field(
                name='q', required=False, location='query', schema=coreschema.String(
                    title=_("Query string"),
                    description=_('Filter by some case-insensitive text contained in name.')
                )
            ),
        )


class GeotrekCourseFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        q = request.GET.get('q')
        if q:
            queryset = queryset.filter(name__icontains=q)
        return queryset

    def get_schema_fields(self, view):
        return (
            Field(
                name='q', required=False, location='query', schema=coreschema.String(
                    title=_("Query string"),
                    description=_('Filter by some case-insensitive text contained in name.')
                )
            ),
        )


class RelatedObjectsPublishedNotDeletedFilter(BaseFilterBackend):
    def get_schema_fields(self, view):
        return (
            Field(
                name='portals', required=False, location='query', schema=coreschema.String(
                    title=_("Portals"),
                    description=_('Filter by one or more portal id, comma-separateds.')
                )
            ),
        )

    def filter_queryset_related_objects_published_not_deleted(self, queryset, request, prefix, optional_query=None):
        """
        TODO : this method is not optimal. the API should have a route /object returning all objects and /object/used returning only used objects.
        Return a queryset filtered by publication status or related objects.
        For example for a queryset of DifficultyLevels it will check the publication status of related treks and return the queryset of difficulties that are used by published treks.
        :param queryset: the queryset to filter
        :param request: the request object to get to the potential language to filter by
        :param prefix: the prefix used to fetch the related object in the filter method
        :param optional_query: optional query Q to add to the filter method (used by portal filter)
        """
        qs = queryset
        # Exclude if no related objects exist
        qs = qs.exclude(**{'{}'.format(prefix): None})
        language = request.GET.get('language', 'all')
        q = Q()
        if language == 'all':
            # no language specified. Check for all.
            for lang in settings.MODELTRANSLATION_LANGUAGES:
                related_field_name = '{}__published_{}'.format(prefix, lang)
                q |= Q(**{related_field_name: True})
        else:
            # one language is specified
            related_field_name = '{}__published_{}'.format(prefix, language)
            q &= Q(**{related_field_name: True})
        # Ensure no deleted content is taken in consideration in the filter
        related_field_name = '{}__deleted'.format(prefix)
        q &= Q(**{related_field_name: False})
        q &= optional_query
        qs = qs.filter(q)
        return qs.distinct()


class RelatedPortalGenericFilter(RelatedObjectsPublishedNotDeletedFilter):
    def filter_queryset_related_objects_published_not_deleted_by_portal(self, qs, request, related_name, optional_query=Q()):
        portals = request.GET.get('portals')
        query = Q()
        if portals:
            related_portal_in = '{}__portal__in'.format(related_name)
            query &= Q(**{related_portal_in: portals.split(',')})
            qs = qs.filter(query)
        query &= optional_query
        return self.filter_queryset_related_objects_published_not_deleted(qs, request, related_name, query)


class TrekRelatedPortalFilter(RelatedPortalGenericFilter):
    def filter_queryset(self, request, qs, view):
        return self.filter_queryset_related_objects_published_not_deleted_by_portal(qs, request, 'treks')


class TouristicEventRelatedPortalFilter(RelatedPortalGenericFilter):
    def filter_queryset(self, request, qs, view):
        return self.filter_queryset_related_objects_published_not_deleted_by_portal(qs, request, 'touristicevent')


# class SiteRelatedPortalFilter(RelatedPortalGenericFilter):
#     def filter_queryset(self, request, qs, view):
#         return self.filter_queryset_related_objects_published_not_deleted_by_portal(qs, request, 'sites')


# class CourseRelatedPortalFilter(RelatedPortalGenericFilter):
#     def filter_queryset(self, request, qs, view):
#         return self.filter_queryset_related_objects_published_not_deleted_by_portal(qs, request, 'courses')


class GeotrekRelatedPortalStructureOrReservationSystemFilter(RelatedObjectsPublishedNotDeletedFilter):
    def filter_queryset(self, request, qs, view):
        portals = request.GET.get('portals')
        query = Q()
        if portals:
            query = Q(trek__portal__in=portals.split(',')) | Q(touristiccontent__portal__in=portals.split(','))
        set_1 = self.filter_queryset_related_objects_published_not_deleted(qs, request, 'trek', query)
        set_2 = self.filter_queryset_related_objects_published_not_deleted(qs, request, 'touristiccontent', query)
        return (set_1 | set_2).distinct()


class GeotrekRelatedPortalTourismFilter(RelatedPortalGenericFilter):
    def filter_queryset(self, request, qs, view):
        return self.filter_queryset_related_objects_published_not_deleted_by_portal(qs, request, 'contents')


class GeotrekRelatedPortalThemeFilter(RelatedObjectsPublishedNotDeletedFilter):
    def filter_queryset(self, request, qs, view):
        portals = request.GET.get('portals')
        query = Q()
        if portals:
            query = Q(treks__portal__in=portals.split(',')) \
                | Q(touristiccontents__portal__in=portals.split(',')) \
                | Q(touristic_events__portal__in=portals.split(','))
        set_1 = self.filter_queryset_related_objects_published_not_deleted(qs, request, 'treks', query)
        set_2 = self.filter_queryset_related_objects_published_not_deleted(qs, request, 'touristiccontents', query)
        set_3 = self.filter_queryset_related_objects_published_not_deleted(qs, request, 'touristic_events', query)
        return (set_1 | set_2 | set_3).distinct()


class GeotrekRatingScaleFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        practices = request.GET.get('practices')
        if practices:
            queryset = queryset.filter(practice__in=practices.split(','))
        q = request.GET.get('q')
        if q:
            queryset = queryset.filter(name__icontains=q)
        return queryset

    def get_schema_fields(self, view):
        return (
            Field(
                name='practices', required=False, location='query', schema=coreschema.Integer(
                    title=_("Practices"),
                    description=_('Filter by one or more practice id, comma-separated.')
                )
            ), Field(
                name='q', required=False, location='query', schema=coreschema.String(
                    title=_("Query string"),
                    description=_('Filter by some case-insensitive text contained in name.')
                )
            ),
        )


class GeotrekRatingFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        scale = request.GET.get('scale')
        if scale:
            queryset = queryset.filter(scale__pk=scale)
        q = request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) | Q(description__icontains=q) | Q(scale__name__icontains=q)
            )
        return queryset

    def get_schema_fields(self, view):
        return (
            Field(
                name='scale', required=False, location='query', schema=coreschema.Integer(
                    title=_("Rating scale"),
                    description=_('Filter by a rating scale id.')
                )
            ), Field(
                name='q', required=False, location='query', schema=coreschema.String(
                    title=_("Query string"),
                    description=_('Filter by some case-insensitive text contained in name, scale name or description.')
                )
            ),
        )


class FlatPageFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        targets = request.GET.get('targets')
        if targets:
            queryset = queryset.filter(target__in=targets.split(','))
        sources = request.GET.get('sources')
        if sources:
            queryset = queryset.filter(source__in=sources.split(','))
        portals = request.GET.get('portals')
        if portals:
            queryset = queryset.filter(portal__in=portals.split(','))
        q = request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) | Q(content__icontains=q)
            )
        return queryset

    def get_schema_fields(self, view):
        return (
            Field(
                name='targets', required=False, location='query', schema=coreschema.Integer(
                    title=_("Targets"),
                    description=_('Filter by one or more target (all, mobile, hidden or web), comma-separated.')
                )
            ), Field(
                name='sources', required=False, location='query', schema=coreschema.Integer(
                    title=_("Sources"),
                    description=_('Filter by one or more source id, comma-separated.')
                )
            ), Field(
                name='portals', required=False, location='query', schema=coreschema.Integer(
                    title=_("Portals"),
                    description=_('Filter by one or more portal id, comma-separated.')
                )
            ), Field(
                name='q', required=False, location='query', schema=coreschema.String(
                    title=_("Query string"),
                    description=_('Filter by some case-insensitive text contained in name or content.')
                )
            ),
        )
