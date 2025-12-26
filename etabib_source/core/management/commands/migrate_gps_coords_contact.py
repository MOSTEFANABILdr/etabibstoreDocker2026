from django.contrib.gis.geos import Point
from django.core.management import BaseCommand, CommandError

from core.models import Contact
from core.utils import is_number


class Command(BaseCommand):
    help = 'Fix GPS coordinates in contact'

    def handle(self, *args, **options):
        nb = 0
        nba = 0
        try:
            contacts = Contact.objects.all()
            for contact in contacts:
                nb += 1
                if contact.gps:
                    nba += 1
                    contact.save()

                if contact.ville:
                    contact.save()

        except Exception as ex:
            raise CommandError("Error %s" % ex)

        self.stdout.write(self.style.SUCCESS('Successfully Fix GPS coordinates in %s contact from %s' % (nba, nb)))
