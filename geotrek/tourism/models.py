import os
import re
import logging

from django.conf import settings
from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.formats import date_format

from colorfield.fields import ColorField
from easy_thumbnails.alias import aliases
from easy_thumbnails.exceptions import InvalidImageFormatError
from easy_thumbnails.files import get_thumbnailer
from mapentity.registry import registry
from mapentity.models import MapEntityMixin
from mapentity.serializers import plain_text, smart_plain_text

from geotrek.authent.models import StructureRelated
from geotrek.core.models import Topology
from geotrek.common.mixins import (NoDeleteMixin, TimeStampedModelMixin,
                                   PictogramMixin, OptionalPictogramMixin,
                                   PublishableMixin, PicturesMixin,
                                   AddPropertyMixin)
from geotrek.common.models import Theme
from geotrek.common.utils import intersecting

from extended_choices import Choices

if 'modeltranslation' in settings.INSTALLED_APPS:
    from modeltranslation.manager import MultilingualManager
else:
    from django.db.models import Manager as MultilingualManager

logger = logging.getLogger(__name__)


def _get_target_choices():
    """ Populate choices using installed apps names.
    """
    apps = [('public', _("Public website"))]
    for model, entity in registry.registry.items():
        if entity.menu:
            appname = model._meta.app_label.lower()
            apps.append((appname, entity.label))
    return tuple(apps)


class InformationDeskType(PictogramMixin):

    label = models.CharField(verbose_name=_("Label"), max_length=128, db_column='label')

    class Meta:
        db_table = 't_b_type_renseignement'
        verbose_name = _("Information desk type")
        verbose_name_plural = _("Information desk types")
        ordering = ['label']

    def __str__(self):
        return self.label


class InformationDesk(models.Model):

    name = models.CharField(verbose_name=_("Title"), max_length=256, db_column='nom')
    type = models.ForeignKey(InformationDeskType, verbose_name=_("Type"), on_delete=models.CASCADE,
                             related_name='desks', db_column='type')
    description = models.TextField(verbose_name=_("Description"), blank=True, db_column='description',
                                   help_text=_("Brief description"))
    phone = models.CharField(verbose_name=_("Phone"), max_length=32,
                             blank=True, null=True, db_column='telephone')
    email = models.EmailField(verbose_name=_("Email"), max_length=256, db_column='email',
                              blank=True, null=True)
    website = models.URLField(verbose_name=_("Website"), max_length=256, db_column='website',
                              blank=True, null=True)
    photo = models.FileField(verbose_name=_("Photo"), upload_to=settings.UPLOAD_DIR,
                             db_column='photo', max_length=512, blank=True, null=True)

    street = models.CharField(verbose_name=_("Street"), max_length=256,
                              blank=True, null=True, db_column='rue')
    postal_code = models.CharField(verbose_name=_("Postal code"), max_length=8,
                                   blank=True, null=True, db_column='code')
    municipality = models.CharField(verbose_name=_("Municipality"),
                                    blank=True, null=True,
                                    max_length=256, db_column='commune')

    geom = models.PointField(verbose_name=_("Emplacement"), db_column='geom',
                             blank=True, null=True,
                             srid=settings.SRID, spatial_index=False)

    objects = models.GeoManager()

    class Meta:
        db_table = 't_b_renseignement'
        verbose_name = _("Information desk")
        verbose_name_plural = _("Information desks")
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def description_strip(self):
        """Used in trek public template.
        """
        nobr = re.compile(r'(\s*<br.*?>)+\s*', re.I)
        newlines = nobr.sub("\n", self.description)
        return smart_plain_text(newlines)

    @property
    def serializable_type(self):
        return {
            'id': self.type.id,
            'label': self.type.label,
            'pictogram': self.type.pictogram.url,
        }

    @property
    def latitude(self):
        if self.geom:
            api_geom = self.geom.transform(settings.API_SRID, clone=True)
            return api_geom.y
        return None

    @property
    def longitude(self):
        if self.geom:
            api_geom = self.geom.transform(settings.API_SRID, clone=True)
            return api_geom.x
        return None

    @property
    def thumbnail(self):
        if not self.photo:
            return None
        thumbnailer = get_thumbnailer(self.photo)
        try:
            return thumbnailer.get_thumbnail(aliases.get('thumbnail'))
        except (IOError, InvalidImageFormatError):
            logger.warning(_("Image %s invalid or missing from disk.") % self.photo)
            return None

    @property
    def resized_picture(self):
        if not self.photo:
            return None
        thumbnailer = get_thumbnailer(self.photo)
        try:
            return thumbnailer.get_thumbnail(aliases.get('medium'))
        except (IOError, InvalidImageFormatError):
            logger.warning(_("Image %s invalid or missing from disk.") % self.photo)
            return None

    @property
    def photo_url(self):
        thumbnail = self.thumbnail
        if not thumbnail:
            return None
        return os.path.join(settings.MEDIA_URL, thumbnail.name)


