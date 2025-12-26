from django.core.management import BaseCommand, CommandError

from core.models import OffrePrepaye


class Command(BaseCommand):
    help = 'Fix Offers'
    def handle(self, *args, **options):
        try:
            nb = 0
            na = 0
            nc = 0
            offers = OffrePrepaye.objects.all()
            for offer in offers:
                na += 1
                if offer.prix > 0:
                    offer.services = ("1", "2", "3", "4", "5", "6", "7", "8")
                    offer.save()
                    nc += 1
        except Exception as ex:
            raise CommandError("Error %s" % ex)

        self.stdout.write(self.style.SUCCESS('Successfully Fix %s offers from %s' % (nc, na)))