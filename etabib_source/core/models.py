import datetime
import mimetypes
import os
import uuid

from cities_light.models import City, Country, Region
from django.contrib.auth import get_user_model, login
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db.models import PointField
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator, FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _, get_language
from django_softdelete.models import SoftDeleteModel
from djmoney.models.fields import MoneyField
from embed_video.fields import EmbedVideoField
from location_field.models.plain import PlainLocationField
from multiselectfield import MultiSelectField
from phonenumber_field.modelfields import PhoneNumberField
from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel
from tinymce import models as tinymce_models
from translated_fields import TranslatedField

from core.enums import ModuleStatus, OfferStatus, LicenceStatus, AdsStatsType, EtabibService
from core.managers import SoftPolyMorphDeleteManager, NonArchivedContactManager, ArchivedContactManager, \
    AllContactManager
from core.mime_types import FileMimeTypeValidator
from core.storage import CustomGoogleDriveStorage
from coupons.models import Coupon
from drugs.models import DciAtc
from epayment.models import OrdreDePaiement
from etabibWebsite import settings
from store.managers import RandomManager
from taggit_autosuggest.managers import TaggableManager


class Avatar(models.Model):
    image = models.ImageField(
        upload_to='avatar/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    "jpg", "png", "jpeg"
                ]
            )
        ]
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(verbose_name=_('Date de création'), auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    template_version = models.IntegerField(default=1)
    data = models.JSONField(default=dict)

    @property
    def nb_list(self):
        return self.data.get("nb_list", 0)


class Poste(models.Model):
    libelle = models.CharField(verbose_name=_("Libellé"), max_length=255)
    medecin = models.ForeignKey('Medecin', on_delete=models.PROTECT, related_name='postes', verbose_name=_("Médecin"))
    mac = models.CharField(verbose_name=_("Identifiant unique"), max_length=255, blank=True, null=True)
    old_mac = models.CharField(verbose_name=_("Ancien Identifiant unique"), max_length=255, blank=True, null=True)
    sid = models.CharField(verbose_name=_("Identifiant de sécurité"), max_length=255, blank=True, null=True)
    etabibappliction = models.ForeignKey('Etabib', on_delete=models.PROTECT, blank=True, null=True)
    updater = models.ForeignKey('Updater', on_delete=models.SET_NULL, blank=True, null=True)
    licence = models.OneToOneField('Licence', on_delete=models.PROTECT, blank=True, null=True)
    modules = models.ManyToManyField('Version', through='Installation', blank=True)
    date_derniere_connexion = models.DateTimeField(verbose_name=_('Date de la dernière connexion'), blank=True,
                                                   null=True)
    date_creation = models.DateTimeField(verbose_name=_('Date de création'), auto_now_add=True)
    desactive_apps = models.BooleanField(default=False, editable=True)
    eula = models.ForeignKey('Eula', on_delete=models.PROTECT, blank=True, null=True)
    blocked = models.BooleanField(default=False, editable=True,
                                  help_text=_("True => poste will be blocked from all updates"))

    blocked = models.BooleanField(default=False, editable=True)

    def __str__(self):
        return "%s" % self.libelle

    @property
    def simple_libelle(self):
        if "//" in self.libelle:
            try:
                return self.libelle.split("//")[0]
            except Exception:
                pass
        if "," in self.libelle and len(self.libelle.split(",")) > 2:
            return self.libelle.split(",")[0]
        return self.libelle

    @property
    def installed_apps(self):
        modules = set([])
        versions = self.modules.all()
        for version in versions:
            modules.add(version.module)
        return modules

    @property
    def daily_consommation(self):
        """
        حساب كمية النقاط المستهلكة يوميا
        :return:
        """
        return Module.consommation(self, "1")

    @property
    def weekly_consommation(self):
        """
        حساب كمية النقاط المستهلكة اسبوعيا
        :return:
        """
        return Module.consommation(self, "2")

    @property
    def monthly_consommation(self):
        """
        حساب كمية النقاط المستهلكة شهريا
        :return:
        """
        return Module.consommation(self, "3")

    @property
    def quarterly_consommation(self):
        """
        حساب كمية النقاط المستهلكة فصليا - كل ثلاثة اشهر
        :return:
        """
        return Module.consommation(self, "4")

    @property
    def yearly_consommation(self):
        """
        حساب كمية في السنة
        :return:
        """
        return Module.consommation(self, "5")

    def has_enough_points(self, app):
        """
        Check if this machine has enough points to install the application "app"
        :param app:
        :return:
        """
        if self.points:
            if app.daily_consommation:
                return self.medecin.points >= app.daily_consommation
        return False


class Medecin(models.Model):
    PUBLIC_RECU = (
        ('1', 'Hommes Seulement'),
        ('2', 'Femmes Seulement'),
    )
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
    contact = models.OneToOneField('Contact', null=True, blank=True, on_delete=models.CASCADE)
    carte = models.ForeignKey('CarteProfessionnelle', on_delete=models.SET_NULL, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    num_ordre = models.CharField(max_length=30, blank=True, null=True, verbose_name=_("Numéro d'ordre"))
    num_agrement = models.CharField(max_length=30, blank=True, null=True, verbose_name=_("Numéro d'agrément"))
    date_derniere_connexion_web = models.DateTimeField(verbose_name=_('Date de la dernière connexion web'), blank=True,
                                                       null=True)
    infos = models.CharField(max_length=255, blank=True, null=True)
    points = models.IntegerField(default=0)
    tarif_consultation = MoneyField(verbose_name=_("Tarif de TéléConsultation"), max_digits=14, decimal_places=0,
                                    default_currency='DZD', null=True, blank=True)
    tarif_cslt_cabinet = MoneyField(verbose_name=_("Tarif de Consultation Au Cabinet"), max_digits=14, decimal_places=0,
                                    default_currency='DZD', null=True, blank=True)
    tarif_cslt_domicile = MoneyField(verbose_name=_("Tarif de Consultation à domicile"), max_digits=14,
                                     decimal_places=0,
                                     default_currency='DZD', null=True, blank=True)
    public_recu = models.CharField(choices=PUBLIC_RECU, max_length=2, null=True, blank=True)
    conventionne_chifa = models.BooleanField(verbose_name=_("Conventionné Chifa"), default=False)
    ccp = models.CharField(verbose_name=_("Numéro CCP"), max_length=10, blank=True, null=True)
    cle = models.CharField(verbose_name=_("Clé"), max_length=2, blank=True, null=True)
    bank = models.ForeignKey("Bank", on_delete=models.DO_NOTHING, null=True, blank=True)
    bank_agence = models.CharField(verbose_name=_("Agence"), max_length=5, null=True, blank=True)
    bank_compte = models.CharField(verbose_name=_("Numéro du Compte"), max_length=10, blank=True, null=True)
    bank_rib = models.CharField(verbose_name=_("Clé RIB"), max_length=2, blank=True, null=True)

    solde = MoneyField(verbose_name=_("Solde"), max_digits=14, decimal_places=0,
                       default_currency='DZD', default=0,
                       null=True, blank=True)

    def non_blocked_postes(self):
        return self.postes.filter(blocked=False)

    def __str__(self):
        if self.contact:
            return self.contact.__str__()
        return "{0} {1}".format(self.user.first_name, self.user.last_name)

    @property
    def nom(self):
        if self.user:
            return self.user.first_name

    @property
    def prenom(self):
        if self.user:
            return self.user.last_name

    @property
    def full_name(self):
        if self.user:
            if self.user.first_name and self.user.last_name:
                return "{} {}".format(self.user.first_name,
                                      self.user.last_name)
            else:
                return self.user.username

    @property
    def email(self):
        if self.user:
            return self.user.email

    @property
    def checked(self):
        if self.carte:
            return self.carte.checked

    @property
    def rejected(self):
        if self.carte:
            return self.carte.rejected

    @property
    def full_address(self):
        if self.contact:
            return "{} {} {}".format(
                self.contact.pays if self.contact.pays else "",
                self.contact.ville.region.name if self.contact.ville else ""
                , self.contact.ville.name if self.contact.ville else ""
            )
        return ""

    @cached_property
    def all_offers(self):
        # List of tuples
        # Include expired ones
        offers = ()
        # get list of prepaied offer
        fols = Facture_OffrePrep_Licence.objects.filter(facture__medecin=self)
        # filter expired offers
        for fol in fols:
            offers += ((fol.offre, fol.is_expired()),)
        # TODO: get list of custom offer
        return offers

    @cached_property
    def current_offers(self):
        # Only active offers
        offers = []
        # get list of prepaied offer
        fols = Facture_OffrePrep_Licence.objects.filter(facture__medecin=self)
        # filter expired offers
        for fol in fols:
            if not fol.is_expired():
                offers.append(fol.offre)
        # TODO: get list of custom offer
        return offers

    @cached_property
    def current_services(self):
        services = []
        for offer in self.current_offers:
            for service in offer.services:
                if service not in services:
                    services.append(service)
        return services

    @cached_property
    def licenses(self):
        # TODO: Add for custom Offers
        return Licence.objects.filter(fol_licensce_set__facture__medecin=self)

    def has_no_offer(self):
        return len(self.all_offers) == 0

    def has_access(self, s):
        service = None
        if isinstance(s, EtabibService):
            service = s.value
        elif isinstance(s, str):
            service = s

        for ser in self.current_services:
            if ser == service:
                return True
        return False

    def is_online(self):
        from teleconsultation.models import Presence
        return Presence.objects.filter(user=self.user).exists()

    def is_busy(self):
        from teleconsultation.models import Presence
        return Presence.objects.filter(user=self.user, busy=True).exists()

    @property
    def adresse(self):
        return "%s %s %s" % (
            self.contact.pays.name if self.pays else "",
            self.contact.wilaya.name if self.wilaya else "",
            self.contact.ville.name if self.ville else "",
        )

    def has_agreed_tos(self):
        return UserAgreement.objects.filter(
            user=self.user,
        ).exists()


class Grade(models.Model):
    libelle = models.CharField(verbose_name=_("Libellé"), max_length=255)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.libelle


class CarteProfessionnelle(models.Model):
    image = models.ImageField(
        blank=False, null=False, upload_to='cartes/%Y/%m/%d/', default="default_card.png",
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    "jpg", "png", "jpeg"
                ]
            )
        ]

    )
    checked = models.BooleanField(verbose_name=_("vérifié"), default=False)
    rejected = models.BooleanField(verbose_name=_("rejetée"), default=False, editable=False)
    reason = models.CharField(verbose_name=_("raison du rejet"), max_length=255, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        try:
            user = self.medecin_set.first().user
            return "carte professionnelle de {} {} {}".format(user.first_name,
                                                              user.last_name,
                                                              user.email)
        except Exception:
            return "carte professionnelle"


def get_carteid_path(instance, filename):
    print(instance.type)
    filename = f"{uuid.uuid4()}.jpg"
    today = timezone.now()
    today_path = today.strftime("%Y/%m/%d")
    if instance.type == '1':
        return os.path.join('cartes/id/', today_path, filename)
    elif instance.type == '2':
        return os.path.join('cartes/chifa/', today_path, filename)
    return "cartes/other/"


class CarteID(models.Model):
    TYPE = (
        ('1', _("Carte d'Identité")),
        ('2', _('Carte Chifa')),
    )
    image_avant = models.ImageField(
        blank=True, null=True, upload_to=get_carteid_path,
        default="default_face_card_id.png",
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    "jpg", "png", "jpeg"
                ]
            )
        ]

    )
    image_arriere = models.ImageField(
        blank=True, null=True, upload_to=get_carteid_path,
        default="default_pile_card_id.png",
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    "jpg", "png", "jpeg"
                ]
            )
        ]
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=2, choices=TYPE, default="1")

    def __str__(self):
        try:
            user = self.medecin_set.first().user
            return "Carte de {} {} {}".format(user.first_name, user.last_name, user.email)
        except Exception:
            return "CarteID"


