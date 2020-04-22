from django.test import TestCase
from django.conf import settings
from django.test.utils import override_settings

from geotrek.core import factories as core_factories
from geotrek.tourism import factories as tourism_factories
from geotrek.trekking import factories as trekking_factories
from geotrek.tourism.factories import InformationDeskTypeFactory

import datetime


class InformationDeskTypeTest(TestCase):
    def setUp(self):
        self.type_informationdesk = InformationDeskTypeFactory(label="Office")

    def test_str(self):
        self.assertEqual(str(self.type_informationdesk), "Office")


class TourismRelations(TestCase):

    def setUp(self):
        self.content = tourism_factories.TouristicContentFactory(geom='SRID=%s;POINT(1 1)' % settings.SRID)
        self.content2 = tourism_factories.TouristicContentFactory(geom='SRID=%s;POINT(2 2)' % settings.SRID, name="ZZZ")
        self.event = tourism_factories.TouristicEventFactory(geom='SRID=%s;POINT(50 50)' % settings.SRID)
        self.event2 = tourism_factories.TouristicEventFactory(geom='SRID=%s;POINT(60 60)' % settings.SRID, name="ZZZ")
        if settings.TREKKING_TOPOLOGY_ENABLED:
            path = core_factories.PathFactory(geom='SRID=%s;LINESTRING(0 100, 100 100)' % settings.SRID)
            self.trek = trekking_factories.TrekFactory(paths=[path])
            self.poi = trekking_factories.POIFactory(paths=[(path, 0.5, 0.5)])
        else:
            self.trek = trekking_factories.TrekFactory(geom='SRID=%s;LINESTRING(0 100, 100 100)' % settings.SRID)
            self.poi = trekking_factories.POIFactory(geom='SRID=%s;POINT(50 100)' % settings.SRID)

    def test_spatial_link_with_tourism(self):
        self.assertIn(self.content2, self.content.touristic_contents.all())
        self.assertIn(self.event, self.content.touristic_events.all())
        self.assertIn(self.content, self.event.touristic_contents.all())
        self.assertIn(self.event2, self.event.touristic_events.all())

    def test_spatial_links_do_not_self_intersect(self):
        self.assertNotIn(self.content, self.content.touristic_contents.all())
        self.assertNotIn(self.event, self.event.touristic_contents.all())

    @override_settings(TOURISM_INTERSECTION_MARGIN=10)
    def test_spatial_link_with_tourism_respects_limit(self):
        self.assertNotIn(self.event, self.content.touristic_events.all())
        self.assertNotIn(self.content, self.event.touristic_contents.all())

    def test_spatial_link_with_topologies(self):
        self.assertIn(self.trek, self.content.treks.all())
        self.assertIn(self.poi, self.content.pois.all())
        self.assertIn(self.trek, self.event.treks.all())
        self.assertIn(self.poi, self.event.pois.all())

    @override_settings(TOURISM_INTERSECTION_MARGIN=10)
    def test_spatial_link_with_topologies_respects_limit(self):
        self.assertNotIn(self.trek, self.content.treks.all())
        self.assertNotIn(self.poi, self.content.pois.all())
        self.assertNotIn(self.trek, self.event.treks.all())
        self.assertNotIn(self.poi, self.event.pois.all())

    def test_spatial_link_from_topologies(self):
        self.assertIn(self.content, self.trek.touristic_contents.all())
        self.assertIn(self.content, self.poi.touristic_contents.all())
        self.assertIn(self.event, self.trek.touristic_events.all())
        self.assertIn(self.event, self.poi.touristic_events.all())

    @override_settings(TOURISM_INTERSECTION_MARGIN=10)
    def test_spatial_link_from_topologies_respects_limit(self):
        self.assertNotIn(self.content, self.trek.touristic_contents.all())
        self.assertNotIn(self.content, self.poi.touristic_contents.all())
        self.assertNotIn(self.event, self.trek.touristic_events.all())
        self.assertNotIn(self.event, self.poi.touristic_events.all())

    def test_spatial_link_from_trek_with_practice_distance(self):
        self.trek.practice.distance = 2000
        self.trek.practice.save()
        self.assertIn(self.content, self.trek.touristic_contents.all())
        self.assertIn(self.event, self.trek.touristic_events.all())

    def test_spatial_link_from_trek_with_practice_distance_respects_limit(self):
        self.trek.practice.distance = 10
        self.trek.practice.save()
        self.assertNotIn(self.content, self.trek.touristic_contents.all())
        self.assertNotIn(self.event, self.trek.touristic_events.all())

    def test_spatial_link_default_ordering(self):
        self.assertEqual(self.trek.touristic_contents.all()[0], self.content)
        self.assertEqual(self.trek.touristic_contents.all()[1], self.content2)

    @override_settings(TOURISTIC_CONTENTS_API_ORDER=('-name', ))
    def test_spatial_link_settings_ordering(self):
        self.assertEqual(self.trek.touristic_contents.all()[0], self.content2)
        self.assertEqual(self.trek.touristic_contents.all()[1], self.content)


class TouristicEventModelTest(TestCase):
    def test_dates_display_no_begin_date(self):
        date = datetime.datetime(year=2000, month=1, day=12)
        event = tourism_factories.TouristicEventFactory(begin_date=None, end_date=date)
        self.assertEqual('up to 01/12/2000', event.dates_display)

    def test_dates_display_no_end_date(self):
        date = datetime.datetime(year=2000, month=1, day=12)
        event = tourism_factories.TouristicEventFactory(begin_date=date, end_date=None)
        self.assertEqual('starting from 01/12/2000', event.dates_display)

    def test_dates_display_same_date(self):
        date = datetime.datetime(year=2000, month=1, day=12)
        event = tourism_factories.TouristicEventFactory(begin_date=date, end_date=date)
        self.assertEqual('01/12/2000', event.dates_display)

    def test_dates_display_no_end_begin_date(self):
        event = tourism_factories.TouristicEventFactory(begin_date=None, end_date=None)
        self.assertEqual('', event.dates_display)

    def test_dates_display_end_begin_date_different(self):
        date_1 = datetime.datetime(year=2000, month=1, day=12)
        date_2 = datetime.datetime(year=2001, month=1, day=12)
        event = tourism_factories.TouristicEventFactory(begin_date=date_1, end_date=date_2)
        self.assertEqual('from 01/12/2000 to 01/12/2001', event.dates_display)


class TouristicContentModelTest(TestCase):
    def tests_type_poi_mobilev1(self):
        category = tourism_factories.TouristicContentCategoryFactory(label="Test")
        content = tourism_factories.TouristicContentFactory(geom='SRID=%s;POINT(1 1)' % settings.SRID,
                                                            category=category)

        self.assertEqual(str(content.type), "Test")
