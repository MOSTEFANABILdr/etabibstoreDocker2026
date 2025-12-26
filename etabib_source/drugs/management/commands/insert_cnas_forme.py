import csv
import os

from django.core.management import BaseCommand

from drugs.models import MedicamentCnasForme


class Command(BaseCommand):
    help = 'Insert Cnas forme'

    def handle(self, *args, **options):
        nb = 0
        nbs = 0
        err = []
        module_dir = os.path.dirname(__file__)  # get current directory
        file_path = os.path.join(module_dir, 'forme_cnas.csv')
        with open(file_path) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            for row in readCSV:
                row = [element.strip() if element.strip().upper() not in ["NULL", "NONE"] else "" for element in row]
                nb += 1
                #ID,CODE_FORME,LIBELLE,LIBELLE_COURT
                try:
                    code = row[1]
                    libelle = row[2]
                    libelle_court = row[3]

                    forme = MedicamentCnasForme()
                    forme.libelle = libelle
                    forme.libelle_court = libelle_court
                    forme.code = code
                    forme.save()

                    nbs += 1
                except Exception as ex:
                    err.append(nb)
                    print("Error %s" % ex)
        self.stdout.write(self.style.SUCCESS('Successfully added %s ,  from %s ' % (nbs, nb)))
        self.stdout.write(self.style.ERROR('Not added %s' % (err)))
