from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from faenet.chat.models import ChatRoom


ROOMS = [
    {
        "name": "The Moonlit Grove",
        "description": "A serene clearing bathed in eternal moonlight. Whisper your secrets to the ancient oaks.",
    },
    {
        "name": "Thornwick Tavern",
        "description": "A lively gathering place where faeries trade tales over dewdrop ale and mushroom stew.",
    },
    {
        "name": "The Whispering Hollow",
        "description": "A hidden vale where the wind carries messages between realms. Speak softly, and be heard.",
    },
]


class Command(BaseCommand):
    help = "Seed the database with default chat rooms"

    def handle(self, *args, **options):
        # Use the first available user as creator, or None
        creator = User.objects.first()

        for room_data in ROOMS:
            room, created = ChatRoom.objects.get_or_create(
                name=room_data["name"],
                defaults={
                    "description": room_data["description"],
                    "created_by": creator,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created room: {room.name}"))
            else:
                self.stdout.write(f"Room already exists: {room.name}")
