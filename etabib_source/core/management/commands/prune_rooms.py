from django.core.management import BaseCommand

from teleconsultation.models import Room


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        Room.objects.prune_rooms()