GEOMETRY_TYPES = Choices(
    ('POINT', 'point', _('Point')),
    ('LINE', 'line', _('Line')),
    ('POLYGON', 'polygon', _('Polygon')),
    ('ANY', 'any', _('Any')),
)


class TouristicContentCategory(PictogramMixin):

    label = models.CharField(verbose_name=_("Label"), max_length=128, db_column='nom')
    geometry_type = models.CharField(db_column="type_geometrie", max_length=16,
                                     choices=GEOMETRY_TYPES, default=GEOMETRY_TYPES.POINT)
    type1_label = models.CharField(verbose_name=_("First list label"), max_length=128,
                                   db_column='label_type1', blank=True)
    type2_label = models.CharField(verbose_name=_("Second list label"), max_length=128,
                                   db_column='label_type2', blank=True)
    order = models.IntegerField(verbose_name=_("Order"), null=True, blank=True, db_column='tri',
                                help_text=_("Alphabetical order if blank"))
    color = ColorField(verbose_name=_("Color"), default='#444444', db_column='couleur',
                       help_text=_("Color of the category, only used in mobile."))  # To be implemented in Geotrek-rando

    id_prefix = 'C'

    class Meta:
        db_table = 't_b_contenu_touristique_categorie'
        verbose_name = _("Touristic content category")
        verbose_name_plural = _("Touristic content categories")
        ordering = ['order', 'label']

    def __str__(self):
        return self.label

    @property
    def prefixed_id(self):
        return '{prefix}{id}'.format(prefix=self.id_prefix, id=self.id)


class TouristicContentType(OptionalPictogramMixin):

    label = models.CharField(verbose_name=_("Label"), max_length=128, db_column='nom')
    category = models.ForeignKey(TouristicContentCategory, related_name='types', on_delete=models.CASCADE,
                                 verbose_name=_("Category"), db_column='categorie')
    # Choose in which list of choices this type will appear
    in_list = models.IntegerField(choices=((1, _("First")), (2, _("Second"))), db_column='liste_choix')

    class Meta:
        db_table = 't_b_contenu_touristique_type'
        verbose_name = _("Touristic content type")
        verbose_name_plural = _("Touristic content type")
        ordering = ['label']

    def __str__(self):
        return self.label


class TouristicContentType1Manager(MultilingualManager):
    def get_queryset(self):
        return super(TouristicContentType1Manager, self).get_queryset().filter(in_list=1)


class TouristicContentType2Manager(MultilingualManager):
    def get_queryset(self):
        return super(TouristicContentType2Manager, self).get_queryset().filter(in_list=2)


class TouristicContentType1(TouristicContentType):
    objects = TouristicContentType1Manager()

    def __init__(self, *args, **kwargs):
        self._meta.get_field('in_list').default = 1
        super(TouristicContentType1, self).__init__(*args, **kwargs)

    class Meta:
        proxy = True
        verbose_name = _("Type1")
        verbose_name_plural = _("First list types")


class TouristicContentType2(TouristicContentType):
    objects = TouristicContentType2Manager()

    def __init__(self, *args, **kwargs):
        self._meta.get_field('in_list').default = 2
        super(TouristicContentType2, self).__init__(*args, **kwargs)

    class Meta:
        proxy = True
        verbose_name = _("Type2")
        verbose_name_plural = _("Second list types")


