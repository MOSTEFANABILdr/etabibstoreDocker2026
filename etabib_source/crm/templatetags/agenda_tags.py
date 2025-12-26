'''
Created on 30 msi. 2022

@author: Moncef
'''
from django import template
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from core.models import Prospect
from smsgateway.utils import verify_number

register = template.Library()


@register.simple_tag
def renderMobileStatus(object):
    if isinstance(object, Prospect):
        if verify_number(object.contact):
            name = _("Numéro valide")
            type = "primary"
        else:
            name = _("Numéro Invalide")
            type = "danger"
        return mark_safe('<span class="badge badge-%s">%s</span>' % (type, name))
