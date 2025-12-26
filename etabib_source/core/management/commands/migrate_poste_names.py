import csv
import datetime
import os

from django.core.management import BaseCommand, CommandError

from core.models import Medecin, Poste, OffrePrepaye, Licence, Facture_OffrePrep_Licence, Facture


class Command(BaseCommand):
    help = 'migrate old poste names'

    def handle(self, *args, **options):
        nb = 0
        nba = 0
        err = []
        try:
            module_dir = os.path.dirname(__file__)  # get current directory
            file_path = os.path.join(module_dir, 'old_poste_names.csv')
            with open(file_path) as csvfile:
                readCSV = csv.reader(csvfile, delimiter=',')
                for row in readCSV:
                    nb += 1
                    libelle = row[0]
                    old_mac = row[1]

                    if old_mac:
                        try:
                            poste = Poste.objects.get(old_mac=old_mac)
                            poste.libelle = libelle
                            poste.save()
                            nba += 1
                        except Exception as e:
                            if not isinstance(e,Poste.DoesNotExist):
                                err.append(nb)
                            print("Error: %s" % e)

        except Exception as ex:
            err.append(nb)
            print("Error %s" % ex)

        self.stdout.write(
            self.style.SUCCESS('Successfully update %s postes, from %s ' % (nba, nb)))
        self.stdout.write(self.style.SUCCESS('Not added %s' % (err)))
