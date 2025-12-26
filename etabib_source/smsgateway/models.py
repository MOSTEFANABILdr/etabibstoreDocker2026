from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _
from core.models import Operateur, Contact, OffrePrepaye, Specialite, Facture_OffrePrep_Licence
from cities_light.models import City, Country, Region
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


class Critere(models.Model):
    libelle = models.CharField(verbose_name=_("Libellé"), max_length=255)
    pays = models.ForeignKey(Country, blank=True, null=True, on_delete=models.DO_NOTHING, verbose_name=_("Pays"))
    ville = models.ForeignKey(City, blank=True, null=True, on_delete=models.DO_NOTHING, verbose_name=_("Ville"))
    specialite = models.ForeignKey(Specialite, blank=True, null=True, on_delete=models.DO_NOTHING,
                                   verbose_name=_("Spécialité"))
    offre = models.ForeignKey(OffrePrepaye, blank=True, null=True, on_delete=models.PROTECT)
    cree_par = models.ForeignKey(Operateur, verbose_name=_("Crée par"), on_delete=models.PROTECT)
    date_creation = models.DateTimeField(auto_now_add=True)

    @property
    def number_problems(self):
        mobilis = []
        problems = []
        good = []
        problemsmail = []
        goodmail = []
        contacts = Contact.objects.all()
        if self.offre:
            contacts_ids = Facture_OffrePrep_Licence.objects.filter(offre=self.offre).values_list(
                "facture__medecin__contact__id", flat=True)
            contacts = contacts.filter(id__in=contacts_ids)
        if self.pays:
            contacts = contacts.filter(pays=self.pays)
        if self.ville:
            contacts = contacts.filter(ville=self.ville)
        if self.specialite:
            contacts = contacts.filter(specialite=self.specialite)

        for contact in contacts:
            if contact.mobile:
                mb = contact.mobile.replace(' ', '')
                if len(mb) == 10:
                    if contact.mobile[:2] in ["07", "06", "05"]:
                        good.append(contact.pk)
                        if contact.mobile[:2] in ["06"]:
                            mobilis.append(contact.pk)
                    else:
                        problems.append(contact.pk)
                elif len(mb) == 13:
                    if contact.mobile[:5] in ["+2137", "+2136", "+2135"]:
                        good.append(contact.pk)
                        if contact.mobile[:5] in ["+2136"]:
                            mobilis.append(contact.pk)
                    else:
                        problems.append(contact.pk)
                elif len(mb) == 14:
                    if contact.mobile[:6] in ["002137", "002136", "002135"]:
                        good.append(contact.pk)
                        if contact.mobile[:6] in ["002136"]:
                            mobilis.append(contact.pk)
                    else:
                        problems.append(contact.pk)
            elif not contact.mobile:
                problems.append(contact.pk)

            if hasattr(contact, "medecin"):
                user = contact.medecin.user
                if user.email:
                    try:
                        validate_email(user.email)
                        goodmail.append(contact.pk)
                    except ValidationError:
                        problemsmail.append(contact.pk)
            elif contact.email:
                try:
                    validate_email(contact.email)
                    goodmail.append(contact.pk)
                except ValidationError:
                    problemsmail.append(contact.pk)
            else:
                problemsmail.append(contact.pk)

        return problems, good, mobilis, problemsmail, goodmail

    def __str__(self):
        return self.libelle


class SmsModel(models.Model):
    libelle = models.CharField(verbose_name=_("Libellé"), max_length=200)
    message = models.CharField(verbose_name=_("Message"), max_length=160)

    def __str__(self):
        return self.libelle


