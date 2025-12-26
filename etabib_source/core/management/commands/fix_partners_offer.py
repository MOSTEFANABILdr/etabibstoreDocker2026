from django.core.management import BaseCommand, CommandError
from django.db import transaction

from core.models import Partenaire, OffrePartenaire, Facture, Facture_Offre_Partenaire


class Command(BaseCommand):
    help = "Fix Partners Offer"

    def handle(self, *args, **options):
        nb = 0
        nba = 0
        try:
            partners = Partenaire.objects.all()
            for partner in partners:
                if partner.facture_set.count() == 0:
                    with transaction.atomic():
                        nb += 1
                        offre = OffrePartenaire.objects.get(id=1)

                        facture = Facture()
                        partner.points = offre.points
                        partner.save()
                        facture.partenaire = partner
                        facture.total = float(offre.prix.amount)

                        facture.save()

                        fop = Facture_Offre_Partenaire()
                        fop.offre = offre
                        fop.facture = facture
                        fop.save()
                        nba += 1

        except Exception as ex:
            raise CommandError("Error %s" % ex)

        self.stdout.write(self.style.SUCCESS('Successfully Fix specialitie in %s contact from %s' % (nba, nb)))