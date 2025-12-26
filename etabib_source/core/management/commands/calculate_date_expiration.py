import datetime

from django.core.management import BaseCommand, CommandError
from django.utils import timezone

from core.models import Medecin, CarteProfessionnelle, Action, Facture_OffrePrep_Licence


class Command(BaseCommand):
    help = 'Calculate date expiration'

    def handle(self, *args, **options):
        try:
            nb = 0
            fols = Facture_OffrePrep_Licence.objects.all()
            for fol in fols:
                nb += 1
                fol.save()
        except Exception as ex:
            raise CommandError("Error %s" % ex)

        self.stdout.write(self.style.SUCCESS('Successfully setting date expiration %s') % (nb))