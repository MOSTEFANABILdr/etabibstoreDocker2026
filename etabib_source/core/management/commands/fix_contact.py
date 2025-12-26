from django.core.management import BaseCommand, CommandError

from core.models import Contact


class Command(BaseCommand):
    help = 'Fix specialities in contact'

    def handle(self, *args, **options):
            nb = 0
            nba = 0
            try:
                contacts = Contact.objects.all()
                for contact in contacts:
                    nb += 1
                    if hasattr(contact, "specialites"):
                        spec = contact.specialites.first()
                        if spec:
                            nba += 1
                            contact.specialite = spec
                            contact.save()

            except Exception as ex:
                raise CommandError("Error %s" % ex)

            self.stdout.write(self.style.SUCCESS('Successfully Fix specialitie in %s contact from %s' % (nba, nb)))