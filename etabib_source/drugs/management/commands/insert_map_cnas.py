import csv
import os

from django.core.management import BaseCommand
from django.db import transaction

from drugs.models import CodeAtc, DciAtc, MapCnas, Medicament, MedicamentCnas


class Command(BaseCommand):
    help = 'Insert Map Cnas'

    def handle(self, *args, **options):
        nb = 0
        nbs = 0
        module_dir = os.path.dirname(__file__)  # get current directory
        file_path = os.path.join(module_dir, 'map_cnas.csv')
        with open(file_path) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            for row in readCSV:
                row = [element.strip() if element.strip().upper() not in ["NULL", "NONE"] else None for element in row]
                nb += 1
                try:
                    cnas_id = row[0]
                    medic_id = row[1]

                    map = MapCnas()
                    medic = Medicament.objects.get(unique_id=medic_id)
                    medicCnas = MedicamentCnas.objects.get(n_enregistrement=cnas_id)

                    map.medicament = medic
                    map.medicamentcnas = medicCnas
                    map.save()

                    nbs += 1
                except Exception as ex:
                    pass

        self.stdout.write(self.style.SUCCESS('Successfully added %s ,  from %s ' % (nbs, nb)))
        self.stdout.write(self.style.ERROR('Not added %s' % (nb - nbs)))
