import os
from unittest import mock
import requests

from django.contrib.gis.geos import WKTWriter
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from geotrek.common.tests import TranslationResetMixin
from geotrek.sensitivity.parsers import BiodivParser
from geotrek.sensitivity.models import SportPractice, Species, SensitiveArea
from geotrek.sensitivity.factories import SpeciesFactory, SportPracticeFactory


json_test_sport_practice = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [
        {
            "id": 1,
            "name": {
                "fr": "Terrestre",
                "en": "Land",
                "it": None,
            },
        },
    ],
}

json_test_sport_practice_2 = {
    "count": 2,
    "next": None,
    "previous": None,
    "results": [
        {
            "id": 1,
            "name": {
                "fr": "Terrestre",
                "en": "Land",
                "it": None,
            },
        },
        {
            "id": 2,
            "name": {
                "fr": "Aerien",
                "en": "Air",
                "it": None,
            },
        },
    ],
}

json_test_species = {
    "count": 2,
    "next": None,
    "previous": None,
    "results": [
        {
            "id": 1,
            "url": "https://biodiv-sports.fr/api/v2/sensitivearea/46/?format=json",
            "name": {"fr": "Tétras lyre", "en": "Black grouse", "it": "Fagiano di monte"},
            "description": {"fr": "Blabla", "en": "Blahblah", "it": ""},
            "period": [True, True, True, True, False, False, False, False, False, False, False, True],
            "contact": "",
            "practices": [1],
            "info_url": "",
            "published": True,
            "structure": "LPO",
            "species_id": 7,
            "kml_url": "https://biodiv-sports.fr/api/fr/sensitiveareas/46.kml",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[3.1, 45], [3.2, 45], [3.2, 46], [3.1, 46], [3.1, 45]],
                                [[3.13, 45.3], [3.17, 45.3], [3.17, 45.7], [3.13, 45.7], [3.13, 45.3]]]
            },
            "update_datetime": "2017-11-29T14:53:35.949097Z",
            "create_datetime": "2017-11-29T14:49:01.317155Z",
            "radius": None
        },
        {
            "id": 2,
            "url": "https://biodiv-sports.fr/api/v2/sensitivearea/46/?format=json",
            "name": {"fr": "Tétras lyre", "en": "Black grouse", "it": "Fagiano di monte"},
            "description": {"fr": "Blabla2", "en": "Blahblah2", "it": ""},
            "period": [True, True, True, True, False, False, False, False, False, False, False, True],
            "contact": "",
            "practices": [1],
            "info_url": "",
            "published": True,
            "structure": "LPO",
            "species_id": 7,
            "kml_url": "https://biodiv-sports.fr/api/fr/sensitiveareas/47.kml",
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [[[[3.1, 45], [3.2, 45], [3.2, 46], [3.1, 46], [3.1, 45]],
                                 [[3.13, 45.3], [3.17, 45.3], [3.17, 45.7], [3.13, 45.7], [3.13, 45.3]],
                                 [[3.145, 45.45], [3.155, 45.45], [3.155, 45.55], [3.145, 45.55], [3.145, 45.45]],
                                 [[3.14, 45.4], [3.16, 45.4], [3.16, 45.6], [3.14, 45.6], [3.14, 45.4]],
                                 [[3.11, 45.45], [3.12, 45.45], [3.12, 45.55], [3.11, 45.55], [3.11, 45.45]]],
                                [[[3.1, 45], [3.2, 45], [3.2, 46], [3.1, 46], [3.1, 45]]]
                                ]
            },
            "update_datetime": "2017-11-29T14:53:35.949097Z",
            "create_datetime": "2017-11-29T14:49:01.317155Z",
            "radius": None
        }
    ]
}


class BiodivWithPracticeParser(BiodivParser):
    practices = "1"


