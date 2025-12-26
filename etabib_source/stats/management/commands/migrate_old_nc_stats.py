import csv
import os
from datetime import datetime

import pytz
from django.core.management import BaseCommand, CommandError

from core.models import Medecin, Poste, OffrePrepaye, Licence, Facture_OffrePrep_Licence, Facture
from drugs.models import NomCommercial
from stats.models import NomComercialStats


class Command(BaseCommand):
    help = 'migrate old nom commercial statistics'

    def handle(self, *args, **options):
        nb = 0
        nba = 0
        err = 0
        row_count= 0
        try:
            module_dir = os.path.dirname(__file__)  # get current directory
            file_path = os.path.join(module_dir, 'ncstats.csv')
            with open(file_path) as csvfile:
                readCSV = csv.reader(csvfile, delimiter=',')
                row_count = sum(1 for row in readCSV)

            with open(file_path) as csvfile:
                readCSV = csv.reader(csvfile, delimiter=',')
                milestones = [15, 30, 45, 60, 75, 90, 100]
                for row in readCSV:
                    nb += 1
                    id = row[0]
                    unique_id = row[1]
                    mac = row[2]
                    date = row[3]


                    try:
                        poste = Poste.objects.get(old_mac=mac)
                        nc = NomCommercial.objects.get(unique_id=unique_id)
                        d = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                        tz = pytz.timezone('Africa/Algiers')
                        d = d.replace(tzinfo=tz)

                        ncs = NomComercialStats()
                        ncs.nomCommercial = nc
                        ncs.poste = poste
                        ncs.date_insertion = d
                        ncs.save()

                        nba += 1
                    except Exception as e:
                        err += 1

                    percentage_complete = (100.0 * (nb + 1) / row_count)
                    while len(milestones) > 0 and percentage_complete >= milestones[0]:
                        print("{}% complete".format(milestones[0]))
                        milestones = milestones[1:]

        except Exception as ex:
            err += 1
            print("Error %s" % ex)

        self.stdout.write(self.style.SUCCESS('Successfully added %s lines, from %s ' % (nba, nb)))
        self.stdout.write(self.style.SUCCESS('Not added %s' % (err)))
