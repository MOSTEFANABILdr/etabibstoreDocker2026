'''
Created on 5 janv. 2019

@author: ZAHI
'''
from django import template
from django.utils import timezone
from django.utils.translation import gettext as _

from core.enums import ProductType, AnnonceType, CampagneType
from core.models import Produit, Medic, AutreProduit, AnnonceFeed, AnnonceDisplay, CampagneImpression, AnnonceVideo

register = template.Library()


@register.filter
def renderProductType(product, **kwargs):
    type = "default"
    name = ""
    if isinstance(product, Produit):
        type = "primary"
        name = ProductType.MEDICAL_DEVICE.value
    if isinstance(product, Medic):
        type = "danger"
        name = ProductType.DRUG.value
    if isinstance(product, AutreProduit):
        type = "warning"
        name = ProductType.AUTRE.value
    return '<span class="label label-%s">%s</span>' % (type, name)


@register.filter
def isMedicalDevice(product, **kwargs):
    return isinstance(product, Produit)


@register.filter
def isDrug(product, **kwargs):
    return isinstance(product, Medic)


@register.filter
def isAutre(product, **kwargs):
    return isinstance(product, AutreProduit)


@register.filter
def renderAnnonceType(annonce, **kwargs):
    type = "default"
    name = ""
    if isinstance(annonce, AnnonceFeed):
        type = "warning"
        name = AnnonceType.FEED.value
    if isinstance(annonce, AnnonceDisplay):
        type = "danger"
        name = AnnonceType.DISPLAY.value
    if isinstance(annonce, AnnonceVideo):
        type = "primary"
        name = AnnonceType.VIDEO.value
    return '<span class="label label-%s">%s</span>' % (type, name)


@register.filter
def isAnnonceFeed(annonce, **kwargs):
    return isinstance(annonce, AnnonceFeed)


@register.filter
def isAnnonceDisplay(annonce, **kwargs):
    return isinstance(annonce, AnnonceDisplay)


@register.filter
def isAnnonceVideo(annonce, **kwargs):
    return isinstance(annonce, AnnonceVideo)


@register.filter
def renderCampagneType(campagne, **kwargs):
    type = "default"
    name = ""
    if isinstance(campagne, CampagneImpression):
        type = "primary"
        name = CampagneType.PRINTING.value
    return '<span class="label label-%s">%s</span>' % (type, name)


@register.filter
def isCampagneImpression(campagne, **kwargs):
    return isinstance(campagne, CampagneImpression)


@register.filter
def isActive(campagne, **kwargs):
    return campagne.is_active


@register.filter
def isPending(campagne, **kwargs):
    if campagne.is_active:
        if campagne.date_debut:
            if campagne.date_debut > timezone.now():
                return True
    return False


@register.filter
def isVerfied(campagne, **kwargs):
    if campagne.verifie:
        return True
    return False


@register.filter
def renderCampagneStatus(campagne, **kwargs):
    if not isVerfied(campagne):
        name = _("Non vérifiée")
        type = "danger"
    elif isActive(campagne):
        name = _("Active")
        type = "success"
    elif isPending(campagne):
        name = _("En attente")
        type = "warning"
    else:
        name = _("Inactive")
        type = "default"
    return '<span class="badge badge-%s">%s</span>' % (type, name)


@register.filter
def to_class_name(value):
    return value.__class__.__name__
