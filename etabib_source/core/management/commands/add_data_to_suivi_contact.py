from django.core.management import BaseCommand, CommandError

from core.models import Contact, Suivi


class Command(BaseCommand):
    help = 'Add data to suivi contact'

    def handle(self, *args, **options):
        nb = 0
        nba = 0
        try:
            contacts = Contact.objects.all()
            for contact in contacts:
                nb += 1
                actions = contact.action_set.exclude(type__in=["3", "4", "5"])
                if actions.exists():
                    lastAction = actions.latest('id')
                    if lastAction.type== "2": #suivi ponctuel
                        #Add it to ListeSuivi table
                        nba += 1
                        sc = Suivi()
                        sc.contact = contact
                        sc.cree_par = lastAction.cree_par
                        sc.save()
                        sc.date_creation = lastAction.date_creation
                        sc.save()

        except Exception as ex:
            raise CommandError("Error %s" % ex)

        self.stdout.write(self.style.SUCCESS('Successfully add %s contact to ListeSuivi from %s' % (nba, nb)))