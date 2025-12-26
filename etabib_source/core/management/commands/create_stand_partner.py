import csv
import os

from django.core.management import BaseCommand

from core.models import Partenaire, Stand


class Command(BaseCommand):
    help = 'Create stand for partners'

    def handle(self, *args, **options):
        nb = 0
        nbs = 0
        module_dir = os.path.dirname(__file__)  # get current directory
        file_path = os.path.join(module_dir, 'partners.csv')
        with open(file_path) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            for row in readCSV:
                nom = row[0].strip()
                prenom = row[1].strip()
                username = row[2]
                try:
                    partner = Partenaire.objects.get(user__username=username)
                    partner.user.first_name = nom
                    partner.user.last_name = prenom
                    partner.contact.nom = nom
                    partner.contact.prenom = prenom
                    partner.contact.save()
                    partner.user.save()

                    nb += 1
                    if not Stand.objects.filter(partner=partner).exists():
                        stand = Stand()
                        stand.partner = partner
                        stand.signaletique = "%s %s" % (partner.nom, partner.prenom)
                        print(stand.signaletique)
                        stand.publie = True
                        stand.save()
                        nbs += 1
                except Exception as e:
                    print(e)
        self.stdout.write(self.style.SUCCESS('Successfully added %s Stand,  from %s ' % (nbs, nb)))
