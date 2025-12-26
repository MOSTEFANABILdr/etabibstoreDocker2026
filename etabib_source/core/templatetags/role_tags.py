'''
Created on 5 janv. 2019

@author: ZAHI
'''
from django import template
from django.contrib.auth.models import User
from django.template.defaultfilters import upper
from django.utils.safestring import mark_safe

from core.enums import Role
from core.models import Contact

register = template.Library()


@register.filter
def is_doctor(obj, **kwargs):
    if isinstance(obj, User):
        if hasattr(obj, 'medecin'):
            return True
    if isinstance(obj, Contact):
        if hasattr(obj, 'medecin'):
            return True
    return False


@register.filter
def is_complete_profil(obj, **kwargs):
    if isinstance(obj, User) or isinstance(obj, Contact):
        if hasattr(obj, 'medecin'):
            contact = obj.medecin.contact
            return contact.pays and contact.ville and contact.mobile_1 and contact.specialite
    return True


@register.filter
def is_partner(obj, **kwargs):
    if isinstance(obj, User):
        if hasattr(obj, 'partenaire'):
            return True
    if isinstance(obj, Contact):
        if hasattr(obj, 'partenaire'):
            return True
    return False


@register.filter
def is_professionnal(obj, **kwargs):
    if isinstance(obj, User):
        if hasattr(obj, 'professionnelsante'):
            return True
    if isinstance(obj, Contact):
        if hasattr(obj, 'professionnelsante'):
            return True
    return False


@register.filter
def is_visitor(obj, **kwargs):
    if isinstance(obj, User):
        if hasattr(obj, 'professionnelsante'):
            if obj.groups.filter(name=Role.VISITOR.value).exists():
                return True
    return False


@register.filter
def is_operator(user, **kwargs):
    if isinstance(user, User):
        if hasattr(user, 'operateur'):
            return True
    return False


@register.filter
def is_patient(user, **kwargs):
    if isinstance(user, User):
        if hasattr(user, 'patient'):
            return True
    return False


@register.filter
def is_organizer(user, **kwargs):
    if isinstance(user, User):
        if hasattr(user, 'organisateur'):
            return True
    return False


@register.filter
def is_speaker(user, **kwargs):
    if isinstance(user, User):
        if hasattr(user, 'speaker'):
            return True
    return False


@register.filter
def is_moderator(user, **kwargs):
    if isinstance(user, User):
        if hasattr(user, 'moderateur'):
            return True
    return False


@register.simple_tag
def role(contact, extra_data=False):
    role = "Contact"
    label = "label-success"
    extra = ""
    is_client = False

    if isinstance(contact, Contact):
        if hasattr(contact, 'medecin'):
            role = "Médecin"
            label = "label-primary"
            is_client = True if contact.medecin.all_offers else False
        elif hasattr(contact, 'partenaire'):
            role = "Partenaire"
            label = "label-warning"
        elif hasattr(contact, 'professionnelsante'):
            if contact.professionnelsante.user.groups.first():
                role = contact.professionnelsante.user.groups.first()
            label = "label-warning"
        if extra_data:
            if hasattr(contact, 'prospect'):
                extra = "<br><span class='label label-info'>Prospect</span> %s" % (contact.prospect.cree_par)
            elif hasattr(contact, 'suivi'):
                extra = "<br><span class='label label-danger'>Phase de suivi</span>"
            if is_client:
                extra += "<br><span class='badge badge-success'>Client</span>"
        return mark_safe('<span class="label {1}">{0}</span>{2}'.format(upper(role), label, extra))


@register.filter
def has_no_role(contact):
    return not is_doctor(contact) and not is_partner(contact) and not is_professionnal(contact)


@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()
