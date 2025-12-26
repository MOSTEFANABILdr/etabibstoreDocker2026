from datetime import datetime

from django import template
from django.template.defaultfilters import upper
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.timesince import timeuntil
from django.utils.translation import gettext as _

from econgre.enums import CongreStatus, WebinarStatus
from econgre.models import UserParticipationWebinar, Webinar, Congre

register = template.Library()


@register.simple_tag
def has_sent_paticipation(webinar, user):
    if UserParticipationWebinar.objects.filter(
            webinar=webinar,
            user=user,
    ).exists():
        return True
    return False


@register.filter
def is_active(object):
    if isinstance(object, Congre):
        status = object.status
        return status == CongreStatus.ACTIVE
    if isinstance(object, Webinar):
        status = object.status
        return status in (WebinarStatus.ACTIVE, WebinarStatus.BROADCASTING)


@register.filter
def is_archived(object):
    if isinstance(object, Congre):
        status = object.status
        return status == CongreStatus.ARCHIVED
    if isinstance(object, Webinar):
        status = object.status
        return status == WebinarStatus.ARCHIVED


@register.filter
def is_published(object):
    if isinstance(object, Congre):
        status = object.status
        return not (status == CongreStatus.NOT_PUBLISHED)
    if isinstance(object, Webinar):
        status = object.status
        return not (status == WebinarStatus.NOT_PUBLISHED)


@register.filter
def is_canceled(object):
    if isinstance(object, Congre):
        status = object.status
        return status == CongreStatus.CANCELED
    if isinstance(object, Webinar):
        status = object.status
        return status == WebinarStatus.CANCELED


@register.filter
def is_expired(object):
    if isinstance(object, Congre):
        status = object.status
        return status == CongreStatus.EXPIRED
    if isinstance(object, Webinar):
        status = object.status
        return status == WebinarStatus.EXPIRED


@register.filter
def is_soon(object):
    if isinstance(object, Webinar):
        status = object.status
        return (status in (WebinarStatus.SOON, WebinarStatus.BROADCASTING_SOON))


@register.filter
def is_participation_opened(object):
    if isinstance(object, Webinar):
        status = object.status
        return (status in (WebinarStatus.NOT_STATRTED_YET, WebinarStatus.SOON, WebinarStatus.ACTIVE))


@register.filter
def renderStatus(object):
    if isinstance(object, Congre):
        css_class = ""
        status = object.status
        if status == CongreStatus.ACTIVE:
            css_class = "primary"
        elif status == CongreStatus.EXPIRED:
            css_class = "warning"
        elif status == CongreStatus.INACTIVE:
            css_class = "default"
        elif status == CongreStatus.CANCELED:
            css_class = "danger"
        elif status == CongreStatus.NOT_PUBLISHED:
            css_class = "info"
        elif status == CongreStatus.BROADCASTING:
            css_class = "success"
        elif status == CongreStatus.BROADCASTING_SOON:
            css_class = "primary"
        return mark_safe('<span class="label label-%s">%s</span>' % (css_class, status.value))
    if isinstance(object, Webinar):
        css_class = ""
        status = object.status
        extra = ""
        if status == WebinarStatus.ACTIVE:
            css_class = "success"
        elif status == WebinarStatus.EXPIRED:
            css_class = "warning"
        elif status == WebinarStatus.NOT_STATRTED_YET:
            css_class = "default"
        elif status == WebinarStatus.CANCELED:
            css_class = "danger"
        elif status == WebinarStatus.NOT_PUBLISHED:
            css_class = "info"
        elif status == CongreStatus.ARCHIVED:
            css_class = "info purple"
        elif status == WebinarStatus.SOON:
            css_class = "primary"
            extra = "<span>%s</span>" % _("Il reste %s") % timeuntil(
                datetime.combine(object.date_debut, object.heure_debut)
            )
        elif status == WebinarStatus.BROADCASTING:
            css_class = "success"
        elif status == WebinarStatus.BROADCASTING_SOON:
            css_class = "primary"
            extra = "<span>%s</span>" % _("Il reste %s") % timeuntil(
                datetime.combine(object.date_diffustion, object.heure_debut_diffusion)
            )
        return mark_safe('<span class="label label-%s">%s</span> %s' % (css_class, status.value, extra))


@register.filter
def renderType(object):
    if isinstance(object, Congre):
        css_class = ""
        type = object.type
        if type == Congre.TYPE_CHOICES[0][0]:
            css_class = "success"
        elif type == Congre.TYPE_CHOICES[1][0]:
            css_class = "warning"
        elif type == Congre.TYPE_CHOICES[2][0]:
            css_class = "info"
        return mark_safe('<span class="badge badge-%s">%s</span>' % (css_class, upper(object.get_type_display())))


@register.filter
def is_presentiel(object):
    if isinstance(object, Congre):
        type = object.type
        return type == Congre.TYPE_CHOICES[1][0]


@register.filter
def is_distanciel(object):
    if isinstance(object, Congre):
        type = object.type
        return type == Congre.TYPE_CHOICES[0][0]


@register.filter
def is_presentiel_and_distanciel(object):
    if isinstance(object, Congre):
        type = object.type
        return type == Congre.TYPE_CHOICES[2][0]