class Facture(models.Model):
    """
    Facture play the role of an order
    """
    REDUCTION_CATEGORIE = (
        ('', '----'),
        ("0", "Remise"),
        ("1", "Rabais"),
        ("2", "Ristourne"),
    )
    REDUCTION_TYPE = (
        ('', '----'),
        ("0", "Pourcentage"),
        ("1", "Argent"),
    )
    medecin = models.ForeignKey(Medecin, on_delete=models.PROTECT, null=True, blank=True)
    partenaire = models.ForeignKey("Partenaire", on_delete=models.PROTECT, null=True, blank=True)
    detail_action = models.OneToOneField('DetailAction', on_delete=models.SET_NULL, null=True, blank=True)
    offre_perso = models.ForeignKey('OffrePersonnalise', blank=True, null=True, on_delete=models.SET_NULL,
                                    related_name="facture_pers_set")
    commercial = models.ForeignKey(User, on_delete=models.PROTECT, blank=True, null=True)
    poste = models.ForeignKey(Poste, on_delete=models.PROTECT, blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    tva = models.DecimalField(max_digits=5, decimal_places=2, default=settings.TVA)
    total = models.FloatField(verbose_name=_("Total sans TVA"), default=0)
    total_prix = models.FloatField(verbose_name=_("Total avec TVA"), default=0)
    reduction_categorie = models.CharField(choices=REDUCTION_CATEGORIE, max_length=2, null=True, blank=True)
    reduction_type = models.CharField(choices=REDUCTION_TYPE, max_length=2, null=True, blank=True)
    reduction = models.FloatField(verbose_name=_("Réduction"), default=0)
    negocie_ttc = models.BooleanField(verbose_name=_("Négocié en TTC"), default=False)
    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT, null=True, blank=True)
    ordre_paiement = models.ForeignKey(OrdreDePaiement, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        verbose_name = _("Bon de commande")
        verbose_name_plural = _("Bons des commandes")

    def __str__(self):
        return "Bon de commande N° %s" % self.id

    def save(self, *args, **kwargs):
        from core.utils import applyTVA
        _total = self.total
        self.total_prix = applyTVA(
            total=_total,
            reduction=self.reduction,
            reduction_pourcentage=self.reduction_type == self.REDUCTION_TYPE[1][0],
            reduction_money_based=self.reduction_type == self.REDUCTION_TYPE[2][0],
            tva=float(self.tva) if not self.negocie_ttc else 0
        )
        super(Facture, self).save(*args, **kwargs)

    @property
    def offre_prepa(self):
        if self.fol_facture_set:
            for fol in self.fol_facture_set.all():
                return fol.offre

    @property
    def offre_partenaire(self):
        if self.fop_facture_set.all():
            for fop in self.fop_facture_set.all():
                return fop.offre

    def offre_perso_services_set(self):
        offre_perso_services = []
        services = self.offre_perso.services if self.offre_perso else None
        if services:
            for service in services.all().distinct():
                offre_perso_services.extend(service.offre_perso_service_set.filter(offre=self.offre_perso))
            return offre_perso_services

    @cached_property
    def total_virements(self):
        total = 0
        for virement in self.virement_set.all():
            total += virement.montant
        return total

    @property
    def est_paye(self):
        if self.ordre_paiement:
            return True
        total = self.total_virements
        if self.total_prix <= total:
            return True
        return False

    def rest_a_paye(self):
        total = self.total_virements
        return self.total_prix - total


def increment_invoice_number():
    last_invoice = FactureCompany.objects.filter(numero__isnull=False).order_by('id').last()
    year = str(timezone.now().year)[-2:]
    if not last_invoice:
        return "%s00001" % year
    invoice_no = last_invoice.numero
    old_year = invoice_no[:2]
    if old_year == year:
        new_invoice_int = int(invoice_no[2:]) + 1
    else:
        new_invoice_int = 1
    new_invoice_no = str(year) + str(new_invoice_int).zfill(5)
    return new_invoice_no


class FactureCompany(models.Model):
    numero = models.CharField(max_length=50, default=increment_invoice_number, null=True, blank=True)
    numero_commande = models.CharField(max_length=50, null=True, blank=True)
    first_last_name = models.CharField(max_length=255)
    adresse = models.CharField(verbose_name="Adresse", max_length=50, null=True, blank=True)
    numeros_telephone = models.CharField(verbose_name="Téléphone", max_length=50, null=True, blank=True)
    numeros_fax = models.CharField(verbose_name="Fax ", max_length=50, null=True, blank=True)
    numero_registre_commerce = models.CharField(verbose_name="NRC", max_length=50, null=True, blank=True)
    numero_identification_fiscale = models.CharField(verbose_name="NIF", max_length=50, null=True, blank=True)
    numero_identification_domaine = models.CharField(verbose_name="NIC", max_length=50, null=True, blank=True)
    adresse_electronique = models.EmailField(verbose_name="Adresse éléctronique", max_length=50, null=True, blank=True)
    numero_article = models.CharField(verbose_name="Article N°", max_length=50, null=True, blank=True)
    numero_tin = models.CharField(verbose_name="TIN N°", max_length=50, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(verbose_name="Statut", max_length=50, null=True, blank=True)
    date_limite_reglement = models.DateField(null=True, blank=True)
    mode_de_paiement = models.CharField(verbose_name="Mode de Paiement", max_length=50, null=True, blank=True)
    remises_et_rabais = models.FloatField(verbose_name=_("REMISES ET RABAIS"), default=0)
    frais_de_livraison = models.FloatField(verbose_name=_("FRAIS DE LIVRAISON"), default=0)
    timbre = models.FloatField(verbose_name=_("TIMBRE"), default=0)
    annuler = models.BooleanField(default=False)
    commercial = models.ForeignKey(User, on_delete=models.PROTECT, blank=True, null=True)

    @property
    def total_without_tva(self):
        total = 0
        for facturecompanydetail in self.facture_company_detail.all():
            total += facturecompanydetail.detail_without_tva
        return total

    @property
    def total_with_tva(self):
        total = 0
        for facturecompanydetail in self.facture_company_detail.all():
            total += facturecompanydetail.detail_with_tva
        return total

    @property
    def total_with_tva_r_f_t(self):
        total = self.total_with_tva - self.remises_et_rabais + self.frais_de_livraison + self.timbre
        return total

    @staticmethod
    def nextInvoiceNumber():
        return increment_invoice_number()


class FactureCompanyDetail(models.Model):
    facturecompany = models.ForeignKey(FactureCompany, null=True, blank=True, on_delete=models.CASCADE,
                                       related_name="facture_company_detail")
    designation = models.CharField(verbose_name="Désignation", max_length=50, null=True, blank=True)
    quantity = models.IntegerField(verbose_name=_("QTY"))
    montant = models.FloatField(verbose_name=_("PRIX HT"), default=0)
    pourcentage_tva = models.FloatField(verbose_name=_("Pourcentage TVA"), default=0)
    date_creation = models.DateTimeField(auto_now_add=True)

    @property
    def detail_without_tva(self):
        total = (self.montant * self.quantity)
        return total

    @property
    def detail_mantant_tva(self):
        total = self.montant * self.pourcentage_tva / 100 * self.quantity
        return total

    @property
    def detail_with_tva(self):
        total = self.montant * (1 + self.pourcentage_tva / 100) * self.quantity
        return total


class Facture_OffrePrep_Licence(models.Model):
    licence = models.ForeignKey("Licence", on_delete=models.PROTECT, related_name="fol_licensce_set", null=True,
                                blank=True)
    offre = models.ForeignKey("OffrePrepaye", on_delete=models.PROTECT)
    facture = models.ForeignKey("Facture", on_delete=models.PROTECT, related_name="fol_facture_set")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_expiration = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Commande(Offres prépayée Médecin)")
        verbose_name_plural = _("Commandes(Offres prépayée Médecin)")

    def is_expired(self):
        if self.offre.licences_nbjours == 0:  # illimité
            return False
        if self.date_expiration < timezone.now():
            return True
        return False

    def save(self, *args, **kwargs):
        if self.offre.licences_nbjours == 0:  # illimité
            pass
        else:
            if self.date_creation:
                self.date_expiration = self.date_creation + datetime.timedelta(days=self.offre.licences_nbjours)
            else:
                self.date_expiration = timezone.now() + datetime.timedelta(days=self.offre.licences_nbjours)
        super(Facture_OffrePrep_Licence, self).save(*args, **kwargs)


class Virement(models.Model):
    METHODE_CHOICES = (
        ("1", _("ESPECE")),
        ("2", _("TPE")),
        ("3", _("VIRMENT CCP SOCIETE")),
        ("4", _("VIRMENT CCP RESPONSABLE")),
        ("5", _("VIRMENT BANCAIRE")),
        ("6", _("EPAIEMENT")),
        ("7", _("Chèque")),
    )
    montant = models.IntegerField()
    image = models.ImageField(
        upload_to="uploads/virements", null=True, blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    "jpg", "png", "jpeg"
                ]
            )
        ]
    )
    date_creation = models.DateTimeField(verbose_name=_("Date d'ajout"), )
    date_maj = models.DateTimeField(verbose_name=_("Date de mise à jour"), auto_now=True)
    facture = models.ForeignKey(Facture, on_delete=models.PROTECT, null=True, blank=True)
    ajouter_par = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    methode_paiement = models.CharField(max_length=2, choices=METHODE_CHOICES, null=True, blank=True)
    ref = models.CharField(verbose_name=_("Référence"), max_length=255, null=True, blank=True)
    verifie = models.BooleanField(default=True)

    def __str__(self):
        return "%s" % self.montant

    def save(self, *args, **kwargs):
        if not self.date_creation:
            self.date_creation = timezone.now()
        super(Virement, self).save(*args, **kwargs)


class Specialite(models.Model):
    libelle = models.CharField(max_length=100)
    libelle_ar = models.CharField(max_length=100, null=True, blank=True)
    point = models.IntegerField(null=True, blank=True, help_text=_("Points de catégorisation"))
    icon = models.ImageField(
        upload_to='specialites', null=True, blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    "jpg", "png", "jpeg"
                ]
            )
        ]
    )

    def __str__(self):
        lang = get_language()
        if lang == "ar":
            return self.libelle_ar or self.libelle
        return self.libelle


class Qualification(models.Model):
    libelle = models.CharField(max_length=255)

    def __str__(self):
        return self.libelle


