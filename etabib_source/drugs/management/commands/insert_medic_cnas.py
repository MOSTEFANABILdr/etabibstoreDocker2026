import csv
import os

from django.core.management import BaseCommand
from django.db import transaction

from drugs.models import CodeAtc, DciAtc, MedicamentCnas


class Command(BaseCommand):
    help = 'Insert Map Cnas'

    def handle(self, *args, **options):
        nb = 0
        nbs = 0
        err = []
        module_dir = os.path.dirname(__file__)  # get current directory
        file_path = os.path.join(module_dir, 'medicament_cnas.csv')
        with open(file_path) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            for row in readCSV:
                row = [element.strip() if element.strip().upper() not in ["NULL", "NONE"] else None for element in row]
                nb += 1
                try:
                    n_enregistrement = row[1]
                    nom_commercial = row[2]
                    nom_dci = row[3]
                    dosage = row[4]
                    unite = row[5]
                    conditionnement = row[6]
                    convention = row[7]
                    remboursable = row[8]
                    date_remboursement = row[9]
                    date_arret_remboursement = row[10]
                    date_decision =  row[11]
                    tarif_de_reference =  row[12]
                    taux =  row[13]
                    forme =  row[14]
                    tableau =  row[15]
                    hopital =  row[16]
                    secteur_sanitair =  row[17]
                    officine = row[18]
                    pays = row[19]
                    laboratoire = row[20]
                    cm = row[21]
                    code_medic = row[22]
                    date_tr = row[23]
                    observation = row[24]
                    code_dci = row[25]
                    inf_tr = row[26]
                    generic = row[27]

                    medic = MedicamentCnas()
                    medic.n_enregistrement = n_enregistrement
                    medic.nom_dci = nom_dci
                    medic.nom_commercial = nom_commercial
                    medic.dosage = dosage
                    medic.unite = unite
                    medic.conditionnement =conditionnement
                    medic.convention = convention
                    medic.remboursable = remboursable
                    medic.date_remboursement = date_remboursement
                    medic.date_arret_remboursement = date_arret_remboursement
                    medic.date_decision = date_decision
                    medic.tarif_de_reference = tarif_de_reference
                    medic.taux = taux
                    medic.forme = forme
                    medic.tableau = tableau
                    medic.hopital = hopital
                    medic.secteur_sanitaire = secteur_sanitair
                    medic.officine = officine
                    medic.pays = pays
                    medic.laboratoire = laboratoire
                    medic.cm = cm
                    medic.code_medic = code_medic
                    medic.date_tr = date_tr
                    medic.observation = observation
                    medic.code_dci = code_dci
                    medic.inf_tr = inf_tr
                    medic.generic = generic
                    medic.save()
                    nbs += 1

                except Exception as ex:
                    err.append(nb)
                    print("Error %s" % ex)
        self.stdout.write(self.style.SUCCESS('Successfully added %s ,  from %s ' % (nbs, nb)))
        self.stdout.write(self.style.ERROR('Not added %s' % (err)))
