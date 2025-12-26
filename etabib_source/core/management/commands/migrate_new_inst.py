import csv
import datetime
import os

import pytz
from django.core.management import BaseCommand, CommandError

from core.models import Medecin, Poste, OffrePrepaye, Licence, Facture_OffrePrep_Licence, Facture


class Command(BaseCommand):
    help = 'migrate new inst'

    def handle(self, *args, **options):
        nb = 0
        nba = 0
        nbb = 0
        err = []
        module_dir = os.path.dirname(__file__)  # get current directory
        file_path = os.path.join(module_dir, 'new_inst.csv')
        with open(file_path) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            for row in readCSV:
                try:
                    nb += 1
                    libelle = row[0]
                    old_mac = row[1]
                    clef = row[2]
                    act_date = row[3]
                    fol= None

                    if clef:
                        licence = Licence.objects.get(clef=clef)
                        if licence:
                            if not hasattr(licence, "poste"):
                                if act_date:
                                    date_time_obj = datetime.datetime.strptime(act_date, "%Y-%m-%d %H:%M:%S")
                                    tz = pytz.timezone('Africa/Algiers')
                                    date_time_obj = date_time_obj.replace(tzinfo=tz)
                                    licence.date_actiavtion_licence = date_time_obj
                                fol = Facture_OffrePrep_Licence.objects.get(licence=licence)
                                if fol:
                                    poste  = Poste()
                                    poste.libelle = libelle
                                    poste.medecin = fol.facture.medecin
                                    poste.old_mac = old_mac
                                    poste.points = fol.offre.points
                                    poste.licence = licence
                                    poste.save()
                                    nba +=1
                            else:
                                fol = Facture_OffrePrep_Licence.objects.get(licence=licence)
                                poste = licence.poste
                                poste.old_mac = old_mac
                                poste.medecin = fol.facture.medecin
                                poste.libelle = libelle
                                poste.points = fol.offre.points
                                poste.save()
                                nbb +=1

                except Exception as ex:
                    err.append(nb)
                    print("Error %s" % ex)
        self.stdout.write(
            self.style.SUCCESS('Successfully add %s postes, update %s postes,  from %s ' % (nba, nbb, nb)))
        self.stdout.write(self.style.ERROR('Not added %s' % (err)))
