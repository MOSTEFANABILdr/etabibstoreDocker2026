import csv
import os

from django.core.management import BaseCommand
from django.db import transaction

from core.models import CategorieProduit


class Command(BaseCommand):
    help = 'Insert a list of categorie produit from a csv file.'

    def handle(self, *args, **options):
        nb = 0
        nbs = 0
        err = []
        module_dir = os.path.dirname(__file__)  # get current directory
        file_path = os.path.join(module_dir, 'categorie_produit_list.csv')
        with open(file_path) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            for row in readCSV:
                try:
                    with transaction.atomic():
                        nb += 1
                        english = row[0]
                        french = row[1]

                        # create a user
                        categorieAutreProduit = CategorieProduit(
                            titre_en=english,
                            titre_fr=french,
                        )
                        categorieAutreProduit.save()
                        nbs += 1

                except Exception as ex:
                    err.append(nb)
                    print("Error %s" % ex)

        self.stdout.write(self.style.SUCCESS('Successfully added %s categorie_produit,  from %s ' % (nbs, nb)))
        self.stdout.write(self.style.ERROR('Not added %s' % (err)))