class Service(models.Model):
    designation = models.CharField(max_length=255, verbose_name=_("Désignation"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    tarif = models.FloatField(verbose_name=_("Tarif"))
    nb_jours = models.IntegerField(blank=True, null=True, verbose_name=_("Nombre de jours"))
    creer_licence = models.BooleanField(default=False, verbose_name=_("Nécessité d'une licence"))
    besoin_licence = models.BooleanField(default=False, verbose_name=_("Besion d'une licence"))
    date_creation = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return self.designation


class ServiceFedilite(models.Model):
    libelle = models.CharField(max_length=200, verbose_name=_("Libellé"))
    code = models.CharField(max_length=10, blank=True, null=True, verbose_name=_("Code"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    nb_points = models.IntegerField(blank=True, null=True, verbose_name=_("Nombre de points"))
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))

    def __str__(self):
        return self.libelle

    class Meta:
        verbose_name = "Service de fédilité"
        verbose_name_plural = "Services de fédilité"


class OffrePrepaye(models.Model):
    SERVICE_CHOICES = (
        ("1", "eTabib Workspace"),
        ("2", "Agenda en ligne"),
        ("3", "eTabib Care"),
        ("4", "eTabib visio"),
        ("5", "eTabib Store"),
        ("6", "Ordonnancier digital"),
        ("7", "etabib Annuaire"),
        ("8", "Télécharger Les Applis eTabib® Store"),
        ("9", "Clinique virtuelle"),
    )
    CRITERE_REDUCTION = (
        ("1", "Délai 15 jours aprés la validation"),
    )
    SAV_CHOICES = (
        ("1", "BASE"),
        ("2", "PRO"),
        ("3", "PREMIUM"),
    )
    libelle = models.CharField(max_length=255, verbose_name=_("Libellé"))
    slug = models.SlugField(blank=True, editable=False, max_length=255)
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    date_creation = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    date_expiration = models.DateTimeField(verbose_name=_("Date d'expiration"))
    date_debut = models.DateTimeField(verbose_name=_("Date de début"))
    points = models.IntegerField(verbose_name=_("Quantité de points"))
    prix_unite = models.IntegerField(verbose_name=_("Prix unitaire d'un point"))
    reduction_intervention = models.IntegerField(default=0, validators=[MaxValueValidator(100), MinValueValidator(0)],
                                                 verbose_name=_("Pourcentage de réduction pour les interventions"))
    reduction_achat_points = models.IntegerField(default=0, validators=[MaxValueValidator(100), MinValueValidator(0)],
                                                 verbose_name=_("Pourcentage de réduction pour l'achat des points"))
    reduction_modules = models.IntegerField(default=0, validators=[MaxValueValidator(100), MinValueValidator(0)],
                                            verbose_name=_("Pourcentage de réduction pour l'utilisations des modules"))
    licences_nbjours = models.IntegerField(blank=False, null=False, verbose_name=_("Nombre de jours de la licence"),
                                           help_text=_("Pour l'illimité vous mettez 0"))
    licences_nbjours_desc = models.CharField(max_length=200, blank=True, null=True,
                                             verbose_name=_("Durée d'abonnement (text)"),
                                             help_text=_("Utilisé dans la page des offres"))
    prix = models.IntegerField(verbose_name=_("Prix de l'offre"), help_text=_("en dinar algérien"), blank=True,
                               null=True)
    prix_reduit = models.IntegerField(verbose_name=_("Prix de l'offre(Réduit)"), help_text=_("en dinar algérien"),
                                      null=True, blank=True)
    critere_reduction = models.CharField(verbose_name=_("Critère de réduction"), max_length=3,
                                         choices=CRITERE_REDUCTION, null=True, blank=True)
    avantages = models.ManyToManyField('ServiceFedilite', blank=True, verbose_name=_("Services de fidélité"))
    services = MultiSelectField(choices=SERVICE_CHOICES, default=("1", "2", "3"), max_length=50)
    sav = models.CharField(verbose_name=_("Support/SAV"), max_length=3, choices=SAV_CHOICES, null=True, blank=True)

    def __str__(self):
        return self.libelle

    @property
    def expiration_pourcentage(self):
        if self.status == OfferStatus.ACTIVE:
            whole = self.date_expiration - self.date_debut
            part = self.date_expiration - timezone.now()
            return 100 - int((part.total_seconds() / whole.total_seconds()) * 100)

    @property
    def status(self):
        if self.date_debut > timezone.now():
            return OfferStatus.INACTIVE
        elif self.date_expiration < timezone.now():
            return OfferStatus.EXPIRED
        else:
            return OfferStatus.ACTIVE

    @property
    def prix_mensuel(self):
        return int(self.prix / (self.licences_nbjours / 30))

    @property
    def prix_mensuel_reduit(self):
        return int(self.prix_reduit / (self.licences_nbjours / 30))

    def has_reduction(self, obj):
        status = self.reduction_status(obj)
        return status["has_reduction"]

    def reduction_status(self, obj):
        # return tuple a booean with a number
        ##get status of the reduction
        ##get number of days before reduction expires
        medecin = None
        if isinstance(obj, User):
            if hasattr(obj, "medecin"):
                medecin = obj.medecin
        if isinstance(obj, Contact):
            if hasattr(obj, "medecin"):
                medecin = obj.medecin
            else:
                # case of a contact without an account
                return {"has_reduction": True, "days": None}
        if medecin:
            if self.critere_reduction and self.prix_reduit:
                if self.critere_reduction == self.CRITERE_REDUCTION[0][0]:  # 15 jours
                    if medecin.carte.checked:
                        date_tmp = medecin.carte.date_validation if medecin.carte.date_validation else medecin.user.date_joined
                        if (date_tmp + datetime.timedelta(days=15)) > timezone.now():
                            td = (date_tmp + datetime.timedelta(days=15)) - timezone.now()
                            return {"has_reduction": True, "days": td.days}
        return {"has_reduction": False, "days": None}

    def save(self, *args, **kwargs):
        self.slug = slugify(self.libelle, allow_unicode=True)
        super(OffrePrepaye, self).save(*args, **kwargs)

    class Meta:
        verbose_name = _("Offre prépayée pour les médecins")
        verbose_name_plural = _("Offres prépayées pour les médecins")


class OffrePersonnalise(models.Model):
    reduction = models.IntegerField(default=0, validators=[MaxValueValidator(100), MinValueValidator(0)])
    services = models.ManyToManyField('Service', through='OffrePersonnalise_Service')
    avantages = models.ManyToManyField('ServiceFedilite', blank=True)
    date_creation = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Commande(Offres personnalisée)")
        verbose_name_plural = _("Commandes(Offres personnalisée)")


class OffrePersonnalise_Service(models.Model):
    offre = models.ForeignKey('OffrePersonnalise', on_delete=models.PROTECT)
    service = models.ForeignKey('Service', on_delete=models.PROTECT, related_name="offre_perso_service_set")
    licence = models.ForeignKey('Licence', on_delete=models.PROTECT, blank=True, null=True,
                                related_name="offre_perso_licence_set")
    quantite = models.IntegerField()
    reduction = models.IntegerField(default=0, validators=[MaxValueValidator(100), MinValueValidator(0)])
    date_creation = models.DateTimeField(auto_now_add=True, blank=True, null=True)


class Licence(models.Model):
    partenaire = models.ForeignKey('Partenaire', on_delete=models.PROTECT, blank=True, null=True)
    clef = models.CharField(max_length=255, unique=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_actiavtion_licence = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.clef

    def current_offre(self):
        """
        :return: an instance of Facture_OffrePrep_Licence
        or an instance of OffrePersonnalise_Service
        depends on the offer if is a prepayed offer or a customized offer
        """
        try:
            if self.fol_licensce_set.count() > 0:
                """
                    :return the first element of the set
                """
                return self.fol_licensce_set.last()

            if self.offre_perso_licence_set.count() > 0:
                """
                    :return the first element of the set
                """
                return self.offre_perso_licence_set.last()
        except Exception as e:
            return None
        return None

    @property
    def remaining_days(self):
        if self.date_actiavtion_licence:
            try:
                co = self.current_offre()
                if co:
                    if isinstance(co, Facture_OffrePrep_Licence):
                        if co.offre.licences_nbjours == 0:  # unlimited offer
                            return LicenceStatus.UNLIMITED.value
                        else:  # limited offer
                            now = timezone.now()
                            diff = co.offre.licences_nbjours - (now - self.date_actiavtion_licence).days
                            return diff if diff > 0 else 0
                    if isinstance(co, OffrePersonnalise_Service):
                        if co.service.nb_jours:
                            now = timezone.now()
                            diff = co.service.nb_jours - (now - self.date_actiavtion_licence).days
                            return diff if diff > 0 else 0

            except Exception as e:
                pass
        return 0

    @property
    def remaining_days_percent(self):
        r = self.remaining_days
        co = self.current_offre()
        try:
            if isinstance(co, Facture_OffrePrep_Licence):
                return int(100 * float(r) / float(co.offre.licences_nbjours))
            elif isinstance(co, OffrePersonnalise_Service):
                return int(100 * float(r) / float(co.service.nb_jours))
        except Exception as e:
            pass
        return 0


class Contact(models.Model):
    GENDER_CHOICES = (
        ("HOMME", _("HOMME")),
        ("FEMME", _("FEMME"))
    )
    SOURCE_CHOICES = (
        ("1", _("Le client se déplace chez nous")),
        ("2", _("Le client nous envoi un SMS")),
        ("3", _("Le client nous appelle par tel")),
        ("4", _("Le client nous envoi un mail")),
        ("5", _("Le client nous envoi un message réseau sociaux")),
        ("6", _("Le client nous laisse un message sur le site")),
        ("7", _("cest un prospect issue de notre recherche")),
        ("8", _("Le client inscrit sur notre site")),
        ("9", _("Société savante")),
        ("10", _("Facebook")),
        ("11", _("LinkedIn")),
        ("12", _("Bouche à oreille")),
        ("13", _("Par laboratoire")),
        ("14", _("SIMEM21")),
        ("15", _("LISTE FOSC")),
        ("16", _("Maps")),
    )
    Motif_CHOICES = (
        ("1", _("Demande achat")),
        ("2", _("Demande devis")),
        ("3", _("Demande essai")),
        ("4", _("Autre")),
    )
    TYPE_EXERCICE_CHOICES = (
        ("1", _("projet installation PRIVE")),
        ("2", _("PRIVE installation < 6mois")),
        ("3", _("PRIVE installation 6mois <1 ans")),
        ("4", _("PRIVE installation 1- 5 ans")),
        ("5", _("PRIVE instatllation > 5 ans")),
        ("8", _("PRIVE")),
        ("6", _("Public")),
        ("7", _("Non connu")),
    )
    TYPE_EXERCICE_CATEGORISATION = (
        ("1", 30),
        ("2", 25),
        ("3", 20),
        ("4", 10),
        ("8", 10),
        ("5", 5),
        ("6", 1),
        ("7", 0),
    )
    AGE_CATEGORISATION = (
        ((20, 28), 4),
        ((28, 35), 10),
        ((36, 45), 7),
        ((45, 60), 4),
    )
    SOURCE_CATEGORISATION = (
        ("1", 35),
        ("2", 34),
        ("3", 33),
        ("4", 32),
        ("5", 25),
        ("6", 31),
        ("7", 20),
        ("8", 20),
        ("9", 10),
        ("10", 10),
        ("11", 10),
        ("12", 10),
        ("13", 10),
        ("14", 20),
        ("15", 10),
        ("16", 10),
    )
    DATE_INSCRIPTION_CATEGORISATION = (
        (datetime.timedelta(days=1), 50),
        (datetime.timedelta(weeks=1), 30),
        (datetime.timedelta(days=15), 20),
        (datetime.timedelta(days=30), 10),
    )
    cree_par = models.ForeignKey('Operateur', verbose_name=_("Crée par"), on_delete=models.PROTECT, blank=True,
                                 null=True)
    place_id = models.CharField(max_length=255, verbose_name=_("Place id"), blank=True, null=True)
    nom = models.CharField(max_length=255, verbose_name=_("Nom"), blank=True, null=True)
    prenom = models.CharField(max_length=255, verbose_name=_("Prénom"), blank=True, null=True)
    date_naissance = models.DateField(verbose_name=_("Date de naissance"), blank=True, null=True)
    sexe = models.CharField(max_length=5, verbose_name=_("Sexe"), choices=GENDER_CHOICES, blank=True, null=True)
    adresse = models.TextField(blank=True, verbose_name=_("Adresse"), null=True)
    gps = PlainLocationField(based_fields=['ville', ], zoom=5, null=True, blank=True)
    geo_coords = PointField(null=True, blank=True, )

    fixe = models.CharField(blank=True, null=True, verbose_name=_("Téléphone Fixe"), max_length=255)
    mobile = models.CharField(max_length=255, blank=True, verbose_name=_("Téléphone Mobile (prive)"), null=True)
    mobile_1 = models.CharField(blank=True, null=True, verbose_name=_("Téléphone Mobile 1 (public)"), max_length=255)
    mobile_2 = models.CharField(max_length=255, verbose_name=_("Téléphone Mobile 2 (public)"), blank=True, null=True)

    email = models.EmailField(blank=True, null=True, verbose_name=_("Email"))
    commentaire = models.TextField(blank=True, null=True, verbose_name=_("Commentaire"))
    specialite = models.ForeignKey('Specialite', on_delete=models.DO_NOTHING, verbose_name=_("Spécialité"),
                                   blank=True,
                                   null=True)
    specialite_certificat = models.ForeignKey('Certificat', on_delete=models.DO_NOTHING,
                                              verbose_name=_("Spécialité certificat"),
                                              blank=True,
                                              null=True, related_name="contact_specialite_certificat")
    qualifications = models.ManyToManyField('Qualification', verbose_name=_("Qualifications"), blank=True)
    qualifications_certificats = models.ManyToManyField('Certificat', verbose_name=_("Qualifications Certificats"),
                                                        blank=True, related_name="contact_qualifications_certificats")

    agrement = models.ForeignKey('Certificat', on_delete=models.DO_NOTHING,
                                 verbose_name=_("Autorisation de travail (agrément ou certificat de travail)"),
                                 blank=True,
                                 null=True, related_name="contact_agrement_certificat")
    fonction = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Fonction"))
    organisme = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Organisme"))
    ville = models.ForeignKey(City, blank=True, null=True, on_delete=models.DO_NOTHING, verbose_name=_("Ville"))
    departement = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Département"))
    commune = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Commune"))
    codepostal = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("Code postal"))
    pays = models.ForeignKey(Country, blank=True, null=True, on_delete=models.DO_NOTHING, verbose_name=_("Pays"))
    type_structure = models.CharField(max_length=255, verbose_name=_("Type Structure"), blank=True, null=True)
    date_ouverture = models.DateField(verbose_name=_("Date d'ouverture"), blank=True, null=True)
    date_debut_exercice = models.DateField(verbose_name=_("Date de début d'exercice"), blank=True, null=True)
    type_exercice = models.CharField(max_length=2, choices=TYPE_EXERCICE_CHOICES, verbose_name=_("Type Exercice"),
                                     blank=True, null=True, default="7")
    rang = models.ForeignKey(Grade, on_delete=models.DO_NOTHING, verbose_name=_("Grade"), blank=True, null=True)
    experience = models.IntegerField(verbose_name=_("Années d'expériences"), blank=True, null=True, default=0)
    pageweb = models.URLField(max_length=1000, blank=True, null=True, verbose_name=_("Page Web/Site Web"))
    facebook = models.URLField(max_length=500, blank=True, null=True, verbose_name=_("Facebook"))
    twitter = models.URLField(max_length=500, blank=True, null=True, verbose_name=_("Twitter"))
    linkedin = models.URLField(max_length=500, blank=True, null=True, verbose_name=_("LinkedIn"))
    instagram = models.URLField(max_length=500, blank=True, null=True, verbose_name=_("Instagram"))
    maps_url = models.URLField(blank=True, null=True, verbose_name=_("Lien Maps"))

    source = models.CharField(max_length=2, verbose_name=_("Source"), choices=SOURCE_CHOICES, blank=True, null=True)
    motif = models.CharField(max_length=2, verbose_name=_("Motif du contact"), choices=Motif_CHOICES, blank=True,
                             null=True)
    carte = models.FileField(
        blank=True, null=True, upload_to='cartes/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg", "doc", "pdf"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    'pdf', "doc", "jpg", "png", "jpeg"
                ]
            )
        ]
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    mdp_genere = models.CharField(verbose_name=_("Mot de pass généré"), max_length=255, blank=True, null=True)
    archive = models.BooleanField(verbose_name=_("Archivé"), default=False)
    compte_test = models.BooleanField(verbose_name=_("Compte de test"), default=False)

    newsletter_history = GenericRelation(
        "enewsletter.NewsletterHistory",
        related_query_name='contacts',
        object_id_field="source_id",
        content_type_field="source_type"
    )
    objects = NonArchivedContactManager()
    archived_objects = ArchivedContactManager()
    all_objects = AllContactManager()

    def age(self):
        if self.date_naissance:
            import datetime
            return int((datetime.date.today() - self.date_naissance).days / 365.25)

    @property
    def full_name(self):
        return "{0} {1}".format(self.nom or "", self.prenom or "")

    @property
    def src_gps(self):
        if self.gps:
            return "https://maps.google.com/maps?q=%s&z=15&output=embed" % self.gps
        return ""

    @property
    def geo_coordinates(self):
        return self.geo_coords if self.geo_coords else Point(36.749658, 2.9917184, 10)

    @property
    def score(self):
        score = 0
        if self.source:
            score += dict(self.SOURCE_CATEGORISATION)[self.source]

        age = self.age()
        if age:
            for key, value in dict(self.AGE_CATEGORISATION).items():
                if age >= key[0] and age < key[1]:
                    score += value

        if self.type_exercice:
            score += dict(self.TYPE_EXERCICE_CATEGORISATION)[self.type_exercice]

        if hasattr(self, "medecin"):
            if self.medecin.user:
                diff = timezone.now() - self.medecin.user.date_joined
                for key, value in dict(self.DATE_INSCRIPTION_CATEGORISATION).items():
                    if diff < key:
                        score += value
                        break
        return score

    @property
    def percentage_complete(self):
        # TODO: complete this methode
        percent_fields = ["nom", "prenom", "date_naissance", "sexe", "adresse", "fixe", "mobile", "email",
                          "commentaire", "specialite", "fonction", "ville", "departement", "commune", "codepostal",
                          "pays", "type_structure", "date_ouverture", "date_debut_exercice", "type_exercice",
                          "pageweb", "facebook", "linkedin", "instagram", "source", "motif"]
        for field in Contact._meta.fields:
            field.get_attname_column()
            print(field)
            print(field.get_attname_column())
            print("--------------")

    def __str__(self):
        if self.nom or self.prenom:
            return "{0} {1}".format(self.nom or "", self.prenom or "")
        else:
            return "Contact {0}".format(self.pk)

    @property
    def carte_pessionnelle(self):
        carte = self.carte
        if hasattr(self, "medecin"):
            if self.medecin.carte:
                carte = self.medecin.carte.image
        if hasattr(self, "professionnelsante"):
            if self.professionnelsante.carte:
                carte = self.professionnelsante.carte.image
        return carte

    def get_emails(self):
        emails = []
        if hasattr(self, "medecin"):
            if self.medecin.user.email:
                email = self.medecin.user.email
                emails.append(email)
        elif hasattr(self, "professionnelsante"):
            if self.professionnelsante.user.email:
                email = self.professionnelsante.user.email
                emails.append(email)
        elif hasattr(self, "partenaire"):
            if self.partenaire.user.email:
                email = self.partenaire.user.email
                emails.append(email)
        if self.email:
            if self.email not in emails:
                emails.append(self.email)
        return emails

    @property
    def full_address(self):
        return "{} {} {}".format(
            self.pays if self.pays else "",
            self.ville.region.name if (self.ville and self.ville.region) else ""
            , self.ville.name if self.ville else ""
        )

    def save(self, *args, **kwargs):
        from core.utils import is_number

        if self.gps:
            points = self.gps.split(",")
            if len(points) == 2 and is_number(points[0]) and is_number(points[1]):
                self.geo_coords = Point(float(points[0]), float(points[1]))

        if self.ville:
            if not self.gps:
                if self.ville.latitude and self.ville.longitude:
                    self.geo_coords = Point(float(self.ville.latitude), float(self.ville.longitude), srid=4326)

        contact = super(Contact, self).save(*args, **kwargs)
        user = None
        if hasattr(self, "medecin"):
            user = self.medecin
        elif hasattr(self, "professionnelsante"):
            user = self.professionnelsante.user
        elif hasattr(self, "partenaire"):
            user = self.partenaire.user
        if user:
            user.first_name = self.nom
            user.last_name = self.prenom
            user.save()
        return contact


