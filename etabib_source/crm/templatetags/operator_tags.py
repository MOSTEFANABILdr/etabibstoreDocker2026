'''
Created on 5 janv. 2019

@author: ZAHI
'''
from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from core.enums import OfferStatus, \
    OfferStatusColor
from core.models import OffrePrepaye, OffrePartenaire, DetailAction

register = template.Library()


@register.filter
def renderStatus(object, **kwargs):
    if isinstance(object, (OffrePrepaye, OffrePartenaire)):
        status = object.status
        if status == OfferStatus.ACTIVE:
            css_class = 'badge'
            color = OfferStatusColor.ACTIVE.value
        elif status == OfferStatus.INACTIVE:
            css_class = 'badge'
            color = OfferStatusColor.INACTIVE.value
        if status == OfferStatus.EXPIRED:
            css_class = 'badge'
            color = OfferStatusColor.EXPIRED.value
        return '<span class="%s" style="background-color: %s">%s</span>' % (css_class, color, status.value)
    return ""


@register.filter
def getUrl(object):
    if isinstance(object, OffrePrepaye):
        return reverse("detail-offer", args=(object.id, object.slug))
    if isinstance(object, OffrePartenaire):
        return reverse("detail-offer-partner", args=(object.id, object.slug))


@register.simple_tag
def renderTreatmentStatus(object):
    if isinstance(object, DetailAction):
        treated = object.is_treated()
        if treated is None:
            return ""
        if treated:
            status = _("Traité")
            css_class = "primary"
        elif treated == False:
            status = _("Non Traité")
            css_class = "warning"
        return mark_safe("<span class='label label-%s pull-right'>%s</span>" % (css_class, status))
    return ""
