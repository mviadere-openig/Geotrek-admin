from django.conf import settings
from django.urls import reverse
from django.db import models as django_db_models
from django.shortcuts import get_object_or_404
from django.utils.translation import get_language

from rest_framework import serializers as rest_serializers
from rest_framework import serializers as rest_fields

from .models import Theme, RecordSource, TargetPortal, FileType, Attachment


class TranslatedModelSerializer(rest_serializers.ModelSerializer):
    def get_field(self, model_field):
        kwargs = {}
        if issubclass(model_field.__class__,
                      (django_db_models.CharField,
                       django_db_models.TextField)):
            if model_field.null:
                kwargs['allow_none'] = True
            kwargs['max_length'] = getattr(model_field, 'max_length')
            return rest_fields.CharField(**kwargs)
        return super(TranslatedModelSerializer, self).get_field(model_field)


class PictogramSerializerMixin(rest_serializers.ModelSerializer):
    pictogram = rest_serializers.ReadOnlyField(source='get_pictogram_url')


class PicturesSerializerMixin(rest_serializers.ModelSerializer):
    thumbnail = rest_serializers.ReadOnlyField(source='serializable_thumbnail')
    pictures = rest_serializers.ReadOnlyField(source='serializable_pictures')
    videos = rest_serializers.ReadOnlyField(source='serializable_videos')
    files = rest_serializers.ReadOnlyField(source='serializable_files')

    class Meta:
        fields = ('thumbnail', 'pictures', 'videos', 'files')


class BasePublishableSerializerMixin(rest_serializers.ModelSerializer):
    class Meta:
        fields = ('published', 'published_status', 'publication_date')


class PublishableSerializerMixin(BasePublishableSerializerMixin):
    printable = rest_serializers.SerializerMethodField('get_printable_url')
    filelist_url = rest_serializers.SerializerMethodField()

    def get_printable_url(self, obj):
        if settings.ONLY_EXTERNAL_PUBLIC_PDF:
            file_type = get_object_or_404(FileType, type="Topoguide")
            if not Attachment.objects.attachments_for_object_only_type(obj, file_type).exists():
                return None
        appname = obj._meta.app_label
        modelname = obj._meta.model_name
        return reverse('%s:%s_printable' % (appname, modelname),
                       kwargs={'lang': get_language(), 'pk': obj.pk, 'slug': obj.slug})

    def get_filelist_url(self, obj):
        appname = obj._meta.app_label
        modelname = obj._meta.model_name
        return reverse('get_attachments', kwargs={'app_label': appname,
                                                  'model_name': modelname,
                                                  'pk': obj.pk})

    class Meta:
        fields = ('name', 'slug', 'map_image_url', 'filelist_url', 'printable') + \
            BasePublishableSerializerMixin.Meta.fields


class ThemeSerializer(PictogramSerializerMixin, TranslatedModelSerializer):
    class Meta:
        model = Theme
        fields = ('id', 'pictogram', 'label')


class RecordSourceSerializer(PictogramSerializerMixin, rest_serializers.ModelSerializer):
    class Meta:
        model = RecordSource
        fields = ('name', 'website', 'pictogram')


class TargetPortalSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = TargetPortal
        fields = ('name', 'website')
