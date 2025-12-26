from django.core.management import BaseCommand, CommandError

from core.models import Medecin, CarteProfessionnelle, Action


class Command(BaseCommand):
    help = 'Fix end date in action'

    def handle(self, *args, **options):
        try:
            actions = Action.objects.all()
            for action in actions:
                for detail in action.detail_set.all():
                    if hasattr(detail, 'prochainerencontre'):
                        if detail.prochainerencontre.date_rencontre > action.date_fin:
                            action.date_fin = detail.prochainerencontre.date_rencontre
                            action.save()
        except Exception as ex:
            raise CommandError("Error %s" % ex)

        self.stdout.write(self.style.SUCCESS('Successfully Fix end date in action '))