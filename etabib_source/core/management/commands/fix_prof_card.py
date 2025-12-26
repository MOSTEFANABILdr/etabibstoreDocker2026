from django.core.management import BaseCommand, CommandError

from core.models import Medecin, CarteProfessionnelle


class Command(BaseCommand):
    help = 'Add for every medecin a professional card if needed'

    def handle(self, *args, **options):
        nb = 0
        nba = 0
        try:
            medecins  = Medecin.objects.filter(carte=None)
            for medecin in medecins:
                if medecin.contact:
                    if medecin.contact.carte:
                        cp = CarteProfessionnelle()
                        cp.image = medecin.contact.carte
                        cp.checked = True
                        cp.save()
                        medecin.carte = cp
                        medecin.save()
                        nb = nb + 1
                    else:
                        cp = CarteProfessionnelle()
                        cp.checked = True
                        cp.save()
                        medecin.carte = cp
                        medecin.save()
                        nba = nba + 1
        except Exception as ex:
            raise CommandError("Error %s" % ex)

        self.stdout.write(self.style.SUCCESS('Successfully added %s cards, %s default cards ' % (nb, nba)))