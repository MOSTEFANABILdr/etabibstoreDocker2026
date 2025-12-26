'''
Created on 9 janv. 2019

@author: ZAHI
'''
from enum import Enum

from django.utils.translation import gettext as _


class Role(Enum):
    COMMERCIAL = "commercial"
    TECHNICIAN = "technicien"
    COMMUNICATION = "communication"
    DATA_ENTRY_PERSON = "agent de saisie"
    DOCTOR = "medecin"
    PARTNER = "partenaire"
    PATIENT = "patient"
    ORGANISATEUR = "organisateur"
    SPEAKER = "speaker"
    MODERATOR = "moderateur"
    PHARMACIST = "pharmacien"
    DELEGUE_COMMERCIAL = "delegue commercial"
    #
    DENTIST = "ch.dentiste"
    STUDENT = "étudiant"
    ADMINISTRATION = "administration"
    MINISTRY = "ministère"
    MEDICAL_PURCHASING_MANAGER = "responsable achat médical"
    PSYCHOLOGIST = "psychologue"
    AUXILIARY = "auxiliare"
    PARAMEDICAL = "paramédical"
    BIOLOGISTE = "biologiste"
    RESEARCHER = "chercheur"
    TEACHER = "enseignant"
    MEDICAL_COMPANY_MANAGER = "chef entreprise médical"
    COMM_MARKETING = "comm/marketing"
    COMPUTER_SCIENCE = "informatique"
    VISITOR = "visiteur"


class RocketChatGroup(Enum):
    SALES_TEAM = "Équipe commercial"
    TECHNICAL_TEAM = "Équipe technique"
    ALL_MEMBERS = "الفـريق"


class RocketChatGroupId(Enum):
    SALES_TEAM = "NWs8NmPNuTvJiFmsf"
    TECHNICAL_TEAM = "mawGYeguFA6zvsBPE"
    ALL_MEMBERS = "H6DXwfvrjK8cdr636"


class ModuleStatus(Enum):
    IS_INSTALLED = "1"
    TO_INSTALL = "2"
    NOT_INSTALLED = "3"
    TO_UNINSTALL = "4"
    NO_VERSION = "5"


class DemandType(Enum):
    SUIVI = "Suivi"
    TECHNIQUE = 'Technique'
    COMMECIALE = 'Commerciale'


class DemandeStatus(Enum):
    WAITING = _("En attente")
    ASSIGNED = _("Attribué")
    TREATED = _("Traitée")
    RESOLVED = _("Résolue")
    NOT_RESOLVED = _("Non Résolue")
    CANCELED = _("Annulée")


class DemandeStatusColor(Enum):
    WAITING = "#7FDBFF"  # AQUA
    ASSIGNED = "#001f3f"  # BLUE NAVY
    TREATED = "#85144b"  # MAROON
    RESOLVED = "#2ECC40"  # GREEN
    NOT_RESOLVED = "#DDDDDD"  # SILVER
    CANCELED = "#FF4136"  # RED


class TacheStatus(Enum):
    WAITING = _("En attente")
    ACTIVE = _("Active")
    TREATED = _("Traitée")
    RESOLVED = _("Résolue")
    OUTDATED = _("dépassée")
    CANCELED = _("Annulée")


class OfferStatus(Enum):
    ACTIVE = _("active")
    EXPIRED = _("expiré")
    INACTIVE = _("inactive")


class OfferStatusColor(Enum):
    ACTIVE = "#0074D9"  # BLUE
    EXPIRED = "#FF4136"  # RED
    INACTIVE = "#3D9970"  # Olive


class LicenceStatus(Enum):
    UNLIMITED = "UNLIMITED"


class LoyaltyServices(Enum):
    WAFI_BASIC = "WFB"
    WAFI_GOLD = "WFG"


class ProductType(Enum):
    DRUG = _("Médicament/Parapharmacie")
    MEDICAL_DEVICE = _("Dispositif médical")
    AUTRE = _("Autre")


class AnnonceType(Enum):
    FEED = _("Feed")
    DISPLAY = _("Display")
    VIDEO = _("Video")


class AdTypeHelper(Enum):
    DISPLAY = ("DISPLAY", "1")
    FEED = ("FEED", "2")
    VIDEO = ("VIDEO", "3")

    @staticmethod
    def get(type):
        return AdTypeHelper.DISPLAY if type == "1" else AdTypeHelper.FEED \
            if type == "2" else AdTypeHelper.VIDEO if type == "3" else None


class CampagneType(Enum):
    PRINTING = _("Campagne publicitaire")
    DPS = _("Campagne classement")


class ActionTypeColor(Enum):
    ACTIVE_TRACKING = "#0074D9"  # blue
    PUNCTUAL_TRACKING = "#FF851B"  # ORANGE
    TECH_INTERVENTION = "#FF4136"  # RED
    COMMERCIAL_REQUEST = "#85144b"  # MARRON
    FORMATION = "#111111"  # purple


class WebsocketCommand(Enum):
    FETCH_NOTIFICATIONS = "FETCH_NOTIFICATIONS"
    FETCH_CART_COUNTS = "FETCH_CART_COUNTS"
    NEW_NOTIFICATION = "NEW_NOTIFICATION"
    TELECONSULTATION_DEMAND_ACCEPTED = "TELECONSULTATION_DEMAND_ACCEPTED"
    TELECONSULTATION_DEMAND_CANCELED = "TELECONSULTATION_DEMAND_CANCELED"
    TELECONSULTATION_DEMAND = "TELECONSULTATION_DEMAND"
    TELECONSULTATION_DEMAND_REJECTED = "TELECONSULTATION_DEMAND_REJECTED"
    NEW_ROCKCHAT_MESSAGE = "NEW_ROCKCHAT_MESSAGE"


class AdsDestination(Enum):
    ETABIB_WORKSPACE = "2"
    WEB = "1"
    AFFICHAGE_CONGRES = "5"


class AdsStatsType(Enum):
    DISPLAY = "1"
    CLICK = "2"


class EtabibService(Enum):
    ETABIB_WORKSPACE = "1"
    ONLINE_AGENDA = "2"
    ETABIB_CARE = "3"
    ETABIB_VISIO = "4"
    ETABIB_STORE = "5"
    E_PRESCRIPTION = "6"
    ETABIB_ANNUAIRE = "7"
    DOWNLOADING_APPS = "8"
    VIRTUAL_CLINIC = "9"


class NotificationVerb(Enum):
    DEMAND_ADD_TO_CARE_TEAM = "demand_add_to_care_team"
    DEMAND_ADD_TO_CARE_TEAM_ACCEPTED = "demand_add_to_care_team_accepted"
    DEMAND_RDV = "demand_rdv"
    DEMAND_RDV_ACCEPTED = "demand_rdv_accepted"
    DEMAND_RDV_REJECTED = "demand_rdv_rejected"
