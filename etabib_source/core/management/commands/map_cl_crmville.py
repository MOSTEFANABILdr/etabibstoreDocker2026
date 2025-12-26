from cities_light.models import City
from django.core.management import BaseCommand

from crm.models import Ville


class Command(BaseCommand):
    help = 'Map City_light_city to Ville'

    def handle(self, *args, **options):
        dz_cities = City.objects.filter(country_id=62)
        dz_ville = Ville.objects.filter(pays__id=1)
        for ville in dz_ville:
            map = dz_cities.filter(name_ascii=ville.nom)
            if len(map) == 0:
                map = dz_cities.filter(name_ascii=str(ville.nom).replace(" ", "-"))

            if len(map) == 1:
                ville.cl_map = map[0]
                ville.save()
