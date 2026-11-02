import os
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase


class EnsureAdminTests(TestCase):
    def run_command(self, **env):
        with mock.patch.dict(os.environ, env, clear=False):
            out = StringIO()
            call_command("ensure_admin", stdout=out)
            return out.getvalue()

    def test_skips_when_variables_missing(self):
        with mock.patch.dict(os.environ, {"ADMIN_USERNAME": "", "ADMIN_PASSWORD": ""}):
            self.assertIn("skipping", self.run_command())
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_creates_superuser_who_can_log_in(self):
        self.run_command(ADMIN_USERNAME="owner", ADMIN_PASSWORD="s3cret-pass!")
        user = get_user_model().objects.get(username="owner")
        self.assertTrue(user.is_superuser and user.is_staff)
        self.assertTrue(self.client.login(username="owner", password="s3cret-pass!"))

    def test_never_overwrites_an_existing_users_password(self):
        get_user_model().objects.create_superuser("owner", password="original-pass")
        self.assertIn("already exists", self.run_command(ADMIN_USERNAME="owner", ADMIN_PASSWORD="changed-pass"))
        self.assertTrue(self.client.login(username="owner", password="original-pass"))
