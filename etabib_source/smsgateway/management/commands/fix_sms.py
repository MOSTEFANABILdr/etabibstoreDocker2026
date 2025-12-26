from django.core.management import BaseCommand, CommandError

from smsgateway.models import Sms


class Command(BaseCommand):
    help = 'Fix sms model'

    def handle(self, *args, **options):
            nb = 0
            nba = 0
            try:
                smss = Sms.objects.all()
                for sms in smss:
                    nb += 1
                    sms.source = sms.contact
                    sms.save()
                    nba += 1

            except Exception as ex:
                raise CommandError("Error %s" % ex)

            self.stdout.write(self.style.SUCCESS('Successfully Fix contact in %s sms from %s' % (nba, nb)))