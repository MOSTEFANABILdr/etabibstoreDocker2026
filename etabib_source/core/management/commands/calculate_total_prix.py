import datetime

from django.core.management import BaseCommand, CommandError
from pytz import timezone

from core.models import Facture


class Command(BaseCommand):
    help = 'Calculate total_prix'

    def handle(self, *args, **options):
        try:
            nb = 0
            nba = 0
            nbb = 0
            localtz = timezone('Africa/Algiers')
            factures = Facture.objects.all()
            for facture in factures:
                nb += 1
                fol = facture.fol_facture_set.first()
                #Fixing date_creation
                if facture.date_creation.date() == datetime.datetime(2020, 1, 5).date():
                    if fol.licence:
                       if fol.licence.date_actiavtion_licence:
                           facture.date_creation = fol.licence.date_actiavtion_licence

                if facture.date_creation < localtz.localize(datetime.datetime(2019, 1, 1)):
                    facture.tva = 0
                    nbb += 1
                elif facture.date_creation >= localtz.localize(datetime.datetime(2019, 1, 1)):
                    facture.tva = 19
                    nba += 1
                facture.save()
        except Exception as ex:
            raise CommandError("Error %s" % ex)

        self.stdout.write(self.style.SUCCESS('Successfully calculate total_prix %s') % (nb))
        self.stdout.write(self.style.SUCCESS('Successfully calculate total_prix wit tva  %s') % (nba))
        self.stdout.write(self.style.SUCCESS('Successfully calculate total_prix without tva  %s') % (nbb))