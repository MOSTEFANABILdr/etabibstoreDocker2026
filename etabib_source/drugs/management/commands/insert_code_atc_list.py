import csv
import os

from django.core.management import BaseCommand
from django.db import transaction

from drugs.models import CodeAtc, DciAtc


class Command(BaseCommand):
    help = 'Insert code atc list'

    def handle(self, *args, **options):
        nb = 0
        nbs = 0
        err = []
        module_dir = os.path.dirname(__file__)  # get current directory
        file_path = os.path.join(module_dir, 'code_atc.csv')
        with open(file_path) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            for row in readCSV:
                row = [element.strip() for element in row]
                try:
                    with transaction.atomic():
                        nb += 1
                        id = row[0]
                        designation = row[1] if row[1] not in ("NULL", r"\N") else None

                        ddd = row[3] if row[3] not in ("NULL", r"\N") else None
                        ddu = row[4] if row[4] not in ("NULL", r"\N") else None
                        ti = row[5] if row[5] not in ("NULL", r"\N") else None
                        intro = row[6] if row[6] not in ("NULL", r"\N") else None
                        narcotic = row[7] if row[7] not in ("NULL", r"\N") else None
                        deleted = row[8] if row[8] not in ("NULL", r"\N") else None
                        unique_id = row[9] if row[9] not in ("NULL", r"\N") else None
                        link = row[10] if row[10] not in ("NULL", r"\N") else None
                        dci_atc_unique_id = row[11] if row[11] not in ("NULL", r"\N") else None

                        dciatc = None
                        if dci_atc_unique_id:
                            dciatc = DciAtc.objects.get(unique_id=dci_atc_unique_id)

                        code = CodeAtc()
                        code.designation = designation
                        code.ddd = float(ddd) if ddd else None
                        code.ddu = ddu
                        code.ti = ti
                        code.intro = intro
                        code.narcotic = int(narcotic) if narcotic else None
                        code.unique_id = unique_id
                        code.link = link
                        code.deleted = True if deleted == "1" else False if deleted == "0" else False
                        code.dciAtc = dciatc
                        code.save()

                        nbs += 1
                except Exception as ex:
                    err.append(nb)
                    print("Error %s" % ex)
                    print(dci_atc_unique_id)
        self.stdout.write(self.style.SUCCESS('Successfully added %s code atc,  from %s ' % (nbs, nb)))
        self.stdout.write(self.style.ERROR('Not added %s' % (err)))