class Client(Contact):
    class Meta:
        proxy = True
        default_permissions = ()
        permissions = (
            ("can_view_client_list", "Can view client list"),
        )


class RegistredUser(User):
    class Meta:
        proxy = True
        default_permissions = ()


class Certificat(models.Model):
    file = models.FileField(
        upload_to='certificat/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg", "doc", "pdf"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    'pdf', "doc", "jpg", "png", "jpeg"
                ]
            )
        ]
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    verifie = models.BooleanField(default=False)

    @property
    def filename(self):
        return os.path.basename(self.file.name)


class OffrePartenaire(models.Model):
    libelle = models.CharField(max_length=255, verbose_name=_("Libellé"))
    slug = models.SlugField(blank=True, editable=False, max_length=255)
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    date_creation = models.DateTimeField(auto_now_add=True)
    date_expiration = models.DateTimeField(verbose_name=_("Date d'expiration"))
    date_debut = models.DateTimeField(verbose_name=_("Date de début"))
    consommation_affichage = models.IntegerField(verbose_name=_("Consomation par affichage en point"))
    consommation_clic = models.IntegerField(verbose_name=_("Consomation par clic en point"))
    points = models.IntegerField(verbose_name=_("Nb des point pack base"))
    prix = MoneyField(verbose_name=_("valeur pack"), max_digits=14, decimal_places=2, default_currency='DZD')
    prix_point = MoneyField(verbose_name=_("Prix du point"), max_digits=14, decimal_places=2, default_currency='DZD')

    def __str__(self):
        return self.libelle

    @property
    def expiration_pourcentage(self):
        if self.status == OfferStatus.ACTIVE:
            whole = self.date_expiration - self.date_debut
            part = self.date_expiration - timezone.now()
            return 100 - int((part.total_seconds() / whole.total_seconds()) * 100)

    @property
    def status(self):
        if self.date_debut > timezone.now():
            return OfferStatus.INACTIVE
        elif self.date_expiration < timezone.now():
            return OfferStatus.EXPIRED
        else:
            return OfferStatus.ACTIVE

    def save(self, *args, **kwargs):
        self.slug = slugify(self.libelle)
        super(OffrePartenaire, self).save(*args, **kwargs)

    class Meta:
        verbose_name = _('Offre pour les partenaires')
        verbose_name_plural = _('Offres pour les partenaire')


class Facture_Offre_Partenaire(models.Model):
    offre = models.ForeignKey("OffrePartenaire", on_delete=models.PROTECT)
    facture = models.ForeignKey("Facture", on_delete=models.PROTECT, related_name="fop_facture_set")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Commande(Offres prépayée Partenaire)")
        verbose_name_plural = _("Commandes(Offres prépayée Partenaire)")


def validate_image(image):
    file_size = image.file.size
    limit_mb = 2
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError("Max size of file is %s MB" % limit_mb)

    w, h = get_image_dimensions(image)
    if w != 840:
        raise ValidationError("The image is %i pixel wide. It's supposed to be 840px" % w)
    if h != 1120:
        raise ValidationError("The image is %i pixel high. It's supposed to be 1120px" % h)


def stand_validate_image(image):
    file_size = image.file.size
    limit_mb = 2
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError("Max size of file is %s MB" % limit_mb)

    w, h = get_image_dimensions(image)
    if w != 1600:
        raise ValidationError("The image is %i pixel wide. It's supposed to be 1600px" % w)
    if h != 840:
        raise ValidationError("The image is %i pixel high. It's supposed to be 840px" % h)


class Stand(models.Model):
    signaletique = models.CharField(max_length=255, verbose_name=_("Signalétique"))
    slogan = models.CharField(max_length=55, verbose_name=_("Slogan"))
    banner = models.ImageField(
        upload_to="stand/%Y/%m/%d/", default="HABILLAGE_STAND_DEFAULT.png",
        validators=[stand_validate_image, FileMimeTypeValidator(
            allowed_extensions=[
                "jpg", "png", "jpeg"
            ]
        )],
        help_text=_("L'image doit avoir une largeur de %s et une hauteur de %s,"
                    " avec une taille < %s") % ("1600px", "840px", "2Mb")
    )
    link = EmbedVideoField(blank=True, null=True, verbose_name=_("Lien vidéo"))
    publie = models.BooleanField(verbose_name=_("Publié"), default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    partner = models.OneToOneField("Partenaire", on_delete=models.CASCADE, null=True)
    salle_discussion = models.CharField(max_length=50, null=True, blank=True,
                                        verbose_name=_("Nom de la salle de discussion"))
    mot_de_passe = models.CharField(verbose_name=_("Mot de passe"), max_length=255, blank=True, null=True)

    def __str__(self):
        return self.signaletique

    def save(self, *args, **kwargs):
        self.salle_discussion = "%s" % uuid.uuid4().hex
        self.mot_de_passe = User.objects.make_random_password(length=8)
        super(Stand, self).save(*args, **kwargs)


class IbnHamzaFeed(models.Model):
    libelle = models.CharField(max_length=50, verbose_name=_("Libellé"))
    description = models.TextField(verbose_name="Description")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_expiration = models.DateTimeField(verbose_name="Date d'expiration")
    lien = models.URLField(blank=True, null=True, verbose_name="Lien")


class Patient(models.Model):
    GENDER_CHOICES = (
        ("1", _("HOMME")),
        ("2", _("FEMME"))
    )
    user = models.OneToOneField(User, null=False, blank=False, on_delete=models.CASCADE, related_name="patient")
    date_naissance = models.DateField(verbose_name=_("Date de naissance"), blank=True, null=True)
    sexe = models.CharField(verbose_name=_("Sexe"), max_length=2, choices=GENDER_CHOICES, blank=True, null=True)
    pays = models.ForeignKey(Country, on_delete=models.DO_NOTHING, verbose_name=_("Pays"), null=True, blank=True)
    wilaya = models.ForeignKey(Region, on_delete=models.DO_NOTHING, verbose_name=_("Wilaya"), null=True, blank=True)
    ville = models.ForeignKey(City, on_delete=models.DO_NOTHING, verbose_name=_("Ville"), null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    telephone = PhoneNumberField(null=True, blank=True, verbose_name=_("Téléphone"))
    solde = MoneyField(verbose_name=_("Solde"), max_digits=14, decimal_places=0,
                       default_currency='DZD', default=0,
                       null=True, blank=True)
    num_carte_id = models.CharField(verbose_name=_("N° carte Nationale"), max_length=50, null=True, blank=True)
    nin = models.CharField(verbose_name=_("N° national"), max_length=50, null=True, blank=True)
    chifa = models.CharField(verbose_name=_("N° carte chifa"), max_length=50, null=True, blank=True)
    donnees_medicales = models.JSONField(default=dict, verbose_name=_("Donnée Médicales"))
    carte_id = models.ForeignKey(CarteID, on_delete=models.DO_NOTHING, verbose_name=_("Carte d'Identité"),
                                 null=True, blank=True, related_name="carte_id")
    carte_chifa = models.ForeignKey(CarteID, on_delete=models.DO_NOTHING, verbose_name=_("Carte Chifa"),
                                    null=True, blank=True, related_name="carte_chifa")
    cree_par = models.ForeignKey(User, on_delete=models.PROTECT, blank=True, null=True, related_name="patient_set")

    @property
    def nom(self):
        if self.user:
            return self.user.first_name

    @property
    def prenom(self):
        if self.user:
            return self.user.last_name

    @property
    def full_name(self):
        if self.user:
            return "%s %s" % (self.user.first_name, self.user.last_name)

    @property
    def full_address(self):
        out = ""
        if self.pays:
            out += self.pays.name
        if self.wilaya:
            out += " " + self.wilaya.name
        if self.ville:
            out += " " + self.ville.name
        return out.strip()

    @property
    def allergies(self):
        return self.donnees_medicales.get("allergies", [])

    @property
    def maladies_chroniques(self):
        return self.donnees_medicales.get("maladies_chroniques", [])

    def age(self):
        if self.date_naissance:
            import datetime
            return int((datetime.date.today() - self.date_naissance).days / 365.25)

    def has_agreed_tos(self):
        return UserAgreement.objects.filter(
            user=self.user,
        ).exists()

    def is_online(self):
        from teleconsultation.models import Presence
        return Presence.objects.filter(user=self.user).exists()

    def __str__(self):
        return "{0} {1}".format(self.nom, self.prenom)

    def make_qr_code_text(self):
        from core.templatetags.utils_tags import offer_id_hash
        qr = offer_id_hash(self)
        return qr


class EquipeSoins(models.Model):
    patient = models.ForeignKey(Patient, verbose_name=_("Patient"), on_delete=models.CASCADE,
                                related_name="equipe_soins")
    professionnel = models.ForeignKey(User, verbose_name=_("Professionnel(le) de santé"), on_delete=models.CASCADE)
    confirme = models.BooleanField(default=False, verbose_name=_("Confirmé"))
    date_confirmation = models.DateTimeField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Équipe de Soins")
        verbose_name_plural = _("Équipe de Soins")
        unique_together = ('patient', 'professionnel',)

    @property
    def specialite(self):
        if hasattr(self.professionnel, "medecin"):
            return self.professionnel.medecin.contact.specialite or ""
        if hasattr(self.professionnel, "professionnelsante"):
            return self.professionnel.professionnelsante.contact.specialite or ""
        return ""

    @property
    def contact(self):
        if hasattr(self.professionnel, "medecin"):
            return self.professionnel.medecin.contact
        if hasattr(self.professionnel, "professionnelsante"):
            return self.professionnel.professionnelsante.contact
        return ""


class Documentation(models.Model):
    libelle = models.CharField(max_length=50, verbose_name=_("Libellé"))
    date_ajout = models.DateTimeField(auto_now_add=True, verbose_name="Date de ajout")
    lien = models.URLField(blank=True, null=True, verbose_name="Lien")

    def __str__(self):
        return self.libelle


class UserAgreement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_ajout = models.DateTimeField(auto_now_add=True, verbose_name="Date d'ajout")


class Bank(models.Model):
    code = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    bic = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class ProfessionnelSante(models.Model):
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
    contact = models.OneToOneField('Contact', null=True, blank=True, on_delete=models.CASCADE)
    carte = models.ForeignKey('CarteProfessionnelle', on_delete=models.SET_NULL, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Professionnel(le) de santé")
        verbose_name_plural = _("Professionnel(le)s de santé")

    @property
    def checked(self):
        if self.carte:
            return self.carte.checked

    @property
    def rejected(self):
        if self.carte:
            return self.carte.rejected


#################################
# ADS Models
################################

class PartenaireMarque(models.Model):
    image = models.ImageField(
        upload_to="trademark_logos",
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    "jpg", "png", "jpeg"
                ]
            )
        ]
    )
    designation = models.CharField(max_length=2, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    partenaire = models.ForeignKey('Partenaire', verbose_name=_("Partenaire"), on_delete=models.SET_NULL, null=True,
                                   blank=True)

    def to_json(self):
        return {"id": self.id, "image_url": "%s" % self.image.url, "image_size": self.image.size,
                "image_label": "%s" % self.image}

    @property
    def filename(self):
        return os.path.basename(self.image.name)


class Partenaire(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    contact = models.OneToOneField('Contact', null=False, blank=False, on_delete=models.PROTECT)
    raisonsocial = models.CharField(max_length=255, blank=True, null=True)
    nrc = models.CharField(max_length=100, blank=True, null=True)
    points = models.IntegerField(default=0)
    logo = models.ImageField(
        upload_to='partenaires_logs', blank=True, null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    "jpg", "png", "jpeg"
                ]
            )
        ]
    )
    banner = models.ImageField(
        upload_to='partenaires_banners', blank=True, null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    "jpg", "png", "jpeg"
                ]
            )
        ]
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    verifie = models.BooleanField(verbose_name=_("vérifié"), default=False)
    description = models.TextField(blank=True, null=True)

    representantEmail = models.CharField(max_length=255, blank=True, null=True)
    representantNom = models.CharField(max_length=255, blank=True, null=True)
    representantFct = models.CharField(max_length=255, blank=True, null=True)

    representantEmail1 = models.CharField(max_length=255, blank=True, null=True)
    representantNom1 = models.CharField(max_length=255, blank=True, null=True)
    representantFct1 = models.CharField(max_length=255, blank=True, null=True)

    representantEmail2 = models.CharField(max_length=255, blank=True, null=True)
    representantNom2 = models.CharField(max_length=255, blank=True, null=True)
    representantFct2 = models.CharField(max_length=255, blank=True, null=True)

    @property
    def nom(self):
        if self.user:
            return self.user.first_name

    @property
    def prenom(self):
        if self.user:
            return self.user.last_name

    def current_offre(self):
        factures = Facture.objects.filter(partenaire=self)
        if factures.exists():
            facture = factures.latest('id')
            if facture.fop_facture_set.count() > 0:
                fop = facture.fop_facture_set.last()
                if fop:
                    return fop.offre
        return None

    def __str__(self):
        return "%s %s" % (self.nom, self.prenom)

    def consumePoints(self, adsStatsType, source):
        offre = self.current_offre()
        points = 0
        description = ""
        if offre:
            if adsStatsType == AdsStatsType.DISPLAY:
                points = offre.consommation_affichage
                description = "Consommation d'un affichage"
                if isinstance(source, AnnonceImpressionLog):
                    source.cout = offre.consommation_affichage
                    source.save()
            elif adsStatsType == AdsStatsType.CLICK:
                points = offre.consommation_clic
                description = "Consommation d'un clic"
                if isinstance(source, AnnonceClickLog):
                    source.cout = offre.consommation_clic
                    source.save()
            if points > 0:
                ph = PointsHistory()
                ph.partenaire = self
                ph.points = -points
                ph.description = description
                ph.source = source
                ph.save()

                self.points += -points
                self.save()

    def has_published_stand(self):
        return Stand.objects.filter(publie=True, partner=self).exists()

    def get_published_stand(self):
        return Stand.objects.get(publie=True, partner=self)


