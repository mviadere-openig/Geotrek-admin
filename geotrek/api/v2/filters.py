from datetime import date
import operator
from functools import reduce

from coreapi.document import Field
from django.conf import settings
from django.db.models.query_utils import Q
from django.utils.translation import ugettext as _
from rest_framework.filters import BaseFilterBackend
from rest_framework_gis.filters import InBBOXFilter, DistanceToPointFilter


class GeotrekQueryParamsFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset

    def get_schema_fields(self, view):
        field_dim = Field(name='dim', required=False,
                          description=_('Set geometry dimension (2 by default for 2D, 3 for 3D)'),
                          example=3, type='integer')
        field_language = Field(name='language', required=False,
                               description=_("Set language for translation. 'all' by default"),
                               example="fr")
        field_format = Field(name='format', required=False,
                             description=_("Set output format (json / geojson). JSON by default"),
                             example="geojson")
        field_fields = Field(name='fields', required=False,
                             description=_("Limit required fields to increase performances. Ex : id,url,geometry"))
        field_omit = Field(name='omit', required=False,
                           description=_("Omit specified fields to increase performance. Ex: url,category"))
        return field_dim, field_language, field_format, field_fields, field_omit


class GeotrekInBBoxFilter(InBBOXFilter):
    """
    Override DRF gis InBBOXFilter with coreapi field descriptors
    """

    def get_schema_fields(self, view):
        field_in_bbox = Field(name=self.bbox_param, required=False,
                              description=_('Filter elements contained in bbox formatted like SW-lng,SW-lat,NE-lng,NE-lat'),
                              example='1.15,46.1,1.56,47.6')

        return field_in_bbox,


class GeotrekDistanceToPointFilter(DistanceToPointFilter):
    """
    Override DRF gis DistanceToPointFilter with coreapi field descriptors
    """

    def get_schema_fields(self, view):
        field_dist = Field(name=self.dist_param, required=False,
                           description=_('Max distance in meters between point and elements'),
                           type='number',
                           example='XXX')
        field_point = Field(name=self.point_param, required=False,
                            description=_('Reference point to compute distance LNG,LAT'),
                            example='1.2563,46.5214', )
        return field_dist, field_point


class GeotrekPublishedFilter(BaseFilterBackend):
    """
    Filter with published state in combination with language
    """

    def filter_queryset(self, request, queryset, view):
        if not hasattr(queryset.model, 'published'):
            return queryset
        qs = queryset
        published = request.GET.get('published', 'true')

        if published.lower() == 'true':
            published = True
        elif published.lower() == 'false':
            published = False
        else:
            published = None
        if published is not None:
            language = request.GET.get('language', 'all')

            if published:
                # if language, check language published. Else, if true one language must me published, if false none
                if language == 'all':
                    filters = list()
                    for lang in settings.MODELTRANSLATION_LANGUAGES:
                        filters.append(Q(**{'published_{}'.format(lang): published}))

                    qs = qs.filter(reduce(operator.or_, filters))

                else:
                    qs = qs.filter(**{'published_{}'.format(language): published})
            else:
                if language == 'all':
                    filters = {}
                    for lang in settings.MODELTRANSLATION_LANGUAGES:
                        filters.update({'published_{}'.format(lang): False})

                    qs = qs.filter(**filters)

                else:
                    qs = qs.filter(**{'published_{}'.format(language): published})
        return qs

    def get_schema_fields(self, view):
        field_published = Field(name='published', required=False,
                                description=_('Publication state. If language specified, only language published are filterted. true/false/all. true by default.'),
                                type='boolean',
                                example='true')
        return field_published,


class GeotrekSensitiveAreaFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        qs = queryset
        practices = request.GET.get('practices', '')
        if practices:
            qs = qs.filter(species__practices__id__in=practices.split(','))
        structure = request.GET.get('structure', '')
        if structure:
            qs = qs.filter(structure_id=structure)
        period = request.GET.get('period', '')
        if not period:
            qs = qs.filter(**{'species__period{:02}'.format(date.today().month): True})
        elif period == 'any':
            qs = qs.filter(reduce(operator.or_, (Q(**{'species__period{:02}'.format(m): True}) for m in range(1, 13))))
        elif period == 'ignore':
            pass
        else:
            months = [int(m) for m in period.split(',')]
            qs = qs.filter(reduce(operator.or_, (Q(**{'species__period{:02}'.format(m): True}) for m in months)))
        return qs.distinct()

    def get_schema_fields(self, view):
        field_period = Field(name='period', required=False,
                             description=_('Period of occupancy. Month numbers (1-12) separated by comas. any = occupied at any time in the year. ignore = occupied or not.'),
                             example='7,8 for july and august')
        field_practices = Field(name='practices', required=False,
                                description=_('Practices ids separated by comas.'),
                                example='1,3')
        field_structure = Field(name='structure', required=False,
                                description=_('Structure id.'),
                                example='5')
        return field_period, field_practices, field_structure
