from enum import Enum

from django.utils.translation import gettext as _


class CongreStatus(Enum):
    ACTIVE = _("ACTIVE")
    ARCHIVED = _("ARCHIVÉ")
    EXPIRED = _("TERMINÉ")
    INACTIVE = _("INACTIVE")
    CANCELED = _("ANNULÉ")
    NOT_PUBLISHED = _("NON PUBLIÉ")
    BROADCASTING = _("DIFFUSION")
    BROADCASTING_SOON = _("DIFFUSION BIENTÔT")

class WebinarStatus(Enum):
    ACTIVE = _("ACTIVE")
    ARCHIVED = _("ARCHIVÉ")
    EXPIRED = _("TERMINÉ")
    NOT_STATRTED_YET = _("PAS ENCORE COMMENCÉ")
    CANCELED = _("ANNULÉ")
    NOT_PUBLISHED = _("NON PUBLIÉ")
    SOON = _("BIENTÔT")
    BROADCASTING = _("DIFFUSION")
    BROADCASTING_SOON = _("DIFFUSION BIENTÔT")