class Article(PolymorphicModel, SoftDeleteModel):
    libelle = models.CharField(verbose_name=_("Libellé"), max_length=255)
    slug = models.SlugField(blank=True, editable=False, max_length=255)
    date_creation = models.DateTimeField(verbose_name=_("Date de création"), auto_now_add=True)
    partenaire = models.ForeignKey('Partenaire', on_delete=models.CASCADE)

    objects = PolymorphicManager()
    soft_objects = SoftPolyMorphDeleteManager()

    def save(self, *args, **kwargs):
        self.slug = slugify(self.libelle)
        super(Article, self).save(*args, **kwargs)


class CategorieProduit(models.Model):
    titre = TranslatedField(models.CharField(_("titre"), max_length=255, blank=True, null=True), )

    def __str__(self):
        return self.titre


class Produit(Article):
    n_enregistrement = models.CharField(verbose_name=_("N° d'enregistrement"), max_length=100, blank=True, null=True)
    description = models.TextField(verbose_name=_("Description"))
    categorie = models.ForeignKey('CategorieProduit', blank=True, null=True, on_delete=models.SET_NULL)
    marque = models.CharField(verbose_name=_("Marque"), max_length=255, blank=True, null=True)
    origine = models.CharField(verbose_name=_("Origine"), max_length=255, blank=True, null=True)
    prix = MoneyField(verbose_name=_("Prix"), max_digits=14, decimal_places=2, default_currency='DZD', null=True,
                      blank=True)
    document_hom = models.ForeignKey('ArticleDocument', on_delete=models.SET_NULL, blank=True, null=True,
                                     verbose_name=_("Document pour l'homologation"),
                                     related_name="document_hom_prd_set")
    document_aut = models.ForeignKey('ArticleDocument', on_delete=models.SET_NULL, blank=True, null=True,
                                     verbose_name=_("Document pour l'autorisation"),
                                     related_name="document_aut_prd_set")
    promotion = models.IntegerField(verbose_name=_("Promotion"), default=0,
                                    validators=[MaxValueValidator(100), MinValueValidator(0)], blank=True, null=True)
    fin_promotion = models.DateTimeField(verbose_name=_("Fin de promotion"), blank=True, null=True)

    def __str__(self):
        return self.libelle

    @property
    def prix_promotion(self):
        if self.fin_promotion:
            if self.fin_promotion > timezone.now():
                return self.prix - (self.prix * self.promotion / 100)
        return self.prix

    class Meta:
        verbose_name = "Produit de type dispositif médical"
        verbose_name_plural = "Produits de type dispositif médical"


class PrecommandeArticle(models.Model):
    cree_par = models.ForeignKey(User, on_delete=models.PROTECT, blank=True, null=True)
    article = models.ForeignKey(Article, on_delete=models.PROTECT, blank=True, null=True)
    quantite = models.IntegerField()
    date_creation = models.DateTimeField(auto_now_add=True)


class ArticleImage(models.Model):
    image = models.ImageField(
        upload_to='produits/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    "jpg", "png", "jpeg"
                ]
            )
        ]
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    article = models.ForeignKey('Article', on_delete=models.SET_NULL, blank=True,
                                null=True)

    def to_json(self):
        return {"id": self.id, "image_url": "%s" % self.image.url, "image_size": self.image.size,
                "image_label": "%s" % self.image}


class ArticleDocument(models.Model):
    document = models.FileField(
        upload_to='documents/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg", "doc", "pdf"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    'pdf', "doc", "jpg", "png", "jpeg"
                ]
            )
        ]
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    def to_json(self):
        if self.document:
            try:
                type = mimetypes.guess_type(self.document.url)[0]
            except:
                type = None
            return {"id": self.id, "file_url": "%s" % self.document.url, "file_size": self.document.size,
                    "file_label": "%s" % self.filename, "file_type": "%s" % type}
        return ""

    @property
    def filename(self):
        return os.path.basename(self.document.name)


class AutreProduit(Article):
    reference = models.CharField(verbose_name=_("Référence"), max_length=255, blank=True, null=True)
    categorie = models.CharField(verbose_name=_("Catégorie"), max_length=255, blank=True, null=True)
    marque = models.CharField(verbose_name=_("Marque"), max_length=255, blank=True, null=True)
    origine = models.CharField(verbose_name=_("Origine"), max_length=255, blank=True, null=True)
    description = models.TextField(verbose_name=_("Description"))
    prix = MoneyField(verbose_name=_("Prix"), max_digits=14, decimal_places=2, default_currency='DZD', null=True,
                      blank=True)

    def __str__(self):
        return self.libelle

    class Meta:
        verbose_name = "Produit de type autre"
        verbose_name_plural = "Produits de type autre"


class Medic(Article):
    TYPE_CHOICES = [
        ("1", 'pharmaceutique'),
        ("2", 'parapharmaceutique')
    ]
    n_enregistrement = models.CharField(verbose_name=_("N° d'enregistrement"), max_length=255)
    dci = models.ForeignKey(DciAtc, verbose_name=_("DCI"), on_delete=models.CASCADE, related_name='dci_medic_set',
                            help_text=_("le DCI selon La nomenclature ATC"))
    type = models.CharField(verbose_name=_("Type"), max_length=2, choices=TYPE_CHOICES, default="1")
    indications = models.TextField(verbose_name=_("Indications"), blank=True, null=True,
                                   help_text=_(
                                       "les indications AMM de manière unitaire si possible selon le Standard en vigueur dans la langue du marché "))
    remboursement = models.BooleanField(verbose_name=_("Remboursable"), default=False,
                                        help_text=_("l'etat de remboursement "))
    prix = MoneyField(verbose_name=_("Prix public"), max_digits=14, decimal_places=2, default_currency='DZD', null=True,
                      blank=True)
    fabriquant = models.CharField(max_length=255, blank=True, null=True)
    exploitant = models.CharField(max_length=255, blank=True, null=True)
    interactions = models.ManyToManyField(DciAtc, verbose_name=_("Intéractions"), blank=True,
                                          related_name='interactions_medic_set')
    document_aut_amm = models.ForeignKey('ArticleDocument', on_delete=models.SET_NULL, blank=True, null=True,
                                         help_text=_(
                                             "Un Document attestant l'autorisation AMM du marché concerné si le Médicament ne figure pas sur la liste du Régulateur "),
                                         verbose_name=_("Document attestant l'autorisation AMM"),
                                         related_name="document_aut_amm_medic_set")
    rcp = models.ForeignKey('ArticleDocument', on_delete=models.SET_NULL, blank=True, null=True,
                            verbose_name=_("RCP"),
                            related_name="rcp_medic_set")
    ref_etude = models.URLField(verbose_name=_("Étude de référence"), blank=True, null=True,
                                help_text=_("Lien de l'étude de référence"))

    def __str__(self):
        return self.libelle

    class Meta:
        verbose_name = "Produit de type médicament /parapharmacie"
        verbose_name_plural = "Produits de type médicament /parapharmacie"


class Annonce(PolymorphicModel, SoftDeleteModel):
    libelle = models.CharField(verbose_name=_("Libellé"), max_length=255)
    slug = models.SlugField(blank=True, editable=False, max_length=255)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)
    article = models.ForeignKey('Article', on_delete=models.CASCADE, null=True, blank=True)
    partenaire = models.ForeignKey('Partenaire', on_delete=models.CASCADE)
    external_link = models.URLField(verbose_name=_("Lien externe"), max_length=255, null=True, blank=True)

    objects = PolymorphicManager()
    soft_objects = SoftPolyMorphDeleteManager()

    def __str__(self):
        return self.libelle

    def save(self, *args, **kwargs):
        self.slug = slugify(self.libelle)
        super(Annonce, self).save(*args, **kwargs)


class AnnonceFeed(Annonce):
    titre = models.CharField(max_length=255)
    corps = models.TextField()

    def __str__(self):
        return self.titre


