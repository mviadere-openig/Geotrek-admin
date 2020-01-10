"""
    Unit tests
"""
from django.test import TestCase
from django.test.utils import override_settings
from django.conf import settings
from django.urls import reverse
from django.utils.translation import LANGUAGE_SESSION_KEY

from mapentity.factories import SuperUserFactory

from geotrek.authent.models import UserProfile


@override_settings(LOGIN_URL='/login/')
class LoginTestCase(TestCase):
    def test_login(self):
        response = self.client.get('/')
        _next = (settings.FORCE_SCRIPT_NAME or '') + '/'
        self.assertRedirects(response, '/login/?next=' + _next)


class UserProfileTest(TestCase):
    def setUp(self):
        self.user = SuperUserFactory(password="Bar")
        success = self.client.login(username=self.user.username, password="Bar")
        self.assertTrue(success)

    def test_profile(self):
        self.assertTrue(isinstance(self.user.profile, UserProfile))

        self.assertEqual(self.user.profile.structure.name, settings.DEFAULT_STRUCTURE_NAME)
        self.assertEqual(self.user.profile.language, settings.LANGUAGE_CODE)

    def test_language(self):
        response = self.client.get(reverse('core:path_list'))
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "Logout")

        # Change user lang
        self.assertNotEqual(settings.LANGUAGE_CODE, "fr")
        userprofile = UserProfile.objects.get(user=self.user)
        userprofile.language = "fr"
        userprofile.save()
        self.assertEqual(self.user.profile.language, "fr")
        # No effect if no logout
        response = self.client.get(reverse('core:path_list'))
        self.assertContains(response, "Logout")

        self.client.logout()

        self.client.login(username=self.user.username, password="Bar")
        response = self.client.get(reverse('core:path_list'))
        self.assertEqual(self.client.session[LANGUAGE_SESSION_KEY], "fr")
        self.assertContains(response, "Déconnexion")

    def test_link_to_adminsite_visible_to_staff(self):
        self.assertTrue(self.user.is_staff)
        response = self.client.get(reverse('core:path_list'))
        self.assertContains(response, '<a href="/admin/">Admin</a>')

    def test_link_to_adminsite_not_visible_to_others(self):
        self.user.is_staff = False
        self.user.save()
        self.client.login(username=self.user.username, password="Bar")
        response = self.client.get(reverse('core:path_list'))
        self.assertNotContains(response, '<a href="/admin/">Admin</a>')
