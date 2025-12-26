import logging

from django.core.management import BaseCommand
from django.utils.translation import gettext as _

from enewsletter.models import Newsletter


class Command(BaseCommand):
    help = _("Submit pending messages.")

    def handle(self, *args, **options):
        logger = logging.getLogger('newsletter')
        # Newsletter.submit_queue()
        #TODO: You can send emails to a maximum of 500 recipients per day through the Gmail website
        logger.info(_('Submitting queued newsletter mailings'))
