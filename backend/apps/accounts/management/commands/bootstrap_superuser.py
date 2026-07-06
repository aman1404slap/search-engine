import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Create/update the superadmin from DJANGO_SUPERUSER_USERNAME/EMAIL/"
        "PASSWORD env vars (idempotent -- safe to run on every deploy; "
        "resets the password to match the env var each time)."
    )

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")

        if not username or not password:
            self.stderr.write(
                self.style.WARNING(
                    "DJANGO_SUPERUSER_USERNAME/PASSWORD not set, skipping superadmin bootstrap"
                )
            )
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        self.stdout.write(
            self.style.SUCCESS(f"Superadmin '{username}' {'created' if created else 'updated'}.")
        )
