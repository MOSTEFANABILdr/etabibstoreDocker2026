from django import template

from core.models import OffrePrepaye

register = template.Library()


def is_including_service(obj, service):
    services = []
    if isinstance(obj, OffrePrepaye):
        services = obj.services
    elif isinstance(obj, list):
        services = obj
    return service in services

@register.filter
def is_including_etabib_workspace(obj):
    return is_including_service(obj, OffrePrepaye.SERVICE_CHOICES[0][0])


@register.filter
def is_including_online_agenda(obj):
    return is_including_service(obj, OffrePrepaye.SERVICE_CHOICES[1][0])


@register.filter
def is_including_etabib_care(obj):
    return is_including_service(obj, OffrePrepaye.SERVICE_CHOICES[2][0])

@register.filter
def is_including_etabib_visio(obj):
    return is_including_service(obj, OffrePrepaye.SERVICE_CHOICES[3][0])

@register.filter
def is_including_etabib_store(obj):
    return is_including_service(obj, OffrePrepaye.SERVICE_CHOICES[4][0])

@register.filter
def is_including_e_prescription(obj):
    return is_including_service(obj, OffrePrepaye.SERVICE_CHOICES[5][0])

@register.filter
def is_including_etabib_annuaire(obj):
    return is_including_service(obj, OffrePrepaye.SERVICE_CHOICES[6][0])

@register.filter
def is_including_app_downloading(obj):
    return is_including_service(obj, OffrePrepaye.SERVICE_CHOICES[7][0])

@register.filter
def is_including_virtual_clinic(obj):
    return is_including_service(obj, OffrePrepaye.SERVICE_CHOICES[8][0])

@register.simple_tag
def reduction_status(offer, user):
    if isinstance(offer, OffrePrepaye):
        return offer.reduction_status(user)
