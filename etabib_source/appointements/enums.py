from enum import Enum
from django.utils.translation import gettext as _


class RdvStatus(Enum):
    DONE = _("Fait")
    ACCEPTED = _("Acceptée")
    REFUSED = _("Refusée")
    CANCELED = _("Annulée")
    WAITING = _("En attente")
    EXPIRED = _("Expiré")
