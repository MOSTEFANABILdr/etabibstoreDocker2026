import csv
import os

from django.core.management import BaseCommand
from django.db import transaction

from drugs.models import CodeAtc, DciAtc


class Command(BaseCommand):
    help = 'Insert drugs list'

    def handle(self, *args, **options):
        nb = 0
        nbs = 0
        err = []
        module_dir = os.path.dirname(__file__)  # get current directory
        file_path = os.path.join(module_dir, 'add_to_medic.csv')
        with open(file_path) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            for row in readCSV:
                row = [element.strip() if element.strip().upper() not in ["NULL", "NONE"] else "" for element in row]

                try:
                    nc_unique_id= "(select id from `drugs_nomcommercial` where `unique_id` like '%s' limit 1)" % row[0] if row[0] else ""
                    dci_unique_id = "(select id from `drugs_dciatc` where `unique_id` like '%s' limit 1)" % row[2] if row[2] else ""
                    dci_pays = row[4]
                    n_enregistrement = row[5]
                    forme = row[6]
                    dosage = row[7]
                    cond = row[8]
                    liste = row[9]
                    p1 = "0" if row[11] in ["OFF"] else "1" if row[11] in ["H", "HOP", "O"] else "null"
                    p2 =  "0" if row[11] in ["OFF"] else "1" if row[11] in ["H", "HOP", "O"] else "null"
                    obs = row[12]
                    labo = row[13]
                    pays_labo = row[14]
                    type = row[17]
                    status = row[18]
                    duree_stabilite = row[19]
                    date_retrait = row[20]
                    motif_retrait = row[21]
                    etat = "null"
                    unique_id = row[25]
                    form_homogene_id = row[24]

                    sql_row = 'INSERT INTO `drugs_medicament`(`unique_id`, `dci_pays`, `num_enregistrement`, ' \
                              '`forme`, `dosage`, `cond`, `liste`, `p1`, `p2`, `obs`, `laboratoire`, ' \
                              '`type`, `status`, `duree_stabilitee`, `etat`, ' \
                              '`date_retrait`, `motif_retrait`, `pays_labo`, `deleted`, `categorie_id`, `dci_atc_id`, ' \
                              '`forme_homogene_id`, `nom_commercial_id`, `pays_marche`) VALUES ("{}",' \
                              ' "{}", "{}", "{}", "{}", "{}", "{}", {}, {}, "{}",' \
                              ' "{}", "{}", "{}", "{}", {}, "{}", "{}", "{}",' \
                              ' {}, {}, {}, {}, {}, {});'

                    sql_row = sql_row.format(unique_id, dci_pays, n_enregistrement, forme, dosage, cond, liste, p1, p2,
                                   obs, labo, type, status, duree_stabilite, etat, date_retrait, motif_retrait,
                                   pays_labo, 0, 1, dci_unique_id, form_homogene_id, nc_unique_id, 204)

                    print(sql_row)


                except Exception as ex:
                    err.append(nb)
                    print("Error %s" % ex)
        self.stdout.write(self.style.SUCCESS('Successfully added %s ,  from %s ' % (nbs, nb)))
        self.stdout.write(self.style.ERROR('Not added %s' % (err)))