class AnnonceDisplay(Annonce):
    images = models.ManyToManyField('AnnonceImage', blank=True)


def get_file_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = "%s.%s" % (uuid.uuid4(), ext)
    today = timezone.now()
    today_path = today.strftime("%Y/%m/%d")
    return os.path.join('annonce/', today_path, filename)


# Use local storage in DEV to avoid Google Drive auth errors with dummy credentials
from django.conf import settings
from django.core.files.storage import FileSystemStorage

if settings.DEBUG:
    gd_storage = FileSystemStorage()
else:
    gd_storage = CustomGoogleDriveStorage()


class Video(models.Model):
    fichier = models.FileField(
        upload_to="annonces/videos/", storage=gd_storage,
        validators=[
            FileExtensionValidator(allowed_extensions=['mp4', 'avi', "mpeg"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    'mp4', "avi", "mpeg"
                ]
            )
        ]
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    @property
    def path(self):
        return self.fichier.path

    @property
    def url(self):
        return self.fichier.url

    @property
    def driveExportUrl(self):
        try:
            link = "https://drive.google.com/uc?export=download&id=%s"
            url = self.url
            if url:
                if url.startswith("https://drive.google.com/file/d/") and url.endswith("/view?usp=drivesdk"):
                    return link % url[32:-18]
        except Exception as e:
            print(e)
        return ""


class AnnonceVideo(Annonce):
    video = models.ForeignKey(Video, on_delete=models.CASCADE)


class AnnonceImage(models.Model):
    image = models.ImageField(
        upload_to=get_file_path,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    "jpg", "png", "jpeg"
                ]
            )
        ]
    )
    type = models.CharField(max_length=2, choices=settings.ADS_IMAGE_SIZE_CHOICES, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def to_json(self):
        return {"id": self.id, "image_url": "%s" % self.image.url, "image_size": self.image.size,
                "image_label": "%s" % self.image}

    @property
    def filename(self):
        return os.path.basename(self.image.name)


class AnnonceFeedBack(models.Model):
    annonce = models.ForeignKey(Annonce, on_delete=models.SET_NULL, verbose_name=_('Annonce'), null=True)
    feedback = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)


class Campagne(PolymorphicModel, SoftDeleteModel):
    libelle = models.CharField(verbose_name=_("Libellé"), max_length=255)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)
    partenaire = models.ForeignKey('Partenaire', on_delete=models.PROTECT)
    date_debut = models.DateTimeField(verbose_name=_("Date de début"), null=True, blank=True)
    date_fin = models.DateTimeField(verbose_name=_("Date de fin"), null=True, blank=True)
    active = models.BooleanField(default=False)
    verifie = models.BooleanField(verbose_name=_("Vérifiée"), default=True)

    objects = PolymorphicManager()
    soft_objects = SoftPolyMorphDeleteManager()

    @property
    def is_active(self):
        if self.verifie:
            if self.active:
                if self.date_debut and self.date_debut < timezone.now():
                    if self.date_fin and self.date_fin > timezone.now():
                        return True
        return False

    @property
    def is_valid(self):
        """
        compaign is valide if partner has enough points
        :return:
        """
        return self.partenaire.points >= 0

    def is_downloaded(self, poste):
        return CampagneStatistique.objects.filter(poste=poste, campagne=self).exists()

    def __str__(self):
        return self.libelle


class CampagneImpression(Campagne):
    CHOICES = (
        (1, _('En Ligne')),
        (2, _('eTabib Workspace')),
        (3, _('Applications de eTabib')),
        (4, _('Applications mobile')),
        (5, _('Affichage CONGRES'))
    )
    annonces = models.ManyToManyField(Annonce)
    reseaux = MultiSelectField(choices=CHOICES)
    cibles = models.ManyToManyField(Specialite, blank=True)
    toutes_specialites = models.BooleanField(verbose_name=_("Toutes les spécialités"), default=False)
    zones = models.ManyToManyField(Region, blank=True)
    toutes_zones = models.BooleanField(verbose_name=_("Toutes les zones"), default=False)
    budget_max = MoneyField(verbose_name=_("Budget MAX"), max_digits=14, decimal_places=2, default_currency='DZD',
                            null=True, blank=True)


class AnnonceImpressionLog(models.Model):
    """
    The AnnonceImpressionLog Model will record every time the ad is loaded on a page
    """
    campagne = models.ForeignKey(Campagne, on_delete=models.SET_NULL, verbose_name=_('Campagne'), null=True)
    annonce = models.ForeignKey(Annonce, on_delete=models.SET_NULL, verbose_name=_('Annonce'), null=True)
    date_impression = models.DateTimeField(verbose_name=_('date impression'))
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    reseau = models.CharField(max_length=2, choices=CampagneImpression.CHOICES, null=True, blank=True)
    cout = models.IntegerField(verbose_name=_('coût'), default=0)

    class Meta:
        verbose_name = _('Annonce Impression log')
        verbose_name_plural = _('Annonces Impressions log')


class AnnonceClickLog(models.Model):
    """
    The AnnonceClickLog Model will record every time the ad is clicked by a user
    """
    campagne = models.ForeignKey(Campagne, on_delete=models.SET_NULL, verbose_name=_('Campagne'), null=True)
    annonce = models.ForeignKey(Annonce, on_delete=models.SET_NULL, verbose_name=_('Annonce'), null=True)
    date_click = models.DateTimeField(verbose_name=_('date de clic'))
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    reseau = models.CharField(max_length=2, choices=CampagneImpression.CHOICES, null=True, blank=True)
    cout = models.IntegerField(verbose_name=_('coût'), default=0)

    class Meta:
        verbose_name = _('Annonce Clic log')
        verbose_name_plural = _('Annonces Clic log')


class CampagneStatistique(models.Model):
    """
    The CampagneStatistique Model will record every time the ad is downladed
    """
    campagne = models.ForeignKey(Campagne, on_delete=models.SET_NULL, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    poste = models.ForeignKey(Poste, on_delete=models.SET_NULL, null=True, blank=True)


class Catalogue(models.Model):
    titre = models.CharField(max_length=255, verbose_name=_("Titre"))
    npages = models.IntegerField(verbose_name=_("N°page"))
    brand = models.CharField(max_length=255, verbose_name=_("brand"))
    image = models.ImageField(
        upload_to="catalogue",
        validators=[
            validate_image,
            FileMimeTypeValidator(
                allowed_extensions=[
                    "jpg", "png", "jpeg"
                ]
            )
        ],
        help_text=_("L'image doit avoir une largeur de %s et une hauteur de %s,"
                    " avec une taille < %s") % ("840px", "1120px", "2Mb")
    )
    link = models.URLField(blank=True, null=True, verbose_name=_("Link"))
    date_creation = models.DateTimeField(auto_now_add=True)
    cree_par = models.ForeignKey(Partenaire, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.titre


#################################
# CRM Models
################################
class Operateur(models.Model):
    GENDRE = (
        ("HOMME", _("HOMME")),
        ("FEMME", _("FEMME"))
    )
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
    date_naissance = models.DateField()
    phone = models.CharField(max_length=100)
    sexe = models.CharField(max_length=5, choices=GENDRE)
    zones = models.ManyToManyField(Region, blank=True)

    def __str__(self):
        if self.user:
            return "{} {}".format(self.user.first_name, self.user.last_name)
        else:
            ""

    @property
    def full_name(self):
        if self.user:
            return "{} {}".format(self.user.first_name,
                                  self.user.last_name)


class Intervention(models.Model):
    detail_action = models.OneToOneField('DetailAction', on_delete=models.PROTECT)
    debut_execution = models.DateTimeField(verbose_name=_("Début d'exécution"), blank=True, null=True)
    duree_reelle = models.DurationField(verbose_name=_("Durée réelle"), blank=True, null=True)
    rapport = tinymce_models.HTMLField(verbose_name=_("Rapport d'intervention"))
    screenshots = models.ManyToManyField('Screenshot', verbose_name=_("Captures d'écran"), blank=True)
    probleme = models.ForeignKey('Probleme', on_delete=models.SET_NULL, blank=True, null=True,
                                 verbose_name=_("Problème"))
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "intervention fait par {0} ".format(self.detail_action.cree_par.user.get_full_name())


def get_screenshot_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = "%s.%s" % (uuid.uuid4(), ext)
    today = timezone.now().date()
    today_path = today.strftime("%Y/%m/%d")
    return os.path.join('screenshots', today_path, filename)


class Screenshot(models.Model):
    image = models.ImageField(
        blank=False, null=False, upload_to=get_screenshot_path,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    "jpg", "png", "jpeg"
                ]
            )
        ]
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.image.name

    @property
    def filename(self):
        return os.path.basename(self.image.name)


class Probleme(models.Model):
    libelle = models.CharField(verbose_name=_("Libellé"), max_length=200)
    cree_par = models.ForeignKey(Operateur, on_delete=models.PROTECT)
    date_creation = models.DateTimeField(verbose_name=_("Date de création"), auto_now_add=True)
    screenshot = models.ManyToManyField('Screenshot', verbose_name=_("Captures d'écran"), blank=True)
    descreption = tinymce_models.HTMLField(verbose_name=_("Description"))
    solution = tinymce_models.HTMLField(blank=True, null=True, verbose_name=_("Solution"))

    def __str__(self):
        return self.libelle


class Action(models.Model):
    CHOICES = (
        ("1", _('Suivi Actif')),
        ("2", _('Suivi Ponctuel')),
        ("3", _('Intervention Technique')),
        ("4", _('Demande de Formation')),
        ("5", _('Demande commerciale')),
    )
    date_debut = models.DateField(verbose_name=_("Date de début"))
    date_debut_time = models.TimeField(verbose_name=_("Heure de début"), default=datetime.time(00, 00))
    date_fin = models.DateField(verbose_name=_("Date de fin"))
    date_fin_time = models.TimeField(verbose_name=_("Heure de fin"), default=datetime.time(23, 59))
    type = models.CharField(max_length=2, choices=CHOICES, default="1", verbose_name=_("Type"))
    cree_par = models.ForeignKey(Operateur, on_delete=models.PROTECT, verbose_name=_("Créé par"),
                                 related_name="operateur_cree_set", blank=True, null=True)
    attribuee_a_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True)
    attribuee_a_id = models.PositiveIntegerField(blank=True, null=True)
    attribuee_a = GenericForeignKey('attribuee_a_type', 'attribuee_a_id')

    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, verbose_name=_("Contact"), null=True, blank=True)
    active = models.BooleanField(default=True)

    date_cloture = models.DateTimeField(blank=True, null=True, verbose_name=_("Date de clôture"))

    date_creation = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    @property
    def attribuee(self):
        if self.attribuee_a:
            if isinstance(self.attribuee_a, Group):
                return _("Groupe: %s") % self.attribuee_a
            elif isinstance(self.attribuee_a, User):
                return self.attribuee_a.get_full_name()

    @property
    def expired(self):
        if self.active:
            if self.date_fin < timezone.now().date():
                return True
        return False


class DetailActionFile(models.Model):
    file = models.FileField(
        upload_to='action/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg", "doc", "pdf"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    'pdf', "doc", "jpg", "png", "jpeg"
                ]
            )
        ]
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    def to_json(self):
        return {"id": self.id, "image_url": "%s" % self.file.url, "image_size": self.file.size,
                "image_label": "%s" % self.file}

    @property
    def filename(self):
        return os.path.basename(self.file.name)


class DetailActionAudioFile(models.Model):
    file = models.FileField(
        upload_to='action/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(allowed_extensions=['mp3', 'wav']),
            FileMimeTypeValidator(
                allowed_extensions=[
                    'mp3', 'wav'
                ]
            )
        ]
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    @property
    def filename(self):
        return os.path.basename(self.file.name)


