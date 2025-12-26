import csv
import os
from datetime import datetime

from cities_light.models import City
from django.core.management import BaseCommand
from django.db import transaction

from core.models import Contact, Specialite
from crm.models import Ville


class Command(BaseCommand):
    help = 'Fix cl_map in ville'


    def handle(self, *args, **options):
        nb = 0
        nbs = 0
        err = []
        characters_to_remove = "!()@-./"
        module_dir = os.path.dirname(__file__)  # get current directory
        file_path = os.path.join(module_dir, 'Ville-2022-05-24.tsv')
        with open(file_path) as csvfile:
            readCSV = csv.reader(csvfile, delimiter='\t')
            for row in readCSV:
                try:
                    with transaction.atomic():
                        nb += 1
                        id = row[0]
                        nom = row[1]
                        nom_ar = row[2]
                        latitude = row[3]
                        longitude = row[4]
                        cl_map__geoname_id = row[5]
                        if cl_map__geoname_id:
                            city = City.objects.filter(geoname_id=cl_map__geoname_id).first()
                            if city:
                                ville = Ville.objects.get(id=id)
                                ville.cl_map = city
                                ville.save()
                                nbs += 1
                except Exception as ex:
                    err.append(nb)
                    print("Error %s" % ex)
        self.stdout.write(self.style.SUCCESS('Successfully fix %s cl_map, from %s ' % (nbs, nb)))
        self.stdout.write(self.style.ERROR('Not added %s' % (err)))
