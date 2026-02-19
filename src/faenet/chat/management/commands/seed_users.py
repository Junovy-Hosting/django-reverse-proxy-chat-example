from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


USERS = [
    {
        "username": "admin",
        "first_name": "Admin",
        "last_name": "Fae",
        "is_staff": True,
        "is_superuser": True,
    },
    {"username": "titania", "first_name": "Titania", "last_name": "Moonweaver"},
    {"username": "oberon", "first_name": "Oberon", "last_name": "Shadowthorn"},
    {"username": "puck", "first_name": "Puck", "last_name": "Trickfoot"},
    {"username": "morgana", "first_name": "Morgana", "last_name": "Mistbloom"},
    {"username": "thistle", "first_name": "Thistle", "last_name": "Duskwing"},
    {"username": "bramble", "first_name": "Bramble", "last_name": "Thornheart"},
    {"username": "luna", "first_name": "Luna", "last_name": "Starfire"},
    {"username": "fern", "first_name": "Fern", "last_name": "Dewdrop"},
    {"username": "cobweb", "first_name": "Cobweb", "last_name": "Silkspinner"},
    {"username": "mustardseed", "first_name": "Mustardseed", "last_name": "Goldenleaf"},
    {
        "username": "omni",
        "first_name": "Omni",
        "last_name": "Voidwalker",
        "password": "omnifae42",
    },
]

DEFAULT_PASSWORD = "faerie123"


class Command(BaseCommand):
    help = "Seed the database with faerie users"

    def handle(self, *args, **options):
        for user_data in USERS:
            username = user_data["username"]
            is_staff = user_data.pop("is_staff", False)
            is_superuser = user_data.pop("is_superuser", False)
            password = user_data.pop("password", DEFAULT_PASSWORD)

            user, created = User.objects.get_or_create(
                username=username,
                defaults=user_data,
            )

            if created:
                user.is_staff = is_staff
                user.is_superuser = is_superuser
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created user: {username}"))
            else:
                self.stdout.write(f"User already exists: {username}")