class DetailAction(models.Model):
    TYPE_CHOICES_CMR = (
        ("0", "Prospection première tentative"),
        ("02", "Prospection deuxième tentative"),
        ("03", "Prospection troisième tentative"),
        ("04", "Prospection quatrième tentative"),
        ("05", "Clôture de la piste de prospection"),
        ("A", "Prise de contact"),
        ("B", "Présentation"),
        ("C", "Conclusion imminente"),
        ("D", "Déplacement Visite"),
        ("E", "Phase Essai"),
        ("F", "Récolte Feed Back"),
        ("P", "Proposition commerciale"),
        ("N", "Négociation"),
        ("R", "Recouvrement"),
        ("MC", "Marché conclu"),
    )
    TYPE_CHOICES_CMR_MC = (
        ("R", "Recouvrement"),
        ("I", "Assistance Technique - Intervention"),
        ("In", "Installation"),
        ("Fo", "Formation"),
        ("We", "Invitation Webinaire-Congrès"),
        ("Pa", "Inciter au parrainage"),
        ("L", "Fidélisation"),
    )
    TYPE_CHOICES_CMR_MNC = (
        ("Re", "Relance"),
        ("No", "Annonce d'une Nouveauté"),
        ("Pr", "Annonce d'une Promo"),
        ("Au", "Autre"),
    )
    TYPE_CHOICES_CMN = (
        ("L", "Fidélisation"),
    )
    TYPE_CHOICES_TEC = (
        ("I", "Intervention technique"),
    )
    DECISION_CHOICES = (
        ("0", "Relance dans"),
        ("1", "Suivi Ponctuel")
    )
    description = models.TextField(null=True, blank=True)
    type = models.CharField(choices=TYPE_CHOICES_CMR + TYPE_CHOICES_CMN + TYPE_CHOICES_TEC, max_length=2, null=True,
                            blank=True)
    action = models.ForeignKey('Action', on_delete=models.PROTECT, related_name="detail_set", )
    pj = models.ForeignKey(DetailActionFile, verbose_name=_("Pièce jointe"), on_delete=models.SET_NULL, null=True,
                           blank=True)
    audio = models.ForeignKey(DetailActionAudioFile, verbose_name=_("Fichier son"), on_delete=models.SET_NULL,
                              null=True,
                              blank=True)
    cree_par = models.ForeignKey(Operateur, on_delete=models.PROTECT, null=True, blank=True)
    decision = models.CharField(max_length=2, choices=DECISION_CHOICES, verbose_name=_("Décision à faire"), blank=True,
                                null=True)
    decision_nb_jour = models.IntegerField(null=True, verbose_name=_("Nombre de jours"), blank=True)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    def is_treated(self):
        if hasattr(self, "prochainerencontre"):
            return self.description or self.audio
        if hasattr(self, "facture"):
            return None
        if hasattr(self, "clotureaction"):
            return None
        if hasattr(self, "intervention"):
            return None
        else:
            return self.description or self.audio
        return None


class ClotureAction(models.Model):
    CATEGORISATIONS = (
        ("1", "C dans l'Année (Froid)"),
        ("2", "A dans le Semestre (Chaud)"),
        ("3", "B dans le Trimestre (Tiède)"),
        ("4", "Se refroidit"),
        ("5", "Se réchauffe"),
        ("6", "Autre"),
    )

    detail_action = models.OneToOneField(DetailAction, on_delete=models.CASCADE)
    categorisations = models.CharField(max_length=2, choices=CATEGORISATIONS[0:3])


class ProchaineRencontre(models.Model):
    detail_action = models.OneToOneField('DetailAction', on_delete=models.PROTECT)
    date_rencontre = models.DateField(verbose_name=_("Rencontrer dans"))
    date_creation = models.DateTimeField(auto_now_add=True)


class ContactezNous(models.Model):
    nom = models.CharField(max_length=255)
    email = models.EmailField()
    object = models.CharField(max_length=255)
    message = models.TextField()

    class Meta:
        verbose_name = "Contactez Nous"
        verbose_name_plural = "Contactez Nous"


class ListeProspect(models.Model):
    titre = models.CharField(max_length=255, blank=True, null=True)
    cree_par = models.ForeignKey("Operateur", verbose_name=_("Crée par"), on_delete=models.PROTECT,
                                 related_name="liste_prospect")
    commune = models.ForeignKey("crm.Ville", verbose_name=_("Commune"), on_delete=models.PROTECT, null=True, blank=True)
    specialite = models.ForeignKey(Specialite, verbose_name=_("Spécialité"), on_delete=models.PROTECT, null=True,
                                   blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    traite = models.BooleanField(verbose_name=_("Traité"), default=False)

    def __str__(self):
        return self.titre or ""

    def save(self, *args, **kwargs):
        if not self.titre:
            if self.cree_par and self.cree_par.user:
                if hasattr(self.cree_par.user, "profile"):
                    profile = self.cree_par.user.profile
                else:
                    profile = Profile.objects.create(user=self.cree_par.user)
                nb_list = profile.nb_list + 1
                self.titre = f'Liste N°: {nb_list}'
                profile.data["nb_list"] = nb_list
                profile.save()
        super(ListeProspect, self).save(*args, **kwargs)


class Prospect(models.Model):
    contact = models.OneToOneField("Contact", on_delete=models.CASCADE)
    cree_par = models.ForeignKey("Operateur", verbose_name=_("Crée par"), on_delete=models.PROTECT)
    date_creation = models.DateTimeField(auto_now_add=True)
    liste = models.ForeignKey("ListeProspect", verbose_name=_("Liste"), on_delete=models.CASCADE, null=True, blank=True)
    urgent = models.BooleanField(default=False)

    def __str__(self):
        return self.contact.__str__()


class Suivi(models.Model):
    contact = models.OneToOneField("Contact", on_delete=models.CASCADE)
    cree_par = models.ForeignKey("Operateur", verbose_name=_("Crée par"), on_delete=models.PROTECT)
    date_creation = models.DateTimeField(auto_now_add=True)
    urgent = models.BooleanField(default=False)

    def __str__(self):
        return self.contact.__str__()


class Tache(models.Model):
    cree_par = models.ForeignKey("Operateur", verbose_name=_("Crée par"), on_delete=models.PROTECT,
                                 related_name="tach_cree_par_set")
    attribuee_a = models.ForeignKey("Operateur", verbose_name=_("Attribuée à"), on_delete=models.PROTECT,
                                    related_name="tach_attr_set")
    date_creation = models.DateTimeField(auto_now_add=True)
    contact = models.OneToOneField("Contact", on_delete=models.PROTECT, null=True, blank=True)
    message = models.CharField(verbose_name=_("Message"), max_length=255, null=True, blank=True)
    termine = models.BooleanField(verbose_name=_("Terminée"), default=False)


class Eula(models.Model):
    version = models.CharField(max_length=10, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    dernier = models.BooleanField(verbose_name=_("Dernier"), default=True)
    description = tinymce_models.HTMLField(verbose_name=_("Description"))

    @staticmethod
    def getLastVersion():
        try:
            eula = Eula.objects.get(dernier=True)
            return eula
        except Eula.DoesNotExist:
            return None

    def save(self, *args, **kwargs):
        if self.dernier == True:
            Eula.objects.all().update(dernier=False)
        super(Eula, self).save(*args, **kwargs)


class DemandeInterventionImage(models.Model):
    image = models.ImageField(
        upload_to='demande_intervention/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    "jpg", "png", "jpeg"
                ]
            )
        ]
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    @property
    def filename(self):
        return os.path.basename(self.image.name)


class DemandeIntervention(models.Model):
    poste = models.ForeignKey(Poste, on_delete=models.PROTECT)
    date_demande = models.DateTimeField(auto_now_add=True)
    en_rapport_avec = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    capture = models.ForeignKey(DemandeInterventionImage, on_delete=models.PROTECT, blank=True, null=True)
    action = models.ForeignKey("Action", on_delete=models.PROTECT, blank=True, null=True)


class PinBoard(models.Model):
    titre = models.CharField(max_length=255, verbose_name=_("Titre"))
    description = models.TextField(verbose_name=_("Description"))
    date_creation = models.DateTimeField(auto_now_add=True)
    cree_par = models.ForeignKey(User, verbose_name=_("Crée par"), on_delete=models.PROTECT)

    def __str__(self):
        return self.titre


#################################
# Store Models
################################
class Module(models.Model):
    TYPE_CONSOMMATION_CHOICES = (
        ("1", _('DAILY')),
        ("2", _('WEEKLY')),
        ("3", _('MONTHLY')),
        ("4", _('QUARTERLY')),
        ("5", _('YEARLY')),
    )
    libelle = models.CharField(verbose_name=_("Libellé"), max_length=255)
    slug = models.SlugField(blank=True, editable=False, max_length=255)
    description_breve = models.CharField(verbose_name=_("Description Brève"), max_length=255, blank=True, null=True)
    description = tinymce_models.HTMLField(verbose_name=_("Description"))
    unique_id = models.CharField(verbose_name=_("Identificateur unique"), max_length=255, blank=True, null=True,
                                 help_text=_("is a unique identifier specified in the development phase "))
    # est un identifiant unique spécifié dans la phase de développement
    type_consomation = models.CharField(verbose_name=_("Type de la consommation"), max_length=10,
                                        choices=TYPE_CONSOMMATION_CHOICES)
    consomation = models.IntegerField(verbose_name=_("Consommation"), default=0)
    icon = models.ImageField(
        verbose_name=_("Icône"), upload_to="uploads/icons_modules",
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg", "ico"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    "jpg", "png", "jpeg", "ico"
                ]
            )
        ]
    )
    captures_ecran = models.ManyToManyField('Imagemodule', verbose_name=_("Captures d'écran"), blank=True)
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name=_("Date d'ajout"))
    tags = TaggableManager(blank=True, verbose_name=_("Mots clés"))

    objects = RandomManager()

    @property
    def version(self):
        try:
            v = Version.objects.get(lastversion=True, module__id=self.id)
            return v.number
        except Exception:
            return ""

    def getLastVersion(self):
        try:
            v = Version.objects.get(lastversion=True, module__id=self.id)
            return v
        except Exception:
            return None

    def compatible_with(self):
        try:
            v = Version.objects.get(lastversion=True, module__id=self.id)
            return "etabib %s" % v.compatible_with.version
        except Exception as e:
            return ""

    def is_consumed_daily(self):
        l = [x[0] for x in self.TYPE_CONSOMMATION_CHOICES]
        if self.type_consomation == l[0]:
            return True

    def is_consumed_weekly(self):
        l = [x[0] for x in self.TYPE_CONSOMMATION_CHOICES]
        if self.type_consomation == l[1]:
            return True

    def is_consumed_monthly(self):
        l = [x[0] for x in self.TYPE_CONSOMMATION_CHOICES]
        if self.type_consomation == l[2]:
            return True

    def is_consumed_quarterly(self):
        l = [x[0] for x in self.TYPE_CONSOMMATION_CHOICES]
        if self.type_consomation == l[3]:
            return True

    def is_consumed_yearly(self):
        l = [x[0] for x in self.TYPE_CONSOMMATION_CHOICES]
        if self.type_consomation == l[4]:
            return True

    @property
    def commentaires(self):
        return self.commentaire_set.all().order_by("-id")

    @property
    def note_globale(self):
        notes = Note.objects.filter(module__id=self.id).values_list('valeur', flat=True)
        return (float(sum(notes)) / max(len(notes), 1)) if notes else 5.0

    @property
    def nb_telechargement(self):
        return Installation.objects.filter(version__module__id=self.id).count()

    @property
    def nb_commentaires(self):
        return self.commentaire_set.all().count()

    def __str__(self):
        return self.libelle

    def note_medecin(self, user):
        if user:
            try:
                note = Note.objects.get(medecin__user=user, module__id=self.id)
                return note.valeur
            except Note.DoesNotExist:
                return 5.0

    def is_published(self):
        if Version.objects.filter(module__id=self.id, lastversion=True).exists():
            return True
        return False

    def etat(self, poste):
        if poste:
            inst1 = Installation.objects.filter(version__module__id=self.id,
                                                a_installer=False,
                                                a_desinstaller=False,
                                                poste=poste).exists()
            inst2 = Installation.objects.filter(version__module__id=self.id,
                                                a_installer=True,
                                                poste=poste).exists()
            inst3 = Installation.objects.filter(version__module__id=self.id,
                                                a_installer=False,
                                                a_desinstaller=True,
                                                poste=poste).exists()
            ver = Version.objects.filter(module__id=self.id, lastversion=True).exists()

            status = ModuleStatus.IS_INSTALLED if inst1 else ModuleStatus.TO_INSTALL if inst2 else ModuleStatus.TO_UNINSTALL if inst3 else ModuleStatus.NO_VERSION if not ver else ModuleStatus.NOT_INSTALLED
            return status

    @staticmethod
    def consommation(poste, type):
        """
        تقوم بحساب كمية استهلاك النقاط للمستخدِم على حسب type سواء كان
        - type == 1 => DAILY يومي
        - type == 2 => WEEKLY اسبوعي
        - type == 3 => MONTHLY شهري
        - type == 4 => QUARTERLY فصلي = 3 اشهر
        - type == 5 => YEARLY
        :param poste:
        :param type:
        :return:
        """
        if isinstance(poste, Poste):
            l = [x[0] for x in Module.TYPE_CONSOMMATION_CHOICES]
            modules = poste.installed_apps
            p = 0
            for app in modules:
                if app.etat(poste) in (ModuleStatus.IS_INSTALLED, ModuleStatus.TO_UNINSTALL):
                    if type == l[0] and app.is_consumed_daily():
                        p = p + app.consomation

                    if type == l[1] and app.is_consumed_weekly():
                        p = p + app.consomation

                    if type == l[2] and app.is_consumed_monthly():
                        p = p + app.consomation

                    if type == l[3] and app.is_consumed_quarterly():
                        p = p + app.consomation

                    if type == l[4] and app.is_consumed_yearly():
                        p = p + app.consomation
            return p

    def save(self, *args, **kwargs):
        self.slug = slugify(self.libelle)
        super(Module, self).save(*args, **kwargs)


class Imagemodule(models.Model):
    image = models.ImageField(
        upload_to="uploads/modules",
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    "jpg", "png", "jpeg"
                ]
            )
        ]
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.image.name