class BiodivParserTests(TranslationResetMixin, TestCase):
    @mock.patch('geotrek.sensitivity.parsers.requests')
    def test_create(self, mocked):
        def side_effect(url):
            response = requests.Response()
            response.status_code = 200
            if 'sportpractice' in url:
                response.json = lambda: json_test_sport_practice
            else:
                response.json = lambda: json_test_species
            return response
        mocked.get.side_effect = side_effect
        call_command('import', 'geotrek.sensitivity.parsers.BiodivParser', verbosity=0)
        practice = SportPractice.objects.get()
        species = Species.objects.first()
        area_1 = SensitiveArea.objects.first()
        self.assertEqual(practice.name, "Land")
        self.assertEqual(practice.name_fr, "Terrestre")
        self.assertEqual(species.name, "Black grouse")
        self.assertEqual(species.name_fr, "Tétras lyre")
        self.assertTrue(species.period01)
        self.assertFalse(species.period06)
        self.assertEqual(species.eid, '7')
        self.assertQuerysetEqual(species.practices.all(), ['<SportPractice: Land>'])
        self.assertEqual(area_1.species, species)
        self.assertEqual(area_1.description, "Blahblah")
        self.assertEqual(area_1.description_fr, "Blabla")
        self.assertEqual(area_1.eid, '1')
        area_2 = SensitiveArea.objects.last()
        self.assertQuerysetEqual(species.practices.all(), ['<SportPractice: Land>'])
        self.assertEqual(area_2.species, species)
        self.assertEqual(area_2.description, "Blahblah2")
        self.assertEqual(area_2.description_fr, "Blabla2")
        self.assertEqual(area_2.eid, '2')
        self.assertEqual(area_2.geom.geom_type, 'MultiPolygon')

    @mock.patch('geotrek.sensitivity.parsers.requests')
    def test_create_with_practice(self, mocked):
        def side_effect(url):
            response = requests.Response()
            response.status_code = 200
            if 'sportpractice' in url:
                response.json = lambda: json_test_sport_practice_2
            else:
                response.json = lambda: json_test_species
            return response
        mocked.get.side_effect = side_effect
        call_command('import', 'geotrek.sensitivity.tests.test_parsers.BiodivWithPracticeParser', verbosity=0)
        self.assertEqual(SportPractice.objects.count(), 2)

    @mock.patch('geotrek.sensitivity.parsers.requests')
    def test_status_code_404(self, mocked):
        def side_effect(url):
            response = requests.Response()
            response.status_code = 404
            return response
        mocked.get.side_effect = side_effect
        with self.assertRaisesRegexp(CommandError, "Failed to download https://biodiv-sports.fr/api/v2/sportpractice/"):
            call_command('import', 'geotrek.sensitivity.parsers.BiodivParser', verbosity=0)

    @mock.patch('geotrek.sensitivity.parsers.requests')
    def test_status_code_404_practice(self, mocked):
        def side_effect(url):
            response = requests.Response()
            if 'in_bbox' in url:
                response.status_code = 404
                response.url = "https://rhododendron.com"
            else:
                response.status_code = 200
                response.json = lambda: {"results": []}
            return response
        mocked.get.side_effect = side_effect
        with self.assertRaisesRegexp(CommandError, "Failed to download https://rhododendron.com. HTTP status code 404"):
            call_command('import', 'geotrek.sensitivity.parsers.BiodivParser', verbosity=0)

    @mock.patch('geotrek.sensitivity.parsers.requests')
    def test_create_no_id(self, mocked):
        def side_effect(url):
            response = requests.Response()
            response.status_code = 200
            if 'sportpractice' in url:
                response.json = lambda: json_test_sport_practice
            else:
                json_test_species_without_id = json_test_species.copy()
                json_test_species_without_id['results'][0]['species_id'] = None
                json_test_species_without_id['results'][1]['species_id'] = None
                response.json = lambda: json_test_species_without_id
            return response
        mocked.get.side_effect = side_effect
        call_command('import', 'geotrek.sensitivity.parsers.BiodivParser', verbosity=0)
        practice = SportPractice.objects.first()
        species = Species.objects.first()
        area = SensitiveArea.objects.first()
        self.assertEqual(practice.name, "Land")
        self.assertEqual(practice.name_fr, "Terrestre")
        self.assertEqual(species.name, "Black grouse")
        self.assertEqual(species.name_fr, "Tétras lyre")
        self.assertEqual(species.eid, None)
        self.assertQuerysetEqual(species.practices.all(), ['<SportPractice: Land>'])
        self.assertEqual(area.eid, '1')

    @mock.patch('geotrek.sensitivity.parsers.requests')
    def test_create_species_url(self, mocked):
        def side_effect(url):
            response = requests.Response()
            response.status_code = 200
            if 'sportpractice' in url:
                response.json = lambda: json_test_sport_practice
            else:
                json_test_species_without_id = json_test_species.copy()
                json_test_species_without_id['results'][0]['info_url'] = "toto.com"
                json_test_species_without_id['results'].pop(1)
                response.json = lambda: json_test_species_without_id
            return response
        mocked.get.side_effect = side_effect
        call_command('import', 'geotrek.sensitivity.parsers.BiodivParser', verbosity=0)
        species = Species.objects.first()
        self.assertEqual(species.url, "toto.com")

    @mock.patch('geotrek.sensitivity.parsers.requests')
    def test_create_species_radius(self, mocked):
        def side_effect(url):
            response = requests.Response()
            response.status_code = 200
            if 'sportpractice' in url:
                response.json = lambda: json_test_sport_practice
            else:
                json_test_species_without_id = json_test_species.copy()
                json_test_species_without_id['results'][0]['radius'] = 5
                json_test_species_without_id['results'][1]['radius'] = 5
                response.json = lambda: json_test_species_without_id
            return response
        mocked.get.side_effect = side_effect
        call_command('import', 'geotrek.sensitivity.parsers.BiodivParser', verbosity=0)
        species = Species.objects.first()
        self.assertEqual(species.radius, 5)


