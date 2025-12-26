'''
Created on 5 janv. 2019

@author: ZAHI
'''
import os
import random

import basehash
from django import template
from django.shortcuts import redirect
from django.template.defaultfilters import pluralize
from django.utils.translation import gettext as _
from rest_framework.authtoken.models import Token

from clinique.models import CliniqueVirtuelle
from core.models import PointsHistory, Action, UserAgreement
from core.utils import getEventIcon, getEventColor
from etabibWebsite import settings
from etabibWebsite.settings import ENVIRONMENT

register = template.Library()


@register.filter
def age(date_naissance, **kwargs):
    if date_naissance:
        import datetime
        return int((datetime.date.today() - date_naissance).days / 365.25)
    return ""


@register.filter
def getSearchPageUrl(path, **kwargs):
    if path:
        if redirect("etabib-store").url in path:
            return redirect("etabib-store-search").url
        elif redirect("doctor-documentation").url in path:
            return redirect("doctor-documentation").url
    return "#"


@register.filter
def isSearchedUrl(path, **kwargs):
    if path:
        urls = [redirect("etabib-store").url, redirect("doctor-documentation").url]
        for url in urls:
            if url in path:
                return True
    return False


@register.filter
def duration(td):
    if td:
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
    else:
        total_seconds = 0
        hours = 0
        minutes = 0
    # return str(hours) + ' ' + pluralize(hours, _('heure')) + str(minutes) + ' min'
    return ' {} {} {} min'.format(hours, pluralize(hours, _('heure,heures')), minutes)


@register.filter
def getimagename(image):
    return os.path.basename(image.name)


@register.filter
def geticon(object):
    if isinstance(object, PointsHistory):
        iconUrl = "/static/img/notification/inc.png" if object.points >= 0 else "/static/img/notification/dec.png"
        icon = '<img class="notification-icon" src="' + iconUrl + '">'
        return icon
    elif isinstance(object, Action):
        return '<i class="fa fa-{0}" style="background-color: {1};' \
               'color: #ffffff;' \
               'border-color: {1};"></i>'.format(getEventIcon(object), getEventColor(object))


@register.filter
def increase_pourecentage(value):
    if value:
        if value >= 0:
            icon = '<i class="fa fa-level-up"></i>'
            bg = 'bg-blue'
        else:
            icon = '<i class="fa fa-level-down"></i>'
            bg = 'bg-purple'
        return '<span class="income-percentange %s">' \
               '<span class="counter">%s</span>%s %s</span>' % (bg, value, '%', icon)
    return ""


@register.filter
def index(indexable, i):
    return indexable[i]


@register.filter
def has_license(user, **kwargs):
    if hasattr(user, "medecin"):
        licenses = []
        for fac in user.medecin.facture_set.all():
            if fac.offre_prepa:
                for fol in fac.fol_facture_set.all():
                    licenses.append((fol.licence, fac))

            elif fac.offre_perso:
                for ops in fac.offre_perso_services_set():
                    if ops.service.creer_licence:
                        licenses.append((ops.licence, fac))
        return len(licenses) > 0
    return False


# settings value
@register.simple_tag
def settings_value(name):
    return getattr(settings, name, "")


@register.simple_tag
def user_id_hash(user):
    hash_fn = basehash.base52(32)
    return hash_fn.hash(user.id)


@register.simple_tag
def user_id_unhash(user_id_hashed):
    hash_fn = basehash.base52(32)
    return hash_fn.unhash(user_id_hashed)


@register.simple_tag
def offer_id_hash(offer):
    hash_fn = basehash.base56(32)
    return hash_fn.hash(offer.id)


@register.simple_tag
def offer_id_unhash(offer_id_hashed):
    hash_fn = basehash.base56(32)
    return hash_fn.unhash(offer_id_hashed)


@register.simple_tag
def coupon_id_hash(coupon):
    hash_fn = basehash.base36(32)
    return hash_fn.hash(coupon.id)


@register.simple_tag
def coupon_id_unhash(coupon_id_hashed):
    hash_fn = basehash.base36(32)
    return hash_fn.unhash(coupon_id_hashed)


@register.filter
def getThmbnailFromGoogleDriveLink(link):
    url = "https://drive.google.com/thumbnail?authuser=0&sz=w320&id=%s"
    if link:
        if link.startswith("https://drive.google.com/file/d/") and link.endswith("/preview"):
            return '<img class ="img-responsive" src="%s" />' % url % link[32:-8]
    return '<i class="img-fluid fa fa-film"></i>'


@register.simple_tag
def random_int(a, b=None):
    try:
        if b is None:
            a, b = 0, a
        return random.randint(a, b)
    except:
        return 0


@register.simple_tag
def percentage(value, maxValue):
    if value and maxValue:
        return "%.2f" % ((value * 100) / maxValue)
    else:
        return 0


@register.simple_tag
def isDevelopingMode():
    return getattr(settings, "ENVIRONMENT", "") == ENVIRONMENT.DEV


@register.simple_tag
def has_agreed_tos(user):
    return UserAgreement.objects.filter(
        user=user,
    ).exists()


@register.simple_tag
def is_mobile_app(request):
    return "TeleConsult-Android" in request.META['HTTP_USER_AGENT']


@register.simple_tag
def get_clinique_virtuelle(user):
    return CliniqueVirtuelle.objects.filter(user=user).first()


@register.simple_tag
def user_token(request):
    token, created = Token.objects.get_or_create(user=request.user)
    return token

@register.simple_tag
def country_code(language_code):
    if language_code == "ar":
        return "dz"
    if language_code == "fr":
        return " "
    if language_code == "en":
        return "en"
    return ""

@register.filter
def join_fk_by(fks, arg):
    ids =[]
    if fks:
        for fk in fks:
            ids.append(f"{fk.id}")
    return arg.join(ids)

@register.filter
def join_fk_value_by(fks, arg):
    ids =[]
    if fks:
        for fk in fks:
            ids.append(f"{fk.libelle}")
    return arg.join(ids)
