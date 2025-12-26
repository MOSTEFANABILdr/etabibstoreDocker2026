from django import dispatch
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext as _

from core import tasks
from core.decorators import skip_signal
from teleconsultation.models import Tdemand, Treclamation


@receiver(post_save, sender=Tdemand)
@skip_signal()
def poste_save_teleconsultation_demand(sender, instance, created, **kwargs):
    """
    post_save signal used to push a notification to the doctor if a new teleconsultation demand is added
    :param sender:
    :param instance:
    :param created:
    :param kwargs:
    :return:
    """
    if created:
        if instance.from_patient:
            tasks.notify(
                instance,
                recipients=[instance.medecin.user],
                verb='Téléconsultation',
                description="Une demande de téconsultation par %s" % (instance.patient),
                action_object=instance.patient,
                url=reverse("doctor-teleconsultation", args=[instance.unique_id])
            )

        else:
            tasks.notify(
                instance,
                recipients=[instance.patient.user],
                verb='Téléconsultation',
                description="Dr %s vous appel" % instance.medecin.full_name,
                action_object=instance.medecin,
                url=reverse("patient-teleconsultation", args=[instance.unique_id])
            )


@receiver(post_save, sender=Treclamation)
def poste_save_treclamation(sender, instance, created, **kwargs):
    """
    post_save signal used to push a notification to the doctor
    if a new treclamation demand is added
    :param sender:
    :param instance:
    :param created:
    :param kwargs:
    :return:
    """
    if created:
        tasks.notify(instance, recipients=[instance.tdemande.medecin.user], verb=_('Réclamation'),
                     description=_(
                         "Une réclamation par %s"
                     ) % (instance.tdemande.patient)
                     )


@receiver(pre_save, sender=Treclamation)
def pre_save_treclamation(sender, instance, **kwargs):
    """
    PreSave signal used to
    push a notification to the patient if a treclamation demand is updated
    by the doctor
    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    if not instance._state.adding:
        try:
            reclamation = Treclamation.objects.get(pk=instance.pk)
            if reclamation.reponse != instance.reponse:
                tasks.notify(
                    instance,
                    recipients=[instance.tdemande.patient.user],
                    verb=_('Réclamation'),
                    description=_(
                        "Votre réclamation à été traitée par %s"
                    ) % (instance.tdemande.medecin)
                )
        except Treclamation.DoesNotExist:
            pass


###################
# Channel presense
##################
presence_changed = dispatch.Signal(
    providing_args=["room", "added", "removed", "bulk_change"]
)

# @receiver(presence_changed)
# def handle_presence_changed(sender, room, **kwargs):
#     for x in ["added", "removed", "bulk_change"]:
#         if x in kwargs:
#             if room.channel_name == settings.DOCTORS_CHANNEL:
#                 #get online patients list
#                 presences = Presence.objects.filter(room__channel_name=settings.PATIENTS_CHANNEL)
#                 channel_layer = get_channel_layer()
#                 out = []
#                 for p in presences:
#                     room_group_name = 'chat_%s' % p.user.pk
#                     async_to_sync(channel_layer.group_send)(
#                         room_group_name,
#                         {
#                             'type': 'notification_message',
#                             'data': {
#                                 'command': 'TELECONSULTATION_GET_ONLINE_DOCTORS_COUNT',
#                                 'count': room.get_users().count(),
#                             }
#                         }
#                     )
