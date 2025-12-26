from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext as _

from appointements.models import DemandeRendezVous
from core import tasks
from core.decorators import skip_signal
from core.enums import NotificationVerb


@receiver(post_save, sender=DemandeRendezVous)
@skip_signal()
def poste_save_demande_rendez_vous(sender, instance, created, **kwargs):
    """
    :param sender:
    :param instance:
    :param created:
    :param kwargs:
    :return:
    """
    if created:
        if instance.destinataire:
            recipients = [instance.destinataire]
            tasks.notify(instance, recipients=recipients, verb=NotificationVerb.DEMAND_RDV.value)
    else:
        if instance.acceptee:
            recipients = [instance.demandeur]
            tasks.notify(instance, recipients=recipients, verb=NotificationVerb.DEMAND_RDV_ACCEPTED.value)
        elif instance.refusee:
            recipients = [instance.demandeur]
            tasks.notify(instance, recipients=recipients, verb=NotificationVerb.DEMAND_RDV_REJECTED.value)