class Commentaire(models.Model):
    date_ajout = models.DateTimeField(auto_now_add=True)
    medecin = models.ForeignKey('Medecin', on_delete=models.PROTECT)
    module = models.ForeignKey('Module', on_delete=models.PROTECT)
    texte = models.TextField()

    class Meta:
        verbose_name = "Commentaire sur les modules"
        verbose_name_plural = "Commentaires sur les modules"


class Note(models.Model):
    date_ajout = models.DateTimeField(auto_now_add=True)
    medecin = models.ForeignKey('Medecin', on_delete=models.PROTECT)
    module = models.ForeignKey('Module', on_delete=models.PROTECT)
    valeur = models.DecimalField(max_digits=3, decimal_places=1)

    class Meta:
        verbose_name = "Note sur les modules"
        verbose_name_plural = "Notes sur les modules"


def validate_file_extension(value):
    import os
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.zip']
    if not ext.lower() in valid_extensions:
        raise ValidationError(u'File not supported!')


class Version(models.Model):
    module = models.ForeignKey('Module', verbose_name=_("Module"), on_delete=models.PROTECT)
    number = models.CharField(max_length=10, verbose_name=_("Numéro de version"),
                              validators=[RegexValidator(
                                  '^(\d+\.)+(\d+\.)+(\*|\d+)$',
                                  message=_('Version number must be in the format X.Y.Z'),
                                  code='invalid_version_number'
                              )], help_text=_("the accepted format is X.Y.Z")
                              )
    description = models.TextField(verbose_name=_("Description"), blank=True, null=True)
    lastversion = models.BooleanField(default=False, verbose_name=_("Dernière version"))
    zipfile = models.FileField(
        upload_to="uploads/versions/%Y/%m/%d/", verbose_name=_("Le fichier zip"),
        validators=[
            FileExtensionValidator(allowed_extensions=['zip']),
            FileMimeTypeValidator(
                allowed_extensions=[
                    'zip'
                ]
            )
        ]
    )
    compatible_with = models.ForeignKey('Etabib', verbose_name=_("Version Etabib Compatible"),
                                        on_delete=models.PROTECT,
                                        related_name="etabib_set")

    def __str__(self):
        return "{0} {1}".format(self.module.libelle, self.number)

    def save(self, *args, **kwargs):
        if self.lastversion == True:
            Version.objects.filter(module=self.module).update(lastversion=False)
        super(Version, self).save(*args, **kwargs)


class Installation(models.Model):
    poste = models.ForeignKey('Poste', on_delete=models.CASCADE)
    version = models.ForeignKey('Version', on_delete=models.CASCADE)
    date_creation = models.DateTimeField(auto_now_add=True)
    a_installer = models.BooleanField(default=True)
    a_desinstaller = models.BooleanField(default=False)

    @property
    def a_mettre_a_jour(self):
        if not self.version.lastversion:
            lv = self.version.module.getLastVersion()
            if lv:
                return True
        return False


class Etabib(models.Model):
    version = models.CharField(max_length=100, validators=[RegexValidator(
        '^(\d+\.)+(\d+\.)+(\*|\d+)$',
        message=_('Version number must be in the format X.Y.Z'),
        code='invalid_version_number'
    )], help_text=_("the accepted format is X.Y.Z"), unique=True)
    zipfile = models.FileField(
        upload_to='etabib',
        validators=[
            FileExtensionValidator(allowed_extensions=['zip']),
            FileMimeTypeValidator(
                allowed_extensions=[
                    'zip'
                ]
            )
        ]
    )
    consommation = models.IntegerField(default=0)
    lastversion = models.BooleanField(default=False)

    def __str__(self):
        return self.version

    @staticmethod
    def getLastVersion():
        try:
            etabib = Etabib.objects.get(lastversion=True)
            return etabib
        except Etabib.DoesNotExist:
            return None

    @staticmethod
    def getNewestVersions(id):
        if isinstance(id, int):
            return Etabib.objects.filter(id__gt=id)
        elif isinstance(id, str):
            try:
                etabib = Etabib.objects.get(version=id)
                return Etabib.getNewestVersions(etabib.id)
            except Etabib.DoesNotExist:
                return None

    @staticmethod
    def isValidVersion(version):
        return Etabib.objects.filter(version=version).exists()

    @staticmethod
    def getByVersion(version):
        try:
            etabib = Etabib.objects.get(version=version)
            return etabib
        except Etabib.DoesNotExist:
            return None

    def save(self, *args, **kwargs):
        if self.lastversion == True:
            Etabib.objects.all().update(lastversion=False)
        super(Etabib, self).save(*args, **kwargs)


class BddScript(models.Model):
    version = models.CharField(max_length=100, validators=[RegexValidator(
        '^(\d+\.)+(\d+\.)+(\d+\.)+(\*|\d+)$',
        message=_('Version number must be in the format X.Y.Z.W'),
        code='invalid_version_number'
    )], help_text=_("the accepted format is X.Y.Z.W"))
    last_version = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    zipfile = models.FileField(
        upload_to='bddscripts',
        validators=[
            FileExtensionValidator(allowed_extensions=['zip']),
            FileMimeTypeValidator(
                allowed_extensions=[
                    'zip'
                ]
            )
        ]
    )

    @staticmethod
    def getLastVersion():
        try:
            bddscript = BddScript.objects.get(last_version=True)
            return bddscript
        except BddScript.DoesNotExist:
            return None

    def save(self, *args, **kwargs):
        if self.last_version == True:
            BddScript.objects.all().update(last_version=False)
        super(BddScript, self).save(*args, **kwargs)


class Updater(models.Model):
    version = models.CharField(max_length=100, validators=[RegexValidator(
        '^(\d+\.)+(\d+\.)+(\d+\.)+(\*|\d+)$',
        message=_('Version number must be in the format X.Y.Z.W'),
        code='invalid_version_number'
    )], help_text=_("the accepted format is X.Y.Z.W"))
    last_version = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    zipfile = models.FileField(
        upload_to='updaters',
        validators=[
            FileExtensionValidator(allowed_extensions=['zip']),
            FileMimeTypeValidator(
                allowed_extensions=[
                    'zip'
                ]
            )
        ]
    )

    def __str__(self):
        return self.version

    @staticmethod
    def getLastVersion():
        try:
            updater = Updater.objects.get(last_version=True)
            return updater
        except Updater.DoesNotExist:
            return None

    def save(self, *args, **kwargs):
        if self.last_version == True:
            Updater.objects.all().update(last_version=False)
        super(Updater, self).save(*args, **kwargs)


class PointsHistory(models.Model):
    poste = models.ForeignKey(Poste, on_delete=models.CASCADE, null=True, blank=True)
    medecin = models.ForeignKey("Medecin", on_delete=models.CASCADE, null=True, blank=True)
    partenaire = models.ForeignKey("Partenaire", on_delete=models.CASCADE, null=True, blank=True)
    points = models.IntegerField()
    description = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)
    source_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True, )
    source_id = models.PositiveIntegerField(blank=True, null=True)
    source = GenericForeignKey('source_type', 'source_id')


################################
# Tracking Pixel model
################################
class TrackingPixel(models.Model):
    user_agent = models.CharField(verbose_name=_("User agent"), max_length=255, null=True, blank=True)
    ip_address = models.CharField(verbose_name=_("Ip address"), max_length=255, null=True, blank=True)
    type = models.CharField(verbose_name=_("Type"), max_length=255, blank=True, null=True)
    label = models.CharField(verbose_name=_("Label"), max_length=255, blank=True, null=True)
    create_at = models.DateTimeField(verbose_name=_('Created at'), auto_now_add=True)
    source_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True, )
    source_id = models.PositiveIntegerField(blank=True, null=True)
    source = GenericForeignKey('source_type', 'source_id')


################################
# Presigned User model
################################
class ComptePreCree(models.Model):
    username = models.CharField(verbose_name=_("Username"), max_length=150, unique=True)
    password = models.CharField(verbose_name=_("Password"), max_length=20)

    class Meta:
        verbose_name = "Compte pré-créé"
        verbose_name_plural = "Comptes pré-créés"

    @property
    def is_available(self):
        return not User.objects.filter(username=self.username).exists()


################################
# User model
################################
User = get_user_model()


class AuthBackend(ModelBackend):
    supports_object_permissions = True
    supports_anonymous_user = False
    supports_inactive_user = False

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def authenticate(request, username=None):
        print('inside custom auth')
        try:
            user = User.objects.get(username=username)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        except User.DoesNotExist:
            return None


################################
# Auxiliary model
################################
class RightsSupport(models.Model):
    """
     auxiliary model with no database table
     It can bring to your project any permission you need
    """

    class Meta:
        managed = False
        default_permissions = ()  # disable "add", "change", "delete"
        # and "view" default permissions

        permissions = (

            ('hide_ads_tab', 'Hide ads tab'),
            ('hide_campaigns_tab', 'Hide campaigns tab'),

            ####################
            #    CRM PRIVILEGES
            ####################
            # communications privileges
            ('crm_can_view_comn_dashboard', 'CRM | Can view communication dashboard'),
            ('crm_can_view_oper_dashboard', 'CRM | Can view dashboard'),
            ('crm_can_view_pin_boards', 'CRM |  Can view pin boards'),
            ('crm_can_view_comn_agenda', 'CRM |  Can view communication agenda'),
            ('crm_can_view_contact_list', 'CRM |  Can view contact list'),
            ('crm_can_view_simplified_contact_list', 'CRM |  Can view simplified contact list'),
            ('crm_can_view_follow_up_list', 'CRM |  Can view follow up list'),
            ('crm_can_view_sms_email', 'CRM | Can view sms & emails'),
            ('crm_can_view_offer_list', 'CRM | Can view offer list'),
            ('crm_can_view_expired_ponctual_events', 'CRM | Can view expired ponctual events'),

            # commercial privileges
            ('crm_can_view_comm_dashboard', 'CRM | Can view commercial dashboard'),
            ('crm_can_view_comm_agenda', 'CRM | Can view commercial agenda'),
            ('crm_can_view_prospect_list', 'CRM | Can view prospect list'),
            ('crm_can_manage_prospect_list', 'CRM | Can manage prospect list'),
            ('crm_can_manage_pistes', 'CRM | Can manage pistes'),
            ('crm_can_view_command_list', 'CRM | Can view command list'),
            ('crm_can_view_untreated_command_list', 'CRM | Can view untreated command list'),
            ('crm_can_view_bordereau_list', 'CRM | Can view bordereau list'),
            ('crm_can_view_viement_list', 'CRM | Can view viements'),
            ('crm_can_view_invoice_list', 'CRM | Can view invoice list'),

            # technicien privileges
            ('crm_can_view_tech_dashboard', 'CRM | Can view technician dashboard'),
            ('crm_can_view_tech_agenda', 'CRM | Can view technician agenda'),
            ('crm_can_view_problem_list', 'CRM | Can view problem list'),

            # common privileges
            ('crm_can_view_delg_agenda', 'CRM | Can view delegue agenda'),
            ('crm_can_create_demand', 'CRM | Can create new demand (tech, commercial ..)'),
            ('crm_can_create_command', 'CRM | Can create new command (Offre Prépayée ..)'),
            ('crm_can_create_action_punctual_follow_up', 'CRM | Can create action type: suivi ponctuel'),
            ('manage_tasks', 'CRM | Manage tasks'),

            ('crm_timeline_can_add_detail', 'CRM | timeline Can add detail'),
            ('crm_timeline_can_add_technical_detail', 'CRM | timeline Can add technical detail'),
            ('crm_timeline_can_close_piste', 'CRM | timeline Can close timeline'),
            ('crm_timeline_can_set_demand_as_done', 'CRM | timeline can set demand as done'),
            ('crm_timeline_crm_can_add_next_meeting', 'CRM | timeline Can add next meeting'),
            ('crm_timeline_can_create_account', 'CRM | timeline Can create account for new contact'),
            ('crm_timeline_can_create_untreated_order', 'CRM | timeline Can create an untreated order for new contact'),

            ####################
            #   PRIVILEGES care
            ####################
            ('care_can_view_dashboard', 'CARE | Can view dashboard'),
            ('care_can_view_profile', 'CARE | Can view profile'),
            ('can_view_etabib_store', 'CARE | Can view etabib store'),
            ('can_view_etabib_expos', 'CARE | Can view etabib expos'),
            ('can_view_etabib_econgre', 'CARE | Can view etabib econgre'),
            ('can_get_expo_badge', 'CARE | Can get expo badge'),
            ('can_veiw_e_prescription', 'CARE | Can view E-prescription'),
            ('can_veiw_teleconsultation', 'CARE | Can view teleconsultation'),
            ('can_veiw_agenda', 'CARE | Can view agenda'),
            ('can_veiw_etabib_file_sharing', 'CARE | Can view etabib file sharing'),
            ('can_view_drugs_list', 'CARE | Can view drugs list'),
            ######################################
            ('can_view_test_dicom', 'Demo | Can Test Dicom'),
        )
