import datetime
import random
import string
from datetime import date, timedelta

import jwt
import requests
from allauth.account.models import EmailAddress
from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, DateTimeField, Aggregate, Value, Case, When, BooleanField
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from notifications.models import Notification

from appointements.models import DemandeRendezVous
from core.enums import LoyaltyServices, ActionTypeColor, NotificationVerb, Role
from core.models import Licence, Facture_OffrePrep_Licence, OffrePersonnalise_Service, Action, DetailAction, \
    DemandeIntervention, OffrePrepaye, Contact, Medecin, Facture
from core.templatetags.avatar_tags import avatar_url
from core.templatetags.event_tags import is_active_tracking, is_punctual_tracking, is_tech_intervention, \
    is_commercial_request, is_formation
from core.templatetags.offer_tags import is_including_etabib_workspace
from coupons.enums import CouponType
from coupons.models import Coupon
from etabibWebsite import settings


def grouped(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


def is_team_member(user):
    """
    Check if user is a team member (Staff or Admin).
    """
    return user.is_active and (user.is_staff or user.is_superuser)


def getUserNotification(user):
    pass


def getEventColor(object):
    if isinstance(object, Action):
        if is_active_tracking(object):
            color = ActionTypeColor.ACTIVE_TRACKING.value
        elif is_punctual_tracking(object):
            color = ActionTypeColor.PUNCTUAL_TRACKING.value
        elif is_tech_intervention(object):
            color = ActionTypeColor.TECH_INTERVENTION.value
        elif is_commercial_request(object):
            color = ActionTypeColor.COMMERCIAL_REQUEST.value
        elif is_formation(object):
            color = ActionTypeColor.FORMATION.value
        return color
    if isinstance(object, DetailAction):
        if object.type in (DetailAction.TYPE_CHOICES_CMR[0][0], DetailAction.TYPE_CHOICES_CMR[1][0],
                           DetailAction.TYPE_CHOICES_CMR[2][0], DetailAction.TYPE_CHOICES_CMR[3][0],
                           DetailAction.TYPE_CHOICES_CMR[4][0]):
            return "#001f3f"
        if object.type == DetailAction.TYPE_CHOICES_CMR[5][0]:
            return "#FF4136"
        if object.type == DetailAction.TYPE_CHOICES_CMR[6][0]:
            return "#85144b"
        if object.type == DetailAction.TYPE_CHOICES_CMR[7][0]:
            return "#2ECC40"
        if object.type == DetailAction.TYPE_CHOICES_CMR[8][0]:
            return "#FF851B"
        if object.type == DetailAction.TYPE_CHOICES_CMR[9][0]:
            return "#7FDBFF"
        if object.type == DetailAction.TYPE_CHOICES_CMR[10][0]:
            return "#3D9970"
        if object.type == DetailAction.TYPE_CHOICES_CMR[11][0]:
            return "#AAAAAA"
        if object.type == DetailAction.TYPE_CHOICES_CMR[12][0]:
            return "#0074D9"
        if object.type == DetailAction.TYPE_CHOICES_CMR[13][0]:
            return "#F012BE"
        if object.type == DetailAction.TYPE_CHOICES_CMR[14][0]:
            return "#F012BE"
        if object.type == DetailAction.TYPE_CHOICES_CMN[0][0]:
            return "#B10DC9"
    if isinstance(object, DemandeIntervention):
        return "#cd5c5c"
    if isinstance(object, DemandeRendezVous):
        return "#450090"
    return ""


def getEventTitle(object, user=None):
    if isinstance(object, Action):
        contact = object.contact
        if contact:
            address = "{} {}".format(contact.ville if contact.ville else "", contact.adresse if contact.adresse else "")
            return "%s: %s %s" % (contact, object.get_type_display(), address)
        else:
            return object.get_type_diplay()
    if isinstance(object, DetailAction):
        out = ""
        contact = object.action.contact
        type = object.get_type_display()
        if contact:
            address = "{} {}".format(contact.ville if contact.ville else "", contact.adresse if contact.adresse else "")
        if type:
            out = "{} {} {}".format(contact if contact else "", type + ":" if type else "",
                                    address if address.strip() else "")
        else:
            if hasattr(object, "facture"):
                out = "{} {} {}".format("Facture:", contact if contact else "", address if address.strip() else "")
            if hasattr(object, "clotureaction"):
                out = "{} {} {}".format("Clôture:", contact if contact else "", address if address.strip() else "")
        return out.strip()
    if isinstance(object, DemandeIntervention):
        contact = None
        if object.poste.medecin:
            contact = object.poste.medecin.contact
        if contact:
            address = "{} {}".format(contact.ville if contact.ville else "",
                                     contact.adresse if contact.adresse else "")
            return "%s: %s %s" % ("Demande Intervention", contact, address)

    if isinstance(object, DemandeRendezVous):
        if user == object.destinataire:
            return "%s: %s" % ("RV", object.demandeur.get_full_name())
        elif user == object.demandeur:
            return "%s: %s" % ("RV", object.destinataire.get_full_name())
        else:
            return ""


def getEventIcon(object):
    if isinstance(object, Action):
        if is_active_tracking(object):
            return 'refresh'
        elif is_punctual_tracking(object):
            return 'phone'
        elif is_tech_intervention(object):
            return 'wrench'
        elif is_commercial_request(object):
            return 'shopping-cart'
        elif is_formation(object):
            return 'video-camera'
    if isinstance(object, DemandeIntervention):
        return 'wrench faa-wrench animated'
    if isinstance(object, DetailAction):
        if object.type:
            if object.type in (DetailAction.TYPE_CHOICES_CMR[0][0], DetailAction.TYPE_CHOICES_CMR[1][0],
                               DetailAction.TYPE_CHOICES_CMR[2][0], DetailAction.TYPE_CHOICES_CMR[3][0],
                               DetailAction.TYPE_CHOICES_CMR[4][0]):
                return "search white"
            if object.type == DetailAction.TYPE_CHOICES_CMR[5][0]:
                return "phone-square"
            if object.type == DetailAction.TYPE_CHOICES_CMR[6][0]:
                return "info"
            if object.type == DetailAction.TYPE_CHOICES_CMR[7][0]:
                return "comment"
            if object.type == DetailAction.TYPE_CHOICES_CMR[8][0]:
                return "car"
            if object.type == DetailAction.TYPE_CHOICES_CMR[9][0]:
                return "spinner"
            if object.type == DetailAction.TYPE_CHOICES_CMR[10][0]:
                return "retweet"
            if object.type == DetailAction.TYPE_CHOICES_CMR[11][0]:
                return "money"
            if object.type == DetailAction.TYPE_CHOICES_CMR[12][0]:
                return "users"
            if object.type == DetailAction.TYPE_CHOICES_CMR[13][0]:
                return "refresh"
            if object.type == DetailAction.TYPE_CHOICES_CMR[14][0]:
                return "shopping-bag"
            if object.type == DetailAction.TYPE_CHOICES_CMN[0][0]:
                return "phone"
        else:
            if hasattr(object, "facture"):
                return "file-text"
            if hasattr(object, "clotureaction"):
                return "check"
    if isinstance(object, DemandeRendezVous):
        return "calendar"


def getAvailableLicenses(quantite):
    licences = Licence.objects.filter(
        fol_licensce_set__isnull=True, offre_perso_licence_set__isnull=True)[:quantite]
    return licences


def has_basic_wafi(license):
    co = license.current_offre()
    if co:
        if isinstance(co, Facture_OffrePrep_Licence):
            if co.offre.avantages.filter(code=LoyaltyServices.WAFI_BASIC.value).exists():
                return True
        if isinstance(co, OffrePersonnalise_Service):
            if co.offre.avantages.filter(code=LoyaltyServices.WAFI_BASIC.value).exists():
                return True
    return False


def has_gold_wafi(license):
    co = license.current_offre()
    if co:
        if isinstance(co, Facture_OffrePrep_Licence):
            if co.offre.avantages.filter(code=LoyaltyServices.WAFI_GOLD.value).exists():
                return True
        if isinstance(co, OffrePersonnalise_Service):
            if co.offre.avantages.filter(code=LoyaltyServices.WAFI_GOLD.value).exists():
                return True
    return False


def generate_username(first_name, last_name):
    val = "{0}{1}".format(first_name[0], last_name).lower()
    x = 0
    while True:
        if x == 0 and User.objects.filter(username=val).count() == 0:
            return val
        else:
            new_val = "{0}{1}".format(val, x)
            if User.objects.filter(username=new_val).count() == 0:
                return new_val
        x += 1
        if x > 1000000:
            raise Exception("Name is super popular!")


def get_first_day(dt, d_years=0, d_months=0):
    # d_years, d_months are "deltas" to apply to dt
    y, m = dt.year + d_years, dt.month + d_months
    a, m = divmod(m - 1, 12)
    return date(y + a, m + 1, 1)


def get_last_day(dt):
    return get_first_day(dt, 0, 1) + timedelta(-1)


def get_last_months(sdate, months):
    for i in range(months):
        yield (sdate)
        sdate += relativedelta(months=-1)


def calculateIncreasePercent(arr):
    if len(arr) != 2:
        return None
    else:
        base = arr[1]
        value = arr[0]
    q = value - base
    return None if base == 0 else q * 100 / base


def generate_random_email():
    domains = ["randommail.etabibstore.com"]
    letters = string.ascii_lowercase[:12]
    domain = random.choice(domains)
    name = ''.join(random.choice(letters) for i in range(7))
    mail = name + '@' + domain
    while True:
        if not EmailAddress.objects.filter(email=mail).exists():
            return mail
        else:
            return generate_random_email()


def nextNonWeekendDay(dt):
    d = dt + datetime.timedelta(days=1)
    if d.weekday() not in settings.CALENDAR_WEEKEND:
        return d
    else:
        return nextNonWeekendDay(d)


def getUserNotification(user):
    notifications = user.notifications.order_by("-id")
    count = user.notifications.unread().count()
    context = {
        'notifications': notifications[:10],
    }
    template_version = get_template_version(user=user)

    notif_list_html = render_to_string("partial/navbar-notifications-unit.html", context, using=template_version)
    return (count, notif_list_html)


def getNotificationContent(notification):
    if isinstance(notification, Notification):
        verb = notification.verb
        description = notification.description
        if notification.verb == NotificationVerb.DEMAND_ADD_TO_CARE_TEAM.value:
            verb = _("Équipe de soins")
            if notification.actor:
                description = _("%s souhaite vous ajouter à son équipe de soins") % notification.actor.patient
        elif notification.verb == NotificationVerb.DEMAND_ADD_TO_CARE_TEAM_ACCEPTED.value:
            verb = _("Équipe de soins")
            if notification.actor:
                description = _(
                    "%s a été ajouté à votre équipe de soins") % notification.actor.professionnel.get_full_name()
        elif notification.verb == NotificationVerb.DEMAND_RDV.value:
            verb = _("Rendez-vous")
            if notification.actor:
                description = _("Une demande de rendez-vous %s par %s") % (
                    notification.actor.get_type_display(), notification.actor.demandeur.get_full_name()
                )

        elif notification.verb == NotificationVerb.DEMAND_RDV_ACCEPTED.value:
            verb = _("Rendez-vous")
            if notification.actor:
                description = _("%s a fixé un rendez-vous pour vous") % (
                    notification.actor.destinataire.get_full_name()
                )

        elif notification.verb == NotificationVerb.DEMAND_RDV_REJECTED.value:
            verb = _("Rendez-vous")
            if notification.actor:
                description = _("%s a refusé votre demande de rendez-vous") % (
                    notification.actor.destinataire.get_full_name()
                )

        return verb, description


def generateJwtToken(user):
    if user and isinstance(user, User):
        cxt = {
            "context": {
                "user": {
                    "avatar": avatar_url(user),
                    "name": "%s %s" % (user.first_name, user.last_name),
                    "email": "%s" % user.email,
                    "id": user.id
                }
            },
            "aud": "eTabib Teleconsultation",
            "iss": settings.JWT_APP_ID,
            "sub": "etabibstore.com",
            "room": "*",
            "exp": int((timezone.now() + datetime.timedelta(hours=24)).timestamp())
        }
        encoded_token = jwt.encode(
            cxt,
            settings.JWT_APP_SECRET,
            algorithm='HS256'
        )
        return encoded_token


class BaseSQL(object):
    function = 'DATE_SUB'
    template = '%(function)s(NOW(), interval %(expressions)s day)'


class DurationAgr(BaseSQL, Aggregate):
    def __init__(self, expression, **extra):
        super(DurationAgr, self).__init__(
            expression,
            output_field=DateTimeField(),
            **extra
        )


def getListDoctorsUsingeTabibCare(sexe=None, q=None, specialty=None):
    """
    get list of doctors subscribed to etabib care
    if ids:
        then exclude doctors with id in ids
    :return:
    """

    medecins = Medecin.objects.filter(facture__fol_facture_set__date_expiration__gte=timezone.now())
    medecins = medecins.filter(facture__fol_facture_set__offre__services__icontains=OffrePrepaye.SERVICE_CHOICES[2][0])
    medecins = medecins.exclude(tarif_consultation=None)
    if sexe == "1":
        medecins = medecins.filter(contact__sexe=Contact.GENDER_CHOICES[0][0])
    elif sexe == "0":
        medecins = medecins.filter(contact__sexe=Contact.GENDER_CHOICES[1][0])
    if q:
        medecins = medecins.filter(
            Q(contact__nom__istartswith=q) | Q(contact__prenom__istartswith=q)
        )
    if specialty:
        medecins = medecins.filter(contact__specialite__libelle=specialty)
    # Add an extra field "is_online" to the queryset to check if the doctor is online or not
    medecins = medecins.annotate(
        is_online=Case(
            When(
                user__presence__isnull=True,
                then=Value(False)
            ), default=Value(True), output_field=BooleanField()
        )
    ).order_by("-is_online")
    # TODO: Same for custom offer
    return medecins.distinct()


def applyDiscount(total, coupon):
    if isinstance(coupon, Coupon):
        if coupon.type == CouponType.PERCENTAGE.value:
            total = float(total) - (float(total) * float(coupon.value) / 100)
        if coupon.type == CouponType.MONETARY.value:
            total = float(total) - float(coupon.value)
        if coupon.type == CouponType.SPONSORSHIP.value:
            total = float(0)
    return total if total > 0 else float(0)


def applyTVA(total, reduction=None, reduction_pourcentage=True, reduction_money_based=True, tva=settings.TVA):
    if reduction:
        if reduction_pourcentage:
            total = total - (total * reduction / 100)
        elif reduction_money_based:  # money based
            total = total - reduction
    return total + (total * tva / 100)


def has_value(someList, value):
    for x, y in someList:
        if x == value:
            return True
    return False


def get_nextautoincrement(mymodel):
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute("SELECT Auto_increment FROM information_schema.tables WHERE table_name='%s';" % \
                   mymodel._meta.db_table)
    row = cursor.fetchone()
    cursor.close()
    return row[0]


def hasEnoughMoney(patient, medecin):
    from teleconsultation.templatetags.teleconsultation_tags import has_discount, apply_discount
    # if not medecin.tarif_consultation:
    #     return True
    hasDiscount, coupon = has_discount(patient).values()
    if hasDiscount:
        tarif = apply_discount(medecin.tarif_consultation, coupon)
        return patient.solde >= tarif
    return patient.solde >= medecin.tarif_consultation


def checkJitsiRoomExists(roomName):
    ROOM_SIZE_API_URL = "https://%s/api/room-size?room=%s&domain=meet.jitsi" % (
        settings.ECONGRE_JITSI_DOMAIN_NAME, roomName
    )
    try:
        response = requests.get(ROOM_SIZE_API_URL, verify=False)
        if response.status_code == 200:
            return True
    except:
        pass
    return False


def createCommand(offre, medecin, coupon=None):
    with transaction.atomic():
        facture = Facture()
        facture.medecin = medecin
        facture.total = 0
        if coupon:
            facture.coupon = coupon
            coupon.redeem(user=medecin.user)
        facture.save()
        licences = None
        if is_including_etabib_workspace(offre):
            # Get list of available licences
            licences = getAvailableLicenses(1)
        fol = Facture_OffrePrep_Licence()
        fol.facture = facture
        fol.offre = offre
        if licences:
            fol.licence = licences[0]
        fol.save()
    return facture


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_template_version(request=None, user=None):
    template_version = "v2"
    grps = [Role.PATIENT.value, Role.DOCTOR.value, Role.VISITOR.value]
    if request:
        user = request.user

    if user.is_authenticated:
        if not user.groups.filter(name__in=grps).exists():
            template_version = "v1"
        elif user.groups.filter(name=Role.PATIENT.value).exists():
            template_version = "v2"
        elif hasattr(user, 'profile'):
            template_version = "v%s" % user.profile.template_version

    return template_version


def is_number(n):
    try:
        float(n)  # Type-casting the string to `float`.
        # If string is not a valid `float`,
        # it'll raise `ValueError` exception
    except ValueError:
        return False
    return True


def convert_distance(degrees):
    if degrees:
        km = degrees * 111.325
        if km < 1:
            m = km * 1000
            return "{:0.2f} m".format(m)

        return "{:0.2f} Km".format(km)
    return ""
