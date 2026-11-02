"""Create the site login from environment variables on first deploy.

Set ADMIN_USERNAME and ADMIN_PASSWORD (and optionally ADMIN_EMAIL) as Railway variables.
Safe to run on every deploy: it never changes an existing user's password, and it does
nothing when the variables aren't set — so you can delete ADMIN_PASSWORD afterwards.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from config.env import env


class Command(BaseCommand):
    help = "Create the admin login from ADMIN_USERNAME / ADMIN_PASSWORD if it doesn't exist yet."

    def handle(self, *args, **options):
        username = env("ADMIN_USERNAME", default="")
        password = env("ADMIN_PASSWORD", default="")
        if not (username and password):
            self.stdout.write("ADMIN_USERNAME / ADMIN_PASSWORD not set — skipping.")
            return

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"User '{username}' already exists — leaving it alone.")
            return

        User.objects.create_superuser(username=username, email=env("ADMIN_EMAIL", default=""), password=password)
        self.stdout.write(self.style.SUCCESS(f"Created admin user '{username}'."))
