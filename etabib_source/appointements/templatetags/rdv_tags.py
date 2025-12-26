'''

@author: ZAHI
'''
from django import template
from django.template.defaultfilters import yesno
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from appointements.enums import RdvStatus
from appointements.models import DemandeRendezVous

register = template.Library()



@register.filter
def renderStatus(obj):
    if isinstance(obj, DemandeRendezVous):
        extra = ""
        if obj.status == RdvStatus.DONE:
            text = _("Fait")
            css_class = "primary"
            return mark_safe('<span class="badge badge-%s">%s</span>' % (css_class, text))
        if obj.status == RdvStatus.ACCEPTED:
            text = _("Acceptée")
            css_class = "success"
        elif obj.status == RdvStatus.REFUSED:
            text = _("Refusée")
            css_class = "danger"
            if obj.motif_refus:
                extra = "<p><strong>%s:</strong> %s</p>" % (_("Motif de refus"), obj.motif_refus)
        elif obj.status == RdvStatus.CANCELED:
            text = _("Annulée")
            css_class = "warning"
        elif obj.status == RdvStatus.EXPIRED:
            text = _("Expirée")
            css_class = "danger"
        else:
            text = _("En attente")
            css_class = "info"
        return mark_safe('<span class="badge badge-%s">%s</span><br>%s' % (css_class, text, extra))
    return ""
