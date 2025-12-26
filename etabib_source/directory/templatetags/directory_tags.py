import datetime

import basehash
from django import template
from django.utils import timezone

from appointements.models import DemandeRendezVous
from core.models import Contact
from cryptography.fernet import Fernet

register = template.Library()

FERNET_KEY = "TcSubJ1rsSeRA8GhcEuw6_owfXkF725v8rJoI3ivOcc="

@register.filter
def contact_id_hash(contact):
    hash_fn = basehash.base52(32)
    return hash_fn.hash(contact.id)


@register.filter
def contact_id_unhash(contact_id_hashed):
    hash_fn = basehash.base52(32)
    return hash_fn.unhash(contact_id_hashed)

@register.filter
def rdv_hash(contact):
    fernet = Fernet(FERNET_KEY)
    message = "%s:%s" % (contact.id, timezone.now().timestamp())
    return fernet.encrypt(message.encode()).decode("utf-8")

@register.filter
def rdv_unhash(rdv_hashed):
    fernet = Fernet(FERNET_KEY)
    rdv = fernet.decrypt(
        bytes(rdv_hashed.encode("utf-8"))
    )
    contact_id, timestamp = rdv.decode("utf-8").split(":")
    return (contact_id, timestamp)

@register.simple_tag
def get_number_valide(obj):
    nb = None
    if isinstance(obj, Contact):
        if obj.mobile:
            nb = obj.mobile.replace(' ', '')
    elif isinstance(obj, Contact):
        if obj.telephone:
            nb = str(obj.telephone).replace(' ', '')
    if nb:
        if len(nb) == 10:
            if nb[:2] in ["07", "06", "05"]:
                return True
            else:
                return False
        elif len(nb) == 13:
            if nb[:5] in ["+2137", "+2136", "+2135"]:
                return True
            else:
                return False
        elif len(nb) == 14:
            if nb[:6] in ["002137", "002136", "002135"]:
                return True
            else:
                return False
    else:
        return False


@register.simple_tag
def renderDateLimit(object):
    if isinstance(object, DemandeRendezVous):
        dt = object.date_creation + datetime.timedelta(days=1)
        return dt.strftime('%d-%m-%Y')
    return ""


@register.simple_tag
def renderAdresse(object):
    if isinstance(object, DemandeRendezVous):
        return object.get_type_display()
    return ""
