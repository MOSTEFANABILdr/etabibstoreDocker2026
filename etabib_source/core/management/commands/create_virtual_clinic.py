import csv
import os

from django.core.management import BaseCommand

from clinique.models import CliniqueVirtuelle, CliniqueVirtuelleImage
from core.models import Partenaire, Stand, Contact


class Command(BaseCommand):
    help = 'Create CliniqueVirtuelle for clients'

    def handle(self, *args, **options):
        nb = 0
        nbs = 0
        clients = Contact.objects.filter(medecin__isnull=False).exclude(medecin__postes__isnull=True).order_by("id")
        for client in clients:
            nb += 1
            if client.full_name and client.full_name.strip():
                if hasattr(client.medecin.user, "cliniquevirtuelle"):
                    cv = client.medecin.user.cliniquevirtuelle
                    print("hererer")
                else:
                    cv = CliniqueVirtuelle()
                if not hasattr(cv, "user"):
                    cv.user = client.medecin.user
                if not cv.ville:
                    cv.ville = client.ville
                if not cv.pays:
                    cv.pays = client.pays
                if not cv.titre:
                    cv.titre = "Clinique du DR {}".format(client.full_name)
                if not cv.image:
                    cv.image = CliniqueVirtuelleImage.objects.filter(default=True).first()
                cv.save()
                nbs += 1
        self.stdout.write(self.style.SUCCESS('Successfully added %s CliniqueVirtuelle,  from %s ' % (nbs, nb)))
