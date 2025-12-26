import datetime
from collections import defaultdict

from django import template
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from drugs.models import Medicament, Stock, MedicamentCnas, Amm

register = template.Library()


@register.simple_tag
def renderType(object):
    if isinstance(object, MedicamentCnas):
        if object.generic == "G":
            image = "drugs/image/%s%s" % ("G", ".png")
        elif object.generic == "P":
            image = "drugs/image/%s%s" % ("P", ".png")
        else:
            image = "drugs/image/%s%s" % ("NOT_AVAILABLE", ".png")
        return mark_safe('/static/%s' % (image))
    elif isinstance(object, Medicament):
        image = "drugs/image/%s%s" % ("NOT_AVAILABLE", ".png")
        if object.type:
            if object.type.upper() == "RÉ":
                image = "drugs/image/%s%s" % ("P", ".png")
            elif object.type.upper() == "GÉ":
                image = "drugs/image/%s%s" % ("G", ".png")
        return mark_safe('/static/%s' % (image))
    else:
        image = "drugs/image/%s%s" % ("NOT_AVAILABLE", ".png")
        return mark_safe('/static/%s' % (image))


class SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'


@register.simple_tag
def renderHaveInStock(object, medicament):
    html_input = '<input class="dispo-event" type="checkbox" data-med-id="{med_id}" data-toggle="toggle" data-on="{on_text}" data-off="{off_text}" data-style="slow" data-onstyle="success" data-offstyle="danger" {checked_status}>'
    html_input = html_input.format_map(
        SafeDict(
            on_text=_("Oui disponible"),
            off_text=_("Indisponible")
        )
    )
    if isinstance(medicament, Medicament):
        html_input = html_input.format_map(
            SafeDict(med_id=medicament.id)
        )

    if isinstance(object, Stock):
        if object:
            if object.valide:
                html_input = html_input.format_map(SafeDict(checked_status="checked"))
            else:
                html_input = html_input.format_map(SafeDict(checked_status=""))
    else:
        html_input = html_input.format_map(SafeDict(checked_status=""))
    return mark_safe(html_input)


@register.simple_tag
def renderCnasTarif(object):
    if isinstance(object, MedicamentCnas):
        if object:
            tarif = object.tarif_de_reference
            da = "DA"
            return mark_safe("%s %s" % (tarif, da))
    else:
        image = "drugs/image/%s%s" % ("NOT_AVAILABLE", ".png")
        return mark_safe('<img src="/static/%s" alt=""/>' % (image))


@register.filter
def renderRefundable(object):
    if isinstance(object, MedicamentCnas):
        if object.remboursable == "O":
            image = "drugs/image/%s%s" % (object.remboursable, ".png")
        else:
            image = "drugs/image/%s%s" % ("ON", ".png")
        return mark_safe('/static/%s' % (image))
    else:
        image = "drugs/image/%s%s" % ("NOT_AVAILABLE", ".png")
        return mark_safe('/static/%s' % (image))


@register.simple_tag
def renderMedicForme(nom_commercial):
    results = defaultdict(list)
    for medicament in nom_commercial.medicament_set.all():
        results[medicament.forme_homogene].append(medicament)
    ind = 0
    result = ''
    for form_homogene, medicamentList in results.items():
        ind += 1
        btn_out = ''
        for medicament in medicamentList:
            btn_sun = '<li class="medicament" data-med-id="%s"><a href="#">%s</a></li>' % (
                medicament.id, medicament.dosage)
            btn_out += btn_sun
        btn_image = "drugs/image/%s.png" % (form_homogene)
        btn_header = '<a id="dropdownMenu%s" data-toggle="dropdown"aria-haspopup="true" aria-expanded="true">\
                 <img src="/static/%s" height="48px" alt=""/>\
                 </a>\
                  <ul class="dropdown-menu" aria-labelledby="dropdownMenu%s">%s</ul>' % (ind, btn_image, ind, btn_out)
        result += mark_safe('<span class="dropdown">%s</span>' % (btn_header))
    return mark_safe(result)


@register.simple_tag
def renderCnasRemboursable(object):
    if isinstance(object, MedicamentCnas):
        if object.remboursable == "O":
            image = "drugs/image/%s%s" % (object.remboursable, ".png")
        else:
            image = "drugs/image/%s%s" % ("ON", ".png")
        return mark_safe('/static/%s' % (image))
    else:
        image = "drugs/image/%s%s" % ("NOT_AVAILABLE", ".png")
        return mark_safe('/static/%s' % (image))


@register.simple_tag
def renderDateTr(object):
    if isinstance(object, MedicamentCnas):
        if object.date_tr == None:
            return ""
        else:
            dt_tr = object.date_tr.replace('/', '-')
            return datetime.datetime.strptime(dt_tr, "%Y-%m-%d").date()
    return ""


@register.simple_tag
def getObservationCnas(object):
    if isinstance(object, MedicamentCnas):
        if object.observation:
            return object.observation
    return ""


@register.simple_tag
def renderAmm(object):
    if isinstance(object, Medicament):
        amm = Amm.objects.filter(medicament=object.unique_id)
        if amm.exists():
            amm = amm.first()
            if amm.amm == "A":
                image = "drugs/image/%s%s" % (amm.amm, ".png")
            elif amm.amm == "Non-Ren":
                image = "drugs/image/%s%s" % (amm.amm, ".png")
            elif amm.amm == "Retiré":
                image = "drugs/image/%s%s" % (amm.amm, ".png")
            return mark_safe('/static/%s' % (image))
        else:
            image = "drugs/image/%s%s" % ("NOT_AVAILABLE", ".png")
            return mark_safe('/static/%s' % (image))


@register.simple_tag
def getAmmObservation(object):
    if isinstance(object, Medicament):
        amm = Amm.objects.filter(medicament=object.unique_id)
        if amm.exists():
            amm = amm.first()
            if amm:
                return amm.motif_retrait
        else:
            return ""
