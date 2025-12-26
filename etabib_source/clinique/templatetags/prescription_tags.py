from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def renderMedicMenu(context):
    return mark_safe(render_to_string('menu_medic_forme.html', context))


@register.simple_tag
def renderForme(forme):
    return mark_safe("<img src = '/static/drugs/image/%s.png' height ='40px' alt = "">" % (forme))


@register.simple_tag
def renderFormePosologie(forme):
    if forme == "AUTRE" or forme=="BUV" or forme == "POUDRE" or forme=="SPRAY":
        result = "dose"
    elif forme == "COMP":
        result = "dose"
    elif forme == "DROP":
        result = "gtte"
    elif forme == "INJ":
        result = "Amp"
    elif forme == "POMMADE":
        result = "Application"
    elif forme == "POMMADE":
        result = "Application"
    elif forme == "SUPPO":
        result = "Supp"
    elif forme == "DISPO" or forme == "PANS":
        result = "usage"
    elif forme == "SOINS":
        result = "soins"
    elif forme == "INFU":
        result = "infusion"
    return result
