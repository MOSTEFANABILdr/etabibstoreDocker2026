from django.core.management import BaseCommand
from django.db.models import Q

from core.models import Contact
from crm.models import Ville


class Command(BaseCommand):
    help = 'Map ville in contacts'

    def handle(self, *args, **options):
        nb = nbs = 0
        contacts = Contact.objects.all()
        cities = set()
        for contact in contacts:
            nb += 1
            if contact.pays:
                if contact.pays.id == 62:
                    contact.pays_n_id = 1
            if contact.ville:
                if Ville.objects.filter(
                        Q(cl_map__geoname_id =contact.ville.geoname_id) | Q(cl_map__name_ascii =contact.ville.name_ascii)
                ).exists():
                    pass
                else:
                    cities.add(contact.ville)
                nbs += 1

        for city in cities:
            # if city.country.id == 62:
            print(f'{city.id} {city.name} {city.region}')
        self.stdout.write(self.style.SUCCESS('Villes %s ' % (len(cities))))
        self.stdout.write(self.style.SUCCESS('Successfully fix %s cities, from %s ' % (nbs, nb)))