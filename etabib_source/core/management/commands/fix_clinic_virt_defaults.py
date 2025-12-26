from django.core.management import BaseCommand

from clinique.models import CliniqueVirtuelle


class Command(BaseCommand):
    help = 'Set the values of salle_discussion and mot_passe for clinique_virtuelle'

    def handle(self, *args, **options):
        all_cv = CliniqueVirtuelle.objects.all()
        for cv in all_cv:
            if not cv.salle_discussion:
                cv.save()