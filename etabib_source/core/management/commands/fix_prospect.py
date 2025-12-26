from django.core.management import BaseCommand, CommandError
from django.db import transaction

from core.models import Prospect, ListeProspect


class Command(BaseCommand):
    help = 'Fix prospect Model'

    def handle(self, *args, **options):
        try:
            nbp = 0
            nba = 0
            prospects = Prospect.objects.all()
            with transaction.atomic():
                for prospect in prospects:
                    nbp += 1
                    if not prospect.liste and prospect.cree_par:
                        if prospect.cree_par.liste_prospect.count() == 0:
                            pl = ListeProspect()
                            pl.cree_par = prospect.cree_par
                            pl.traite = True
                            pl.save()
                        else:
                            pl = prospect.cree_par.liste_prospect.first()

                        prospect.liste = pl
                        prospect.save()
                        nba += 1
        except Exception as ex:
            raise CommandError("Error %s" % ex)

        self.stdout.write(self.style.SUCCESS('Fixe: %s') % nba)
        self.stdout.write(self.style.SUCCESS('From: %s') % nbp)
