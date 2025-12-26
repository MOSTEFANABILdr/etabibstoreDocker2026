from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from django.utils.translation import gettext as _
from djmoney.models.fields import MoneyField
from invitations.app_settings import app_settings
from invitations.base_invitation import AbstractBaseInvitation
from location_field.models.plain import PlainLocationField
from tinymce import models as tinymce_models

from core.models import Medecin, Video
from econgre.enums import CongreStatus, WebinarStatus
from taggit_autosuggest.managers import TaggableManager


class Congre(models.Model):
    TYPE_CHOICES = (
        ("1", _("distanciel")),
        ("2", _("présentiel")),
        ("3", _("présentiel et distanciel")),
    )
    nom = models.CharField(verbose_name=_("Libellé"), max_length=255)
    slug = models.SlugField(max_length=255, null=True, blank=True)
    description = models.TextField(verbose_name=_("Description"), blank=True, null=True)
    type = models.CharField(verbose_name=_("Type"), choices=TYPE_CHOICES, default="1", max_length=2)
    adresse = models.CharField(verbose_name=_("Adresse"), null=True, blank=True, max_length=255)
    etablissement = models.CharField(verbose_name=_("Établissement"), null=True, blank=True, max_length=255)
    emplacement = PlainLocationField(based_fields=['adresse'], zoom=5, null=True, blank=True)
    date_debut = models.DateTimeField(verbose_name=_("Date de début"))
    date_fin = models.DateTimeField(verbose_name=_("Date de fin"))
    date_limite_inscription = models.DateTimeField(verbose_name=_("Date limite d'inscription"))
    payant = models.BooleanField(default=False)
    prix = MoneyField(verbose_name=_("Prix"), max_digits=14, decimal_places=2, default_currency='DZD', default=0)
    banner_prog = models.ForeignKey("CongreImage", on_delete=models.CASCADE, null=True, blank=True,
                                    related_name="bcongre_set")
    sponsor_gold_banniere = models.ForeignKey("CongreImage", on_delete=models.CASCADE, null=True, blank=True,
                                              related_name="scongre_set")
    sponsor_gold_logo = models.ForeignKey("CongreImage", on_delete=models.CASCADE, null=True, blank=True,
                                          related_name="lcongre_set")
    autre_sponsors = models.ManyToManyField("CongreImage", blank=True)  # sponsors non gold
    tags = TaggableManager(blank=True)
    annule = models.BooleanField(verbose_name=_("Annulé"), default=False)
    publie = models.BooleanField(verbose_name=_("Publié"), default=False)
    archive = models.BooleanField(verbose_name=_("Archivé"), default=False)
    organisateur = models.ForeignKey('Organisateur', on_delete=models.PROTECT)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)

    def getBanner(self):
        default_path = '/static/img/banner.png'
        if self.banner_prog:
            return self.banner_prog.image.url
        else:
            return default_path

    def getSponsorGoldBanniere(self):
        default_path = '/static/img/sponsor-gold-banner.png'
        if self.sponsor_gold_banniere:
            return self.sponsor_gold_banniere.image.url
        else:
            return default_path

    def getsponsorGoldLogo(self):
        default_path = '/static/img/sponsor-gold-logo.png'
        if self.sponsor_gold_logo:
            return self.sponsor_gold_logo.image.url
        else:
            return default_path

    def save(self, *args, **kwargs):
        self.slug = slugify(self.nom, allow_unicode=False)
        super(Congre, self).save(*args, **kwargs)

    def has_broadcast_soon(self):
        """
        Check if this congress has at least one webinar has a BROADCASTING_SOON status
        :return:
        """
        for wb in self.webinar_set.all():
            if wb.status == WebinarStatus.BROADCASTING_SOON:
                return True
        return False

    def has_broadcast(self):
        """
        Check if this congress has at least one webinar has a BROADCASTING status
        :return:
        """
        for wb in self.webinar_set.all():
            if wb.status == WebinarStatus.BROADCASTING:
                return True
        return False

    @property
    def status(self):
        if self.archive:
            return CongreStatus.ARCHIVED
        elif not self.publie:
            return CongreStatus.NOT_PUBLISHED
        elif self.annule:
            return CongreStatus.CANCELED
        elif self.has_broadcast():
            return CongreStatus.BROADCASTING
        elif self.has_broadcast_soon():
            return CongreStatus.BROADCASTING_SOON
        elif timezone.now() > self.date_fin:
            return CongreStatus.EXPIRED
        elif timezone.now() < self.date_debut:
            return CongreStatus.INACTIVE
        else:
            return CongreStatus.ACTIVE

    def speakers(self):
        out = []
        for wb in self.webinar_set.all():
            for sp in wb.speakers.all():
                if sp not in out:
                    out.append(sp)
        return out

    def sponsors(self):
        out = []
        for wb in self.webinar_set.all():
            if wb.sponsor:
                if wb.sponsor not in out:
                    out.append(wb.sponsor)

        return out

    def __str__(self):
        return self.nom