class SpeciesSensitiveAreaShapeParserTest(TestCase):
    def test_cli(self):
        filename = os.path.join(os.path.dirname(__file__), 'data', 'species.shp')
        call_command('import', 'geotrek.sensitivity.parsers.SpeciesSensitiveAreaShapeParser', filename, verbosity=0)
        self.assertEqual(SensitiveArea.objects.count(), 0)
        species = SpeciesFactory(name="Aigle royal")
        call_command('import', 'geotrek.sensitivity.parsers.SpeciesSensitiveAreaShapeParser', filename, verbosity=0)
        area = SensitiveArea.objects.first()
        self.assertEqual(area.species, species)
        self.assertEqual(area.contact, "Contact")
        self.assertEqual(area.description, "Test UTF8 éêè")
        self.assertEqual(
            WKTWriter(precision=7).write(area.geom),
            b'POLYGON (('
            b'929315.3613369 6483309.4435054, 929200.3539448 6483204.0200627, '
            b'928404.8861499 6482494.8078118, 928194.0392645 6482082.6979903, '
            b'927925.6886830 6481210.5586006, 927676.5060003 6481287.2301953, '
            b'927772.3454936 6481498.0770807, 927887.3528857 6481900.6029529, '
            b'928184.4553151 6482600.2312545, 928625.3169846 6483520.2903908, '
            b'929162.0181475 6483664.0496309, 929315.3613369 6483309.4435054'
            b'))')


class RegulatorySensitiveAreaShapeParserTest(TestCase):
    def test_regulatory_sensitive_area_shape(self):
        filename = os.path.join(os.path.dirname(__file__), 'data', 'species_regu.shp')
        call_command('import', 'geotrek.sensitivity.parsers.RegulatorySensitiveAreaShapeParser', filename, verbosity=0)
        self.assertEqual(SensitiveArea.objects.count(), 0)
        SportPracticeFactory(name="sport")
        call_command('import', 'geotrek.sensitivity.parsers.RegulatorySensitiveAreaShapeParser', filename, verbosity=0)
        area = SensitiveArea.objects.first()
        self.assertEqual(str(area.species), "Nom")
        self.assertTrue(area.species.period10)
        self.assertTrue(area.species.period11)
        self.assertTrue(area.species.period12)
        self.assertFalse(area.species.period08)
        self.assertEqual(area.species.radius, 23)
        self.assertEqual(area.species.url, "http://test.com")
        self.assertEqual(area.contact, "Contact")
        self.assertEqual(area.description, "Test UTF8 éêè")
        self.assertEqual(
            WKTWriter(precision=7).write(area.geom),
            b'POLYGON (('
            b'929315.3613369 6483309.4435054, 929200.3539448 6483204.0200627, '
            b'928404.8861499 6482494.8078118, 928194.0392645 6482082.6979903, '
            b'927925.6886830 6481210.5586006, 927676.5060003 6481287.2301953, '
            b'927772.3454936 6481498.0770807, 927887.3528857 6481900.6029529, '
            b'928184.4553151 6482600.2312545, 928625.3169846 6483520.2903908, '
            b'929162.0181475 6483664.0496309, 929315.3613369 6483309.4435054'
            b'))')
