from django.core.management import BaseCommand, CommandError

from econgre.models import UserParticipationWebinar


class Command(BaseCommand):
    help = 'Fix UserParticipationWebinar data'

    def handle(self, *args, **options):
        try:
            entries = UserParticipationWebinar.objects.all()
            nb = 0
            for entry in entries:
                entry.user = entry.medecin.user
                nb += 1
                entry.save()
        except Exception as ex:
            raise CommandError("Error %s" % ex)

        self.stdout.write(self.style.SUCCESS('Successfully %s UserParticipationWebinar data' % nb))