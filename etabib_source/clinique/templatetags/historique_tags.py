from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from clinique.models import Consultation, Document

register = template.Library()


@register.filter
def hist_event_date(date):
    return date.strftime("%b %d %Y")


@register.filter
def hist_event_time(date):
    return date.strftime("%H:%M")


@register.filter
def hist_content_type(event):
    span_html = '<span class="label label-%s">%s</span>'
    span_text = ""
    span_class = "info"
    if isinstance(event, Consultation):
        span_text = _("Consultation")
        span_class = "purple"
    elif isinstance(event, Document):
        span_text = _("Document")
        span_class = "inverse"
    return mark_safe(span_html % (span_class, span_text))


@register.filter
def hist_render_content(event):
    if isinstance(event, Consultation):
        return render_to_string('partial/care-path-consultation.html', {'consultation': event})
    elif isinstance(event, Document):
        return render_to_string('partial/care-path-document.html', {'document': event})


@register.filter
def consultation_motif(obj):
    if isinstance(obj, Consultation):
        if obj.motif:
            return obj.motif
        return ""


@register.filter
def consultation_interrogatoire(obj):
    if isinstance(obj, Consultation):
        if obj.interrogatoire:
            return obj.interrogatoire
        return ""


@register.filter
def consultation_examenclinique(obj):
    if isinstance(obj, Consultation):
        if obj.examen_clinique:
            return obj.examen_clinique
        return ""


@register.filter
def consultation_examendemande(obj):
    if isinstance(obj, Consultation):
        if obj.examen_demande:
            return obj.examen_demande
        return ""


@register.filter
def consultation_resultatexamen(obj):
    if isinstance(obj, Consultation):
        if obj.resultat_examen:
            return obj.resultat_examen
        return ""


@register.filter
def consultation_diagsuppose(obj):
    if isinstance(obj, Consultation):
        if obj.diag_suppose:
            return obj.diag_suppose
        return ""


@register.filter
def consultation_diagretenu(obj):
    if isinstance(obj, Consultation):
        if obj.diag_retenu:
            return obj.diag_retenu
        return ""


@register.filter
def consultation_conduitetenir(obj):
    if isinstance(obj, Consultation):
        if obj.conduite_tenir:
            return obj.conduite_tenir
        return ""
