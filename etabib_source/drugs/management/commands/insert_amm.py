import csv
import os

from django.core.management import BaseCommand

from drugs.models import Amm, Medicament


class Command(BaseCommand):
    help = 'Insert Amm'

    def handle(self, *args, **options):
        nb = 0
        nbs = 0
        err = []
        module_dir = os.path.dirname(__file__)  # get current directory
        file_path = os.path.join(module_dir, 'maj_amm.csv')
        with open(file_path) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            for row in readCSV:
                row = [element.strip() if element.strip().upper() not in ["NULL", "NONE"] else "" for element in row]
                nb += 1

                try:
                    unique_id = row[0]
                    amm = row[1]
                    date_retrait = row[2]
                    motif_retrait = row[3]

                    ammObj = Amm()
                    ammObj.medicament = Medicament.objects.get(unique_id=unique_id)
                    ammObj.amm = amm
                    ammObj.date_retrait = date_retrait
                    ammObj.motif_retrait = motif_retrait
                    ammObj.save()
                    nbs += 1
                except Exception as ex:
                    err.append(nb)
                    print("Error %s" % ex)
        self.stdout.write(self.style.SUCCESS('Successfully added %s ,  from %s ' % (nbs, nb)))
        self.stdout.write(self.style.ERROR('Not added %s' % (err)))
