import csv
import datetime
import os

import pytz
from django.core.management import BaseCommand, CommandError

from core.models import Medecin, Poste, OffrePrepaye, Licence, Facture_OffrePrep_Licence, Facture


class Command(BaseCommand):
    help = 'migrate old data'

    def handle(self, *args, **options):
        nb = 0
        nbl = 0
        nba = 0
        nbo = 0
        err = []
        module_dir = os.path.dirname(__file__)  # get current directory
        file_path = os.path.join(module_dir, 'old-data.csv')
        with open(file_path) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            next(readCSV, None)  # skip the headers
            for row in readCSV:
                try:
                    nb += 1
                    username = row[0]
                    name = row[2]
                    clef = row[8]
                    offer_id = row[9]
                    act_date = row[10]
                    old_mac = row[11]

                    offre = None
                    licence = None

                    if clef:
                        licence = Licence()
                        licence.clef = clef
                        if act_date:
                            date_time_obj = datetime.datetime.strptime(act_date, "%B %d, %Y %H:%M")
                            tz = pytz.timezone('Africa/Algiers')
                            date_time_obj = date_time_obj.replace(tzinfo=tz)
                            licence.date_actiavtion_licence = date_time_obj
                        licence.save()
                        nbl += 1

                    if offer_id:
                        try:
                            offre = OffrePrepaye.objects.get(id=offer_id)
                        except Exception as e:
                            print("Error rr %s " % e)

                    if username:
                        try:
                            medecin = Medecin.objects.get(user__username=username)

                            if (offre and name) or (offre and old_mac):
                                facture = Facture()
                                facture.medecin = medecin
                                facture.commercial = None
                                facture.total = offre.prix
                                facture.save()

                                fol = Facture_OffrePrep_Licence()
                                fol.licence = licence
                                fol.offre = offre
                                fol.facture = facture
                                fol.save()

                                nbo += 1

                                if old_mac:
                                    poste = Poste()
                                    poste.libelle = "TEST"  # TODO
                                    poste.medecin = medecin
                                    poste.old_mac = old_mac
                                    poste.sid = None
                                    poste.points = offre.points
                                    poste.licence = licence
                                    poste.save()
                                    nba += 1
                        except Exception as e:
                            print("Error %s does not exists in medecin table %s" % (username, e))
                except Exception as ex:
                    err.append(nb)
                    print("Error %s" % ex)

        self.stdout.write(
            self.style.SUCCESS('Successfully added %s Licenses, %s offres,  %s postes, from %s ' % (nbl, nbo, nba, nb)))
        self.stdout.write(self.style.SUCCESS('Not added %s' % (err)))