class ReservationSystem(models.Model):
    name = models.CharField(verbose_name=_("Name"), max_length=256,
                            blank=False, null=False, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 't_b_systeme_reservation'
        verbose_name = _("Reservation system")
        verbose_name_plural = _("Reservation systems")
        ordering = ('name',)


class TouristicContent(AddPropertyMixin, PublishableMixin, MapEntityMixin, StructureRelated,
                       TimeStampedModelMixin, PicturesMixin, NoDeleteMixin):
    """ A generic touristic content (accomodation, museum, etc.) in the park
    """
    description_teaser = models.TextField(verbose_name=_("Description teaser"), blank=True,
                                          help_text=_("A brief summary"), db_column='chapeau')
    description = models.TextField(verbose_name=_("Description"), blank=True, db_column='description',
                                   help_text=_("Complete description"))
    themes = models.ManyToManyField(Theme, related_name="touristiccontents",
                                    db_table="t_r_contenu_touristique_theme", blank=True, verbose_name=_("Themes"),
                                    help_text=_("Main theme(s)"))
    geom = models.GeometryField(verbose_name=_("Location"), srid=settings.SRID)
    category = models.ForeignKey(TouristicContentCategory, related_name='contents', on_delete=models.CASCADE,
                                 verbose_name=_("Category"), db_column='categorie')
    contact = models.TextField(verbose_name=_("Contact"), blank=True, db_column='contact',
                               help_text=_("Address, phone, etc."))
    email = models.EmailField(verbose_name=_("Email"), max_length=256, db_column='email',
                              blank=True, null=True)
    website = models.URLField(verbose_name=_("Website"), max_length=256, db_column='website',
                              blank=True, null=True)
    practical_info = models.TextField(verbose_name=_("Practical info"), blank=True, db_column='infos_pratiques',
                                      help_text=_("Anything worth to know"))
    type1 = models.ManyToManyField(TouristicContentType1, related_name='contents1',
                                   verbose_name=_("Type 1"), db_table="t_r_contenu_touristique_type1",
                                   blank=True)
    type2 = models.ManyToManyField(TouristicContentType2, related_name='contents2',
                                   verbose_name=_("Type 2"), db_table="t_r_contenu_touristique_type2",
                                   blank=True)
    source = models.ManyToManyField('common.RecordSource',
                                    blank=True, related_name='touristiccontents',
                                    verbose_name=_("Source"), db_table='t_r_contenu_touristique_source')
    portal = models.ManyToManyField('common.TargetPortal',
                                    blank=True, related_name='touristiccontents',
                                    verbose_name=_("Portal"), db_table='t_r_contenu_touristique_portal')
    eid = models.CharField(verbose_name=_("External id"), max_length=1024, blank=True, null=True, db_column='id_externe')
    reservation_system = models.ForeignKey(ReservationSystem, verbose_name=_("Reservation system"),
                                           on_delete=models.CASCADE, blank=True, null=True)
    reservation_id = models.CharField(verbose_name=_("Reservation ID"), max_length=1024,
                                      blank=True, db_column='id_reservation')
    approved = models.BooleanField(verbose_name=_("Approved"), default=False, db_column='labellise')

    objects = NoDeleteMixin.get_manager_cls(models.GeoManager)()

    class Meta:
        db_table = 't_t_contenu_touristique'
        verbose_name = _("Touristic content")
        verbose_name_plural = _("Touristic contents")

    def __str__(self):
        return self.name

    @property
    def districts_display(self):
        return ', '.join([str(d) for d in self.districts])

    @property
    def type1_label(self):
        return self.category.type1_label

    @property
    def type2_label(self):
        return self.category.type2_label

    @property
    def type1_display(self):
        return ', '.join([str(n) for n in self.type1.all()])

    @property
    def type2_display(self):
        return ', '.join([str(n) for n in self.type2.all()])

    @property
    def prefixed_category_id(self):
        return self.category.prefixed_id

    def distance(self, to_cls):
        return settings.TOURISM_INTERSECTION_MARGIN

    @property
    def type(self):
        """Fake type to simulate POI for mobile app v1"""
        return self.category

    @property
    def min_elevation(self):
        return 0

    @property
    def max_elevation(self):
        return 0

    @property
    def portal_display(self):
        return ', '.join([str(portal) for portal in self.portal.all()])

    @property
    def source_display(self):
        return ','.join([str(source) for source in self.source.all()])

    @property
    def themes_display(self):
        return ','.join([str(source) for source in self.themes.all()])

    @property
    def extent(self):
        return self.geom.buffer(10).transform(settings.API_SRID, clone=True).extent

    @property
    def rando_url(self):
        category_slug = _('touristic-content')
        return '{}/{}/'.format(category_slug, self.slug)

    @property
    def meta_description(self):
        return plain_text(self.description_teaser or self.description)[:500]


Topology.add_property('touristic_contents', lambda self: intersecting(TouristicContent, self), _("Touristic contents"))
Topology.add_property('published_touristic_contents', lambda self: intersecting(TouristicContent, self).filter(published=True), _("Published touristic contents"))
TouristicContent.add_property('touristic_contents', lambda self: intersecting(TouristicContent, self), _("Touristic contents"))
TouristicContent.add_property('published_touristic_contents', lambda self: intersecting(TouristicContent, self).filter(published=True), _("Published touristic contents"))


class TouristicEventType(OptionalPictogramMixin):

    type = models.CharField(verbose_name=_("Type"), max_length=128, db_column='type')

    class Meta:
        db_table = 't_b_evenement_touristique_type'
        verbose_name = _("Touristic event type")
        verbose_name_plural = _("Touristic event types")
        ordering = ['type']

    def __str__(self):
        return self.type


class TouristicEvent(AddPropertyMixin, PublishableMixin, MapEntityMixin, StructureRelated,
                     PicturesMixin, TimeStampedModelMixin, NoDeleteMixin):
    """ A touristic event (conference, workshop, etc.) in the park
    """
    description_teaser = models.TextField(verbose_name=_("Description teaser"), blank=True,
                                          help_text=_("A brief summary"), db_column='chapeau')
    description = models.TextField(verbose_name=_("Description"), blank=True, db_column='description',
                                   help_text=_("Complete description"))
    themes = models.ManyToManyField(Theme, related_name="touristic_events",
                                    db_table="t_r_evenement_touristique_theme", blank=True, verbose_name=_("Themes"),
                                    help_text=_("Main theme(s)"))
    geom = models.PointField(verbose_name=_("Location"), srid=settings.SRID)
    begin_date = models.DateField(blank=True, null=True, verbose_name=_("Begin date"), db_column='date_debut')
    end_date = models.DateField(blank=True, null=True, verbose_name=_("End date"), db_column='date_fin')
    duration = models.CharField(verbose_name=_("Duration"), max_length=64, blank=True, db_column='duree',
                                help_text=_("3 days, season, ..."))
    meeting_point = models.CharField(verbose_name=_("Meeting point"), max_length=256, blank=True, db_column='point_rdv',
                                     help_text=_("Where exactly ?"))
    meeting_time = models.TimeField(verbose_name=_("Meeting time"), blank=True, null=True, db_column='heure_rdv',
                                    help_text=_("11:00, 23:30"))
    contact = models.TextField(verbose_name=_("Contact"), blank=True, db_column='contact')
    email = models.EmailField(verbose_name=_("Email"), max_length=256, db_column='email',
                              blank=True, null=True)
    website = models.URLField(verbose_name=_("Website"), max_length=256, db_column='website',
                              blank=True, null=True)
    organizer = models.CharField(verbose_name=_("Organizer"), max_length=256, blank=True, db_column='organisateur')
    speaker = models.CharField(verbose_name=_("Speaker"), max_length=256, blank=True, db_column='intervenant')
    type = models.ForeignKey(TouristicEventType, verbose_name=_("Type"), blank=True, null=True, db_column='type', on_delete=models.CASCADE)
    accessibility = models.CharField(verbose_name=_("Accessibility"), max_length=256, blank=True, db_column='accessibilite')
    participant_number = models.CharField(verbose_name=_("Number of participants"), max_length=256, blank=True, db_column='nb_places')
    booking = models.TextField(verbose_name=_("Booking"), blank=True, db_column='reservation')
    target_audience = models.CharField(verbose_name=_("Target audience"), max_length=128, blank=True, null=True, db_column='public_vise')
    practical_info = models.TextField(verbose_name=_("Practical info"), blank=True, db_column='infos_pratiques',
                                      help_text=_("Recommandations / To plan / Advices"))
    source = models.ManyToManyField('common.RecordSource',
                                    blank=True, related_name='touristicevents',
                                    verbose_name=_("Source"), db_table='t_r_evenement_touristique_source')
    portal = models.ManyToManyField('common.TargetPortal',
                                    blank=True, related_name='touristicevents',
                                    verbose_name=_("Portal"), db_table='t_r_evenement_touristique_portal')
    eid = models.CharField(verbose_name=_("External id"), max_length=1024, blank=True, null=True, db_column='id_externe')
    approved = models.BooleanField(verbose_name=_("Approved"), default=False, db_column='labellise')

    objects = NoDeleteMixin.get_manager_cls(models.GeoManager)()

    category_id_prefix = 'E'

    class Meta:
        db_table = 't_t_evenement_touristique'
        verbose_name = _("Touristic event")
        verbose_name_plural = _("Touristic events")
        ordering = ['-begin_date']

    def __str__(self):
        return self.name

    @property
    def type1(self):
        return [self.type] if self.type else []

    @property
    def type2(self):
        return []

    @property
    def districts_display(self):
        return ', '.join([str(d) for d in self.districts])

    @property
    def dates_display(self):
        if not self.begin_date and not self.end_date:
            return ""
        elif not self.end_date:
            return _("starting from {begin}").format(
                begin=date_format(self.begin_date, 'SHORT_DATE_FORMAT'))
        elif not self.begin_date:
            return _("up to {end}").format(
                end=date_format(self.end_date, 'SHORT_DATE_FORMAT'))
        elif self.begin_date == self.end_date:
            return date_format(self.begin_date, 'SHORT_DATE_FORMAT')
        else:
            return _("from {begin} to {end}").format(
                begin=date_format(self.begin_date, 'SHORT_DATE_FORMAT'),
                end=date_format(self.end_date, 'SHORT_DATE_FORMAT'))

    @property
    def prefixed_category_id(self):
        return self.category_id_prefix

    def distance(self, to_cls):
        return settings.TOURISM_INTERSECTION_MARGIN

    @property
    def portal_display(self):
        return ', '.join([str(portal) for portal in self.portal.all()])

    @property
    def source_display(self):
        return ', '.join([str(source) for source in self.source.all()])

    @property
    def themes_display(self):
        return ','.join([str(source) for source in self.themes.all()])

    @property
    def rando_url(self):
        category_slug = _('touristic-event')
        return '{}/{}/'.format(category_slug, self.slug)

    @property
    def meta_description(self):
        return plain_text(self.description_teaser or self.description)[:500]


TouristicEvent.add_property('touristic_contents', lambda self: intersecting(TouristicContent, self), _("Touristic contents"))
TouristicEvent.add_property('published_touristic_contents', lambda self: intersecting(TouristicContent, self).filter(published=True), _("Published touristic contents"))
Topology.add_property('touristic_events', lambda self: intersecting(TouristicEvent, self), _("Touristic events"))
Topology.add_property('published_touristic_events', lambda self: intersecting(TouristicEvent, self).filter(published=True), _("Published touristic events"))
TouristicContent.add_property('touristic_events', lambda self: intersecting(TouristicEvent, self), _("Touristic events"))
TouristicContent.add_property('published_touristic_events', lambda self: intersecting(TouristicEvent, self).filter(published=True), _("Published touristic events"))
TouristicEvent.add_property('touristic_events', lambda self: intersecting(TouristicEvent, self), _("Touristic events"))
TouristicEvent.add_property('published_touristic_events', lambda self: intersecting(TouristicEvent, self).filter(published=True), _("Published touristic events"))