class Sponsor(models.Model):
    SPONSOR_IMAGE_CHOICES = (
        ("1", "90x90"),
        ("2", "60x60"),
    )
    IMAGE_SIZE_CHOICES = (
        # width, #Height
        (90, 90),  # 90x90
        (60, 60),  # 60x60
    )
    image = models.ImageField(upload_to='sponsor/%Y/%m/%d/')
    type = models.CharField(max_length=2, choices=SPONSOR_IMAGE_CHOICES, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def to_json(self):
        return {"id": self.id, "image_url": "%s" % self.image.url, "image_size": self.image.size,
                "image_label": "%s" % self.image}


class CongreImage(models.Model):
    TYPE_CHOICES = (
        ('1', "Banner"),
        ('2', "Bannièrer sponsor gold"),
        ('3', "logo sponsor gold"),
        ('4', "autre sponsor"),
    )
    IMAGE_SIZE_CHOICES = (
        # width, #Height
        (595, 842),  # banner
        (1600, 150),  # Bannièrer sponsor gold
        (250, 250),  # logo sponsor gold
        (90, 90),  # Autre sponsor
    )
    image = models.ImageField(upload_to='congre/%Y/%m/%d/')
    type = models.CharField(max_length=2, choices=TYPE_CHOICES, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def to_json(self):
        return {"id": self.id, "image_url": "%s" % self.image.url, "image_size": self.image.size,
                "image_label": "%s" % self.image}


class Webinar(models.Model):
    TYPE_CHOICES = (
        ("1", "webinaire"),
        ("2", "Table Ronde"),
        ("3", "Panel"),
        ("4", "Cas Clinique interactif"),
        ("5", "Session"),
        ("6", "Quiz"),
        ("7", "Plénière"),
        ("8", "Conférence"),
        ("9", "Conférence de prestige"),
        ("10", "Flash Info"),
        ("11", "Atelier"),
        ("12", "Symposium"),
    )
    nom = models.CharField(verbose_name=_("Libellé"), max_length=255)
    slug = models.SlugField(max_length=255, null=True, blank=True)
    type = models.CharField(max_length=3, choices=TYPE_CHOICES, default="1")
    description = models.TextField(verbose_name=_("Description"), blank=True, null=True)
    salle_discussion = models.CharField(max_length=50, null=True, blank=True,
                                        verbose_name=_("Nom de la salle de discussion"))
    mot_de_passe = models.CharField(verbose_name=_("Mot de passe"), max_length=255, blank=True, null=True)
    nb_max_participant = models.IntegerField(verbose_name=_("Le nombre maximum de participants"), default=0,
                                             help_text=_("0 signifie pas de limite"))
    date_debut = models.DateField(verbose_name=_("Date"), blank=True, null=True)
    heure_debut = models.TimeField(verbose_name=_("Heure de début"), blank=True, null=True)
    heure_fin = models.TimeField(verbose_name=_("Heure de fin"), blank=True, null=True)
    date_diffustion = models.DateField(verbose_name=_("Date de diffusion"), blank=True, null=True)
    heure_debut_diffusion = models.TimeField(verbose_name=_("Heure de début"), blank=True, null=True)
    heure_fin_diffusion = models.TimeField(verbose_name=_("Heure de fin"), blank=True, null=True)
    salle_physique = models.CharField(verbose_name=_("Salle physique"), blank=True, null=True, max_length=255)
    moderateurs = models.ManyToManyField('Moderateur', blank=True)
    speakers = models.ManyToManyField('Speaker', blank=True)
    congre = models.ForeignKey('Congre', on_delete=models.PROTECT, blank=True)
    sponsor = models.ForeignKey(Sponsor, on_delete=models.CASCADE, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)
    annule = models.BooleanField(default=False)
    publie = models.BooleanField(verbose_name=_("Publié"), default=False)
    archive = models.BooleanField(verbose_name=_("Archivé"), default=False)

    @property
    def status(self):
        if self.archive:
            return WebinarStatus.ARCHIVED
        elif not self.publie:
            return WebinarStatus.NOT_PUBLISHED
        elif self.annule:
            return WebinarStatus.CANCELED
        elif timedelta(0) < (datetime.combine(self.date_debut, self.heure_debut) - datetime.now()) < timedelta(hours=1):
            return WebinarStatus.SOON
        elif datetime.combine(self.date_debut, self.heure_debut) > datetime.now():
            return WebinarStatus.NOT_STATRTED_YET
        elif self.date_diffustion and self.heure_debut_diffusion and self.heure_fin_diffusion and timedelta(0) < (
                datetime.combine(self.date_diffustion, self.heure_debut_diffusion) - datetime.now()) < timedelta(
            hours=1):
            return WebinarStatus.BROADCASTING_SOON
        elif self.date_diffustion and self.heure_debut_diffusion and self.heure_fin_diffusion and \
                datetime.combine(
                    self.date_diffustion, self.heure_debut_diffusion
                ) <= datetime.now() <= datetime.combine(
            self.date_diffustion, self.heure_fin_diffusion
        ):
            return WebinarStatus.BROADCASTING
        elif datetime.combine(self.date_debut, self.heure_fin) < datetime.now():
            return WebinarStatus.EXPIRED
        else:
            return WebinarStatus.ACTIVE

    @property
    def speaker(self):
        if self.speakers.all():
            return self.speakers.first()
        else:
            return None

    @property
    def video(self):
        if self.videos.all():
            qs = self.videos.filter(active=True)
            if qs.exists():
                return qs.first()

    def save(self, *args, **kwargs):
        self.slug = slugify(self.nom, allow_unicode=False)
        super(Webinar, self).save(*args, **kwargs)


class Organisateur(models.Model):
    user = models.OneToOneField(User, null=False, blank=False, on_delete=models.CASCADE)
    profession = models.CharField(max_length=255)
    points = models.IntegerField(default=0)

    @property
    def full_name(self):
        return "%s %s" % (self.user.first_name, self.user.last_name)

    def __str__(self):
        return self.full_name


class Moderateur(models.Model):
    user = models.OneToOneField(User, null=False, blank=False, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(auto_now_add=True)

    @property
    def full_name(self):
        return "%s %s" % (self.user.first_name, self.user.last_name)

    def __str__(self):
        return self.full_name


class Speaker(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    qualification = models.CharField(max_length=255, verbose_name=_("Qualification"), null=True, blank=True)

    @property
    def full_name(self):
        return "%s %s" % (self.user.first_name, self.user.last_name)

    def __str__(self):
        return self.full_name


class UserParticipationWebinar(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    webinar = models.ForeignKey(Webinar, on_delete=models.SET_NULL, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)


class CongressInvitation(AbstractBaseInvitation):
    INITATION_CHOICES = (
        ("1", "médecin"),
    )
    email = models.EmailField(verbose_name=_('e-mail address'),
                              max_length=app_settings.EMAIL_MAX_LENGTH)
    created = models.DateTimeField(verbose_name=_('created'),
                                   default=timezone.now)
    congre = models.ForeignKey(Congre, on_delete=models.SET_NULL, null=True)
    message = tinymce_models.HTMLField(verbose_name=_("Message"))
    type = models.CharField(max_length=2, choices=INITATION_CHOICES, default="1")

    class Meta:
        unique_together = ['email', 'congre']

    @classmethod
    def create(cls, email, inviter=None, **kwargs):
        key = get_random_string(64).lower()
        instance = cls._default_manager.create(
            email=email,
            key=key,
            inviter=inviter,
            **kwargs)
        return instance

    def key_expired(self):
        expiration_date = (
                self.sent + timedelta(
            days=app_settings.INVITATION_EXPIRY))
        return expiration_date <= timezone.now()

    def send_invitation(self, request, **kwargs):
        current_site = kwargs.pop('site', Site.objects.get_current())
        invite_url = reverse('accept-invite',
                             args=[self.key])
        invite_url = request.build_absolute_uri(invite_url)
        login_url = reverse('account_login')
        login_url = request.build_absolute_uri(login_url)
        ctx = kwargs
        ctx.update({
            'invite_url': invite_url,
            'login_url': login_url,
            'message': self.message,
            'organiser_name': "%s %s" % (self.inviter.first_name, self.inviter.last_name),
            'congress_name': self.congre.nom,
            'congress_description': self.congre.description,
            'key': self.key,
        })

        email_template = 'invitations/email/email_invite'

        from invitations.adapters import get_invitations_adapter
        get_invitations_adapter().send_mail(
            email_template,
            self.email,
            ctx)
        from django.utils import timezone
        self.sent = timezone.now()
        self.save()

        from invitations import signals
        signals.invite_url_sent.send(
            sender=self.__class__,
            instance=self,
            invite_url_sent=invite_url,
            inviter=self.inviter
        )

    def __str__(self):
        return "Invite: {0}".format(self.email)


class WebinarVideo(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    webinar = models.ForeignKey(Webinar, on_delete=models.PROTECT, related_name="videos")
    active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.pk is None:  # new object
            qs = WebinarVideo.objects.filter(webinar=self.webinar)
            if qs.exists():
                qs.update(active=False)
        super(WebinarVideo, self).save(*args, **kwargs)

    @property
    def url(self):
        return self.video.driveExportUrl


class WebinarUrl(models.Model):
    libelle = models.CharField(verbose_name=_("Libellé"), max_length=255)
    url = models.URLField(verbose_name=_("URL"))
    webinar = models.ForeignKey(Webinar, on_delete=models.PROTECT, related_name="urls")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)


class WebinarStatistique(models.Model):
    wvideo = models.ForeignKey(WebinarVideo, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    duree = models.IntegerField()
    date_vision = models.DateTimeField(auto_now_add=True)
