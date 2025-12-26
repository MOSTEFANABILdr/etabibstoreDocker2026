'''
Created on 5 janv. 2019

@author: ZAHI
'''
from django import template
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from djmoney.money import Money

from appointements.models import DemandeRendezVous
from core.models import Medecin, Patient
from core.utils import applyDiscount
from coupons.models import CouponUser
from etabibWebsite import settings
from teleconsultation.models import Presence
from teleconsultation.models import Room, Tdemand

register = template.Library()


@register.simple_tag
def render_status(obj):
    if isinstance(obj, Medecin):
        return "online" if obj.is_online else ""  # away
    if isinstance(obj, Patient):
        return "online" if Presence.objects.filter(user=obj.user).exists() else ""  # away
    if isinstance(obj, User):
        return "online" if Presence.objects.filter(user=obj).exists() else ""  # away


@register.filter
def is_online(obj):
    if isinstance(obj, Medecin):
        try:
            room = Room.objects.get(channel_name=settings.DOCTORS_CHANNEL)
            return room.has_presence(obj.user)
        except Room.DoesNotExist:
            return False
    elif isinstance(obj, DemandeRendezVous):
        return obj.type == DemandeRendezVous.TYPE_CHOICES[0][0]
    elif isinstance(obj, Patient):
        try:
            room = Room.objects.get(channel_name=settings.PATIENTS_CHANNEL)
            return room.has_presence(obj.user)
        except Room.DoesNotExist:
            return False
    return False


@register.simple_tag
def has_rdv_with(destinataire, demandeur):
    dmnds = DemandeRendezVous.objects.filter(
        destinataire=destinataire,
        demandeur=demandeur,
        acceptee=False,
        refusee=False,
        annulee=False
    )
    if dmnds.exists():
        return (True, dmnds.first().id)
    else:
        return (False, None)


@register.simple_tag
def render_online_doctor(medecin):
    if medecin:
        return render_to_string("partial/teleconsultation_doctor_item.html", {'medecin': medecin})


@register.simple_tag
def online_doctors_count():
    try:
        room = Room.objects.get(channel_name=settings.DOCTORS_CHANNEL)
        return room.get_users().count()
    except Room.DoesNotExist:
        return 0


@register.simple_tag
def render_rdv_types():
    out = '<select id="rdv_choices">'
    for type in DemandeRendezVous.TYPE_CHOICES:
        out += '<option value="%s">%s</option>' % (type[0], type[1])
    out += "</select>"
    return mark_safe(out)


@register.simple_tag
def render_rdv_description():
    out = '<div class="form-group">' \
          '<label for="comment">' + str(_("Description")) + ':</label>' \
           '<textarea id="rdv_description" class="form-control"></textarea>' \
           '</div>'
    return mark_safe(out)


@register.simple_tag
def has_discount(patient):
    if isinstance(patient, Patient):
        cu = CouponUser.objects.filter(
            user=patient.user,
            coupon__target="2"  # see COUPON_TARGETS settings
        ).order_by('id').last()
        if cu and not cu.coupon.expired():
            if not Tdemand.objects.filter(patient=patient, coupon=cu.coupon).exists():
                return {"has_discount": True, "coupon": cu.coupon}
    return {"has_discount": False, "coupon": None}


@register.simple_tag
def apply_discount(tarif, coupon):
    if coupon and not coupon.expired():
        if isinstance(tarif, Money):
            total = applyDiscount(tarif.amount, coupon)
            return Money(amount=total, currency=tarif.currency, decimal_places=0)
    return tarif


@register.simple_tag
def is_from_care_team(patient, professionnel):
    if isinstance(professionnel, User):
        return patient.equipe_soins.filter(professionnel=professionnel, confirme=True).exists()
    return False
