from django.core.management import BaseCommand, CommandError
from django.db.models import signals

from core.models import Contact, Poste, Medecin
from core.signals import pre_save_medecin


class Command(BaseCommand):
    help = 'Fix specialities in contact'

    def handle(self, *args, **options):
            nb = 0
            try:
                postes = Poste.objects.all()
                signals.pre_save.disconnect(pre_save_medecin, sender=Medecin)
                for poste in postes:
                    nb += 1
                    medecin = poste.medecin
                    medecin.points += poste.points
                    medecin.save()
            except Exception as ex:
                raise CommandError("Error %s" % ex)
            signals.pre_save.connect(pre_save_medecin, sender=Medecin)
            self.stdout.write(self.style.SUCCESS('Successfully Fix points in %s postes' % (nb)))