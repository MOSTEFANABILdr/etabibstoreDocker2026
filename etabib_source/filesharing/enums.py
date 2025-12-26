from enum import Enum

from django.utils.translation import gettext as _


class PatientFileType(Enum):
    ORDONNANCES = ("1", _("ORDONNANCES"))
    BILANS = ("2", _("BILANS"))
    CERTIFICATS = ("3", _("CERTIFICATS"))
    LETTRES = ("4", _("LETTRES"))
    AUTRES = ("5", _("AUTRES"))
    COMPTES_RENDUS = ("6", _("COMPTES RENDUS"))
