from datetime import timedelta

from dateutil import parser
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from post_office import mail

from core.models import Contact
from etabibWebsite import settings
from smsicosnet.utils import send_sms_icosnet


class Newsletter(models.Model):
    TYPE_CHOICES = (
        ("0", "Mail"),
        ("1", "Sms"),
    )
    DESTINATION_CHOICES = (
        ("0", "Patients"),
        ("1", "Médecins"),
        ("2", "Client"),
        ("3", "User"),
        ("4", "Contact"),
    )
    EXP_CHOICES = (
        ("0", "Avant (exact)"),
        ("1", "Après (exact)"),
        ("2", "Après (Ou plus)"),
        ("3", "Autre"),
    )
    CRITERIA_CHOICES = (
        ("1", "Inscription"),
        ("2", "Validation"),
        ("3", "Connexion"),
        ("4", "Inscrit mais n'a pas choisi de profil patient"),
        ("5", "Inscrit médecin mais pas activé"),
        ("6", "Expiration de l'abonnement"),
        ("7", "Autre"),
    )
    title = models.CharField(
        max_length=200, verbose_name=_('Titre')
    )
    slug = models.SlugField(db_index=True, max_length=255, unique=True, editable=False)
    destination = models.CharField(verbose_name=_('Destination'), max_length=2, choices=DESTINATION_CHOICES)
    type = models.CharField(verbose_name=_("Type"), max_length=2, choices=TYPE_CHOICES, default="0")
    criteria_exp = models.CharField(verbose_name=_('Condition'), max_length=2, choices=EXP_CHOICES, default="1")
    criteria_days = models.IntegerField(verbose_name=_('x Jour(s)'), blank=True, null=True)
    criteria = models.CharField(verbose_name=_('Critères'), max_length=255, choices=CRITERIA_CHOICES, blank=True,
                                null=True)
    criteria_json = models.JSONField(verbose_name=_('Critères'), blank=True, null=True)
    create_date = models.DateTimeField(verbose_name=_('Date de création'), auto_now_add=True)
    update_date = models.DateTimeField(verbose_name=_('Date de modification'), auto_now=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title, allow_unicode=True)
        super(Newsletter, self).save(*args, **kwargs)

    def is_email(self):
        return self.type == self.TYPE_CHOICES[0][0]

    def is_sms(self):
        return self.type == self.TYPE_CHOICES[1][0]

    def _make_query(self):
        # filter by destination
        users = User.objects.none()
        count = self.message_set.filter(draft=False).count()
        if count == 0:
            return users
        if not self.destination == Newsletter.DESTINATION_CHOICES[4][0]:

            if self.destination == Newsletter.DESTINATION_CHOICES[0][0]:  # for patients
                users = User.objects.filter(patient__isnull=False)
            elif self.destination == Newsletter.DESTINATION_CHOICES[1][0]:  # for doctors
                users = User.objects.filter(Q(medecin__isnull=False) | Q(professionnelsante__isnull=False))
            elif self.destination == Newsletter.DESTINATION_CHOICES[2][0]:  # for Client
                users = User.objects.filter(
                    Q(medecin__isnull=False) & (
                            Q(medecin__facture__ordre_paiement__isnull=False) |
                            Q(medecin__facture__virement_set__isnull=False)
                    )
                )
            elif self.destination == Newsletter.DESTINATION_CHOICES[3][0]:  # for User
                users = User.objects.filter(operateur__isnull=True)

            # filter by criteria
            selectedDate = None
            if self.criteria_exp in (self.EXP_CHOICES[1][0], self.EXP_CHOICES[2][0]):  # Après
                selectedDate = (timezone.now() - timedelta(days=self.criteria_days)).date()
            elif self.criteria_exp == self.EXP_CHOICES[0][0]:  # Avant exact
                selectedDate = (timezone.now() + timedelta(days=self.criteria_days)).date()

            if self.criteria in Newsletter.CRITERIA_CHOICES[0][0]:  # Inscription
                if selectedDate:
                    if self.criteria_exp in self.EXP_CHOICES[2][0]:
                        users = users.filter(date_joined__date__lte=selectedDate)
                    else:
                        users = users.filter(date_joined__date=selectedDate)

            elif self.criteria in Newsletter.CRITERIA_CHOICES[1][0]:  # Validation
                if selectedDate:
                    if self.criteria_exp in self.EXP_CHOICES[2][0]:
                        users = users.filter(
                            Q(medecin__carte__checked=True) &
                            Q(medecin__carte__date_validation__date__lte=selectedDate)
                        )
                    else:
                        users = users.filter(
                            Q(medecin__carte__checked=True) &
                            Q(medecin__carte__date_validation__date=selectedDate)
                        )

            elif self.criteria in Newsletter.CRITERIA_CHOICES[2][0]:  # Connexion
                if selectedDate:
                    if self.criteria_exp in self.EXP_CHOICES[2][0]:
                        users = users.filter(
                            last_login__date__lte=selectedDate
                        )
                    else:
                        users = users.filter(
                            last_login__date=selectedDate
                        )

            elif self.criteria in Newsletter.CRITERIA_CHOICES[3][0]:  # Inscrit mais n'a pas choisi de profil patient
                users = users.filter(
                    groups__isnull=True
                )

            elif self.criteria in Newsletter.CRITERIA_CHOICES[4][0]:  # Inscrit médecin mais pas activé
                # None: doctor is not activated it means that he did not send us a professional card
                users = users.filter(
                    Q(medecin__isnull=False, medecin__carte__isnull=True) |
                    Q(professionnelsante__isnull=False, professionnelsante__carte__isnull=True)
                )
                if selectedDate:
                    if self.criteria_exp in self.EXP_CHOICES[2][0]:
                        users = users.filter(date_joined__date__lte=selectedDate)
                    else:
                        users = users.filter(date_joined__date=selectedDate)

            elif self.criteria in Newsletter.CRITERIA_CHOICES[5][0]:  # Expiration d'une offre
                if selectedDate:
                    if self.criteria_exp in self.EXP_CHOICES[2][0]:
                        users = users.filter(
                            medecin__facture__fol_facture_set__date_expiration__date__lte=selectedDate,
                        )
                    else:
                        users = users.filter(
                            medecin__facture__fol_facture_set__date_expiration__date=selectedDate,
                        )
            elif self.criteria in Newsletter.CRITERIA_CHOICES[5][0]:  # Autres
                pass
            return users
        else:
            contacts = Contact.objects.filter(
                medecin__isnull=True, professionnelsante__isnull=True, partenaire__isnull=True
            )
            # filter by s
            if self.criteria_json:
                if 'regions' in self.criteria_json:
                    if self.criteria_json['regions'] and isinstance(self.criteria_json['regions'], list):
                        contacts = contacts.filter(ville__region__id__in=self.criteria_json['regions'])
                if 'specialites' in self.criteria_json:
                    if self.criteria_json['specialites'] and isinstance(self.criteria_json['specialites'], list):
                        contacts = contacts.filter(specialite__id__in=self.criteria_json['specialites'])
                if 'date_ajout' in self.criteria_json:
                    if self.criteria_json['date_ajout']:
                        contacts = contacts.filter(
                            date_creation__gte=parser.parse(self.criteria_json['date_ajout']).date())
            return contacts

    @staticmethod
    def preview():
        newsletters = Newsletter.objects.filter(active=True)
        for newsletter in newsletters:
            objs = newsletter._make_query()
            print("users: %s" % objs.count())

    @staticmethod
    def submit_queue():
        newsletters = Newsletter.objects.filter(active=True)
        for newsletter in newsletters:
            try:
                objs = newsletter._make_query()
                for message in newsletter.message_set.filter(draft=False):
                    emails = []
                    # exclude from the queryset
                    if newsletter.destination == Newsletter.DESTINATION_CHOICES[4][0]:
                        # objs is a list of contacts
                        objs = objs.filter(newsletter_history__isnull=True)[:50]
                    else:
                        # objs is a list of users
                        user_ids = NewsletterHistory.objects.filter(source_type__model="user", message=message).values_list(
                            'source_id', flat=True)
                        objs = objs.exclude(id__in=user_ids)[:50]

                    for obj in objs:
                        context = {}
                        sent = False

                        if isinstance(obj, User):
                            context.update({
                                "nom": obj.first_name,
                                "prenom": obj.first_name,
                            })
                            email = obj.email
                        elif isinstance(obj, Contact):
                            context.update({
                                "nom": obj.nom,
                                "prenom": obj.prenom,
                            })
                            email = obj.email

                        if newsletter.is_email() and email:
                            emails.append({
                                'sender': settings.DEFAULT_FROM_EMAIL,
                                'recipients': [email],
                                'subject': message.subject,
                                'message': message.content,
                                "html_message": message.html_content,
                                'priority': 'low',
                                'context': context,
                            })
                            sent =True

                        elif newsletter.is_sms():
                            if isinstance(obj, User):
                                if hasattr(obj, "medecin"):
                                    send_sms_icosnet(
                                        obj=obj.medecin.contact,
                                        message=message.content,
                                    )
                                    sent = True
                                elif hasattr(obj, "professionnelsante"):
                                    send_sms_icosnet(
                                        obj=obj.professionnelsante.contact,
                                        message=message.content,
                                    )
                                    sent = True
                                elif hasattr(obj, "patient"):
                                    send_sms_icosnet(
                                        obj=obj.patient,
                                        message=message.content,
                                    )
                                    sent = True
                            elif isinstance(obj, Contact):
                                send_sms_icosnet(
                                    obj=obj,
                                    message=message.content,
                                )
                                sent = True

                        if sent:
                            nhist = NewsletterHistory()
                            nhist.source = obj
                            nhist.message = message
                            nhist.save()
                    if emails:
                        mail.send_many(
                            emails
                        )
            except Exception as e:
                pass


class Message(models.Model):
    title = models.CharField(max_length=200, verbose_name=_('title'))
    slug = models.SlugField(verbose_name=_('slug'), max_length=255, editable=False)
    newsletter = models.ForeignKey(
        Newsletter, verbose_name=_('newsletter'), on_delete=models.CASCADE
    )
    subject = models.CharField(max_length=255, verbose_name=_("Subject"))
    content = models.TextField(verbose_name=_("Content"))
    html_content = models.TextField(verbose_name=_("Html Content"), blank=True, null=True)
    draft = models.BooleanField(default=True)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title, allow_unicode=True)
        super(Message, self).save(*args, **kwargs)


class NewsletterHistory(models.Model):
    message = models.ForeignKey(Message, verbose_name=_('message'), on_delete=models.CASCADE)
    source_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True, )
    source_id = models.PositiveIntegerField(blank=True, null=True)
    source = GenericForeignKey('source_type', 'source_id')
    create_date = models.DateTimeField(auto_now_add=True)
