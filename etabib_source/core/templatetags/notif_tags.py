from django import template
from django.urls import reverse
from django.utils import timezone
from notifications.models import Notification

from appointements.models import DemandeRendezVous
from core.enums import Role
from core.models import Module, Action, Tache, DetailAction, DemandeIntervention, Virement
from core.utils import getNotificationContent
from teleconsultation.models import Tdemand, Treclamation

register = template.Library()

@register.simple_tag
def notificationContent(notification):
    return getNotificationContent(notification)


@register.filter
def renderNotificationIcon(notification, **kwargs):
    if isinstance(notification, Notification):
        iconUrl = getNotificationIconUrl(notification)
        icon = '<img class="notification-icon" src="' + iconUrl + '">'
        return icon
    return ""


@register.filter
def renderNotificationOnClickUrl(notification, **kwargs):
    return getNotificationUrl(notification)


def getNotificationIconUrl(notification):
    if isinstance(notification, Notification):
        icon = '/static/img/logo/ihsm.png'
        try:
            if isinstance(notification.actor, Module):
                icon = notification.actor.icon.url
            if isinstance(notification.actor, Tache):
                icon = '/static/img/tasks.png'
            if isinstance(notification.actor, Tdemand):
                icon = '/static/img/teleconsultation.png'
            if isinstance(notification.actor, Treclamation):
                icon = '/static/img/reclamation.png'
        except Exception:
            pass
        return icon


def getNotificationUrl(notification, **kwargs):
    url = "#"
    if notification:
        if isinstance(notification, Notification):
            if notification.data and "url" in notification.data and notification.data.get("url", ""):
                url = notification.data.get("url", "") + "?notif_id=%s" % (notification.id)
            else:
                try:
                    if isinstance(notification.actor, Module):
                        url = reverse("etabib-store-item", args=[notification.actor.id, notification.actor.slug]) + (
                                "?notif_id=%s" % notification.id)
                    if isinstance(notification.actor, Action):
                        url = reverse("action-detail", args=[notification.actor.id]) + ("?notif_id=%s" % notification.id)
                    if isinstance(notification.actor, DetailAction):
                        url = reverse("action-detail", args=[notification.actor.action.id]) + (
                                "?notif_id=%s" % notification.id)
                    if isinstance(notification.actor, DemandeIntervention):
                        url = reverse("demande-intervention-detail", args=[notification.actor.id]) + (
                                "?notif_id=%s" % notification.id)
                    if isinstance(notification.actor, Tache):
                        if notification.recipient.groups.filter(name=Role.COMMERCIAL.value):
                            url = reverse("operator-dashboard")
                        elif notification.recipient.groups.filter(name=Role.COMMUNICATION.value):
                            url = reverse("operator-dashboard")
                    if isinstance(notification.actor, Tdemand):
                        if notification.actor.from_patient:
                            url = reverse("doctor-teleconsultation", args=[notification.actor.unique_id]) + (
                                    "?notif_id=%s" % notification.id)
                        else:
                            url = reverse("patient-teleconsultation", args=[notification.actor.unique_id]) + (
                                    "?notif_id=%s" % notification.id)
                    if isinstance(notification.actor, DemandeRendezVous):
                        url = "#"
                        if notification.actor.destinataire == notification.recipient:
                            if notification.actor.destinataire.groups.filter(
                                    name=Role.DOCTOR.value
                            ).exists():
                                url = reverse("doctor-appointments")+ ("?notif_id=%s" % notification.id)
                            elif notification.actor.destinataire.groups.filter(
                                    name=Role.PARTNER.value
                            ).exists():
                                url = reverse("partner-appointments") + ("?notif_id=%s" % notification.id)
                            elif notification.actor.destinataire.groups.filter(
                                    name=Role.PATIENT.value
                            ).exists():
                                url = reverse("patient-appointments") + ("?notif_id=%s" % notification.id)
                    if isinstance(notification.actor, Virement):
                        url = reverse("commercial-list-virement") + ("?notif_id=%s" % notification.id)

                except Exception as e:
                    print(e)
    return url
