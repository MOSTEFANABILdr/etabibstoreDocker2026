from django.core.management import BaseCommand, CommandError
from django.db import transaction

from appointements.models import DemandeRendezVous


class Command(BaseCommand):
    help = 'Fix demande RDV data'

    def handle(self, *args, **options):
        try:
            nbp = 0
            drdvs = DemandeRendezVous.objects.all()
            with transaction.atomic():
                for drdv in drdvs:
                    nbp += 1
                    drdv.demandeur = drdv.patient.user
                    drdv.destinataire = drdv.medecin.user
                    drdv.save()
        except Exception as ex:
            raise CommandError("Error %s" % ex)

        self.stdout.write(self.style.SUCCESS('RDV fixed: %s') % nbp)
