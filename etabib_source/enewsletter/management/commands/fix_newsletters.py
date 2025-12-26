import logging

from django.core.management import BaseCommand, CommandError
from django.utils.translation import gettext as _

from enewsletter.models import Newsletter


class Command(BaseCommand):
    help = _("Fix newsletter")

    def handle(self, *args, **options):
        # Newsletter.submit_queue()
        nb = 0
        try:
            arr = {
                "Inscription": "1",
                "Validation": "2",
                "Connexion": "3",
                "Inscrit mais n'a pas choisi de profil paient": "4",
                "Inscrit médecin mais pas activé": "5",
                "Expiration de l'abonnement": "6",
            }
            news = Newsletter.objects.all()
            for nw in news:
                nb += 1
                print(nw.criteria)
                if nw.criteria in arr:
                    nw.criteria = arr[nw.criteria]
                nw.save()
        except Exception as ex:
            raise CommandError("Error %s" % ex)
        self.stdout.write(self.style.SUCCESS('Successfully Fix  %s newsletters' % (nb)))