class SMSTemplate(models.Model):
    """
    Model to hold template information from db
    """
    name = models.CharField(_('Name'), max_length=255, help_text=_("e.g: 'welcome_sms'"))
    description = models.TextField(_('Description'), blank=True,
                                   help_text=_("Description of this template."))
    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    subject = models.CharField(max_length=255, blank=True, verbose_name=_("Subject"))
    content = models.TextField(blank=True, max_length=160, verbose_name=_("Content"))
    language = models.CharField(max_length=12, verbose_name=_("Language"),
                                help_text=_("Render template in alternative language"), default='', blank=True)
    default_template = models.ForeignKey('self', related_name='translated_templates',
                                         null=True, default=None, verbose_name=_('Default template'),
                                         on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'language', 'default_template')
        ordering = ['name']

    def __str__(self):
        return u'%s %s' % (self.name, self.language)

    def save(self, *args, **kwargs):
        # If template is a translation, use default template's name
        if self.default_template and not self.name:
            self.name = self.default_template.name

        template = super().save(*args, **kwargs)
        return template


class Sms(models.Model):
    SMS_STATUS = (
        ("1", _("TOSEND")),
        ("2", _("SENT")),
        ("3", _("DELIVERED")),
        ("4", _("RECEIVED")),
    )
    SIM_NUMBER = (
        ("1", _("Sim1")),
        ("2", _("Sim2")),
    )
    priority = models.IntegerField(default="2")
    critere = models.ForeignKey(Critere, blank=True, null=True, on_delete=models.DO_NOTHING, verbose_name=_("Critere"))
    smsmodel = models.ForeignKey(SmsModel, on_delete=models.PROTECT, verbose_name=_("SmsModel"), null=True, blank=True)
    template = models.ForeignKey(SMSTemplate, on_delete=models.PROTECT, verbose_name=_("SmsTemplate"), null=True,
                                 blank=True)
    message = models.CharField(verbose_name=_("Message"), max_length=160, null=True, blank=True)
    #TODO: remove contact field after transefiring the data to source field
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, verbose_name=_("Contact"), null=True, blank=True)
    source_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True, )
    source_id = models.PositiveIntegerField(blank=True, null=True)
    source = GenericForeignKey('source_type', 'source_id')
    status = models.CharField(verbose_name=_("Status"), choices=SMS_STATUS, default="1", max_length=255)
    sim = models.CharField(verbose_name=_("Sim"), choices=SIM_NUMBER, default="1", max_length=255)
    date_creation = models.DateTimeField(auto_now_add=True)
    cree_par = models.ForeignKey(Operateur, blank=True, null=True, on_delete=models.PROTECT)

    @property
    def status_sms(self):
        if self.status == "1":
            st = _("A ENVOYÉ")
        elif self.status == "2":
            st = _("ENVOYÉ")
        elif self.status == "3":
            st = _("LIVRÉ")
        return st

    def __str__(self):
        if self.smsmodel:
            content = self.smsmodel.message
        elif self.message:
            content = self.message
        elif self.template:
            content = "Message Système"
        return content


class Listenvoi(models.Model):
    libelle = models.CharField(verbose_name=_("Libellé"), max_length=200)
    contacts = models.ManyToManyField(Contact, blank=True)
    cree_par = models.ForeignKey(Operateur, verbose_name=_("Crée par"), on_delete=models.PROTECT)
    date_creation = models.DateTimeField(auto_now_add=True)

    @property
    def mobilis_number(self):
        mobilis = []
        for contact in self.contacts.all():
            if contact.mobile:
                mb = contact.mobile.replace(' ', '')
                if len(mb) == 10:
                    if contact.mobile[:2] in ["07", "06", "05"]:
                        if contact.mobile[:2] in ["06"]:
                            mobilis.append(contact.pk)
                elif len(mb) == 13:
                    if contact.mobile[:5] in ["+2137", "+2136", "+2135"]:
                        if contact.mobile[:5] in ["+2136"]:
                            mobilis.append(contact.pk)
                elif len(mb) == 14:
                    if contact.mobile[:6] in ["002137", "002136", "002135"]:
                        if contact.mobile[:6] in ["002136"]:
                            mobilis.append(contact.pk)
            return mobilis

    def __str__(self):
        return self.libelle


class EmailModel(models.Model):
    libelle = models.CharField(verbose_name=_("Libellé"), max_length=200)
    subject = models.CharField(verbose_name=_("Sujet"), max_length=200)
    message = models.TextField(verbose_name=_("Message"))

    def __str__(self):
        return self.libelle
