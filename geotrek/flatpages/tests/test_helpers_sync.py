from io import StringIO
import os
import shutil
from unittest.mock import patch

from django.test import TestCase

from geotrek.common.factories import FakeSyncCommand, RecordSourceFactory, TargetPortalFactory
from geotrek.flatpages.factories import FlatPageFactory
from geotrek.flatpages.helpers_sync import SyncRando


class SyncRandoTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super(SyncRandoTestCase, cls).setUpClass()
        cls.flatpage = FlatPageFactory.create(published=True, title="test-0")
        cls.source = RecordSourceFactory()

        cls.portal = TargetPortalFactory()
        cls.flatpage_s_p = FlatPageFactory.create(published=True, title="test")
        cls.flatpage_s_p.source.add(cls.source)
        cls.flatpage_s_p.portal.add(cls.portal)
        cls.flatpage_s_p.save()

    @patch('sys.stdout', new_callable=StringIO)
    def test_flatpages(self, mock_stdout):
        command = FakeSyncCommand()
        synchro = SyncRando(command)
        synchro.sync('en')
        self.assertTrue(os.path.exists(os.path.join('var', 'tmp_sync_rando', 'api', 'en', 'flatpages.geojson')))
        self.assertTrue(os.path.exists(os.path.join('var', 'tmp_sync_rando', 'meta', 'en', 'informations',
                                                    'test-0', 'index.html')))

    @patch('sys.stdout', new_callable=StringIO)
    def test_flatpages_sources_portal_filter(self, mock_stdout):
        command = FakeSyncCommand(portal=self.portal.name, source=[self.source.name])
        synchro = SyncRando(command)
        synchro.sync('en')
        self.assertTrue(os.path.exists(os.path.join('var', 'tmp_sync_rando', 'api', 'en', 'flatpages.geojson')))
        self.assertTrue(os.path.exists(os.path.join('var', 'tmp_sync_rando', 'meta', 'en', 'informations',
                                                    'test', 'index.html')))

    def tearDown(self):
        if os.path.exists(os.path.join('var', 'tmp_sync_rando')):
            shutil.rmtree(os.path.join('var', 'tmp_sync_rando'))
