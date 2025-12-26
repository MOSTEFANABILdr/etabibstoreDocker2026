import os
import uuid

from cities_light.models import Country, City
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from embed_video.fields import EmbedVideoField
from location_field.models.plain import PlainLocationField
from phonenumber_field.modelfields import PhoneNumberField
from polymorphic.models import PolymorphicModel

from core.mime_types import FileMimeTypeValidator
from core.models import Medecin
from drugs.models import Medicament


class TimeStampMixin(models.Model):
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class DetailClinique(PolymorphicModel, TimeStampMixin):
    patient = models.ForeignKey('core.Patient', null=True, blank=True, on_delete=models.PROTECT)


class OrdonnanceMedic(TimeStampMixin, models.Model):
    ordonance = models.ForeignKey('Ordonnance', null=True, blank=True, on_delete=models.DO_NOTHING)
    medicament = models.ForeignKey(Medicament, null=True, blank=True, on_delete=models.DO_NOTHING)
    conditionnement = models.CharField(max_length=255, null=True, blank=True)
    forme = models.CharField(max_length=255, null=True, blank=True)
    nom_commercial = models.CharField(max_length=255, null=True, blank=True)
    dci = models.CharField(max_length=255, null=True, blank=True)
    duree = models.CharField(max_length=255, null=True, blank=True)
    posologie = models.CharField(max_length=255, null=True, blank=True)


class Ordonnance(DetailClinique):
    medicaments = models.ManyToManyField(Medicament, through=OrdonnanceMedic)
    operateur = models.ForeignKey(Medecin, null=True, blank=True, on_delete=models.SET_NULL)


class Consultation(DetailClinique):
    motif = models.TextField(blank=True, null=True)
    interrogatoire = models.TextField(blank=True, null=True)
    examen_clinique = models.TextField(blank=True, null=True)
    examen_demande = models.TextField(blank=True, null=True)
    resultat_examen = models.TextField(blank=True, null=True)
    diag_suppose = models.TextField(blank=True, null=True)
    diag_retenu = models.TextField(blank=True, null=True)
    conduite_tenir = models.TextField(blank=True, null=True)
    operateur = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)


def document_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = "%s.%s" % (uuid.uuid4(), ext)
    today = timezone.now()
    today_path = today.strftime("%Y/%m/%d")
    return os.path.join('documents/', today_path, filename)


class Document(DetailClinique):
    operateur = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)
    titre = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    fichier = models.FileField(
        upload_to=document_path, null=True, blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'jpg', 'png', "jpeg"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    'pdf', "doc", "jpg", "png", "jpeg"
                ]
            )
        ]
    )

    # TODO tags
    @property
    def filename(self):
        return os.path.basename(self.fichier.name)


class CliniqueVirtuelleImage(TimeStampMixin, models.Model):
    image = models.ImageField(upload_to='clinvirtimages/%Y/%m/%d/', validators=[
        FileExtensionValidator(allowed_extensions=['jpg', 'png', "jpeg"]),
        FileMimeTypeValidator(
            allowed_extensions=[
                "jpg", "png", "jpeg"
            ]
        )
    ])
    user = models.ForeignKey(User, on_delete=models.PROTECT, blank=True, null=True)
    default = models.BooleanField(default=False)


class CliniqueVirtuelle(TimeStampMixin, models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT)
    titre = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image = models.ForeignKey(CliniqueVirtuelleImage, on_delete=models.PROTECT, blank=True, null=True)
    video = EmbedVideoField(blank=True, null=True)
    pays = models.ForeignKey(Country, on_delete=models.DO_NOTHING, verbose_name=_("Pays"), null=True, blank=True)
    ville = models.ForeignKey(City, on_delete=models.DO_NOTHING, verbose_name=_("Ville"), null=True, blank=True)
    fixe = PhoneNumberField(null=True, blank=True, verbose_name=_("Téléphone Fixe"))
    mobile = PhoneNumberField(null=True, blank=True, verbose_name=_("Téléphone Mobile"))
    pageweb = models.URLField(max_length=1000, blank=True, null=True, verbose_name=_("Page Web/Site Web"))
    facebook = models.URLField(max_length=500, blank=True, null=True, verbose_name=_("Facebook"))
    instagram = models.URLField(max_length=500, blank=True, null=True, verbose_name=_("Instagram"))
    gps = PlainLocationField(based_fields=['ville', ], zoom=5, null=True, blank=True)
    prestations = models.TextField(verbose_name=_("Prestations"), null=True, blank=True)
    salle_discussion = models.CharField(max_length=50, null=True, blank=True,
                                        verbose_name=_("Nom de la salle de discussion"))
    mot_de_passe = models.CharField(verbose_name=_("Mot de passe"), max_length=255, blank=True, null=True, )

    @property
    def contact(self):
        if hasattr(self.user, "medecin"):
            return self.user.medecin.contact

    def save(self, *args, **kwargs):
        self.salle_discussion = "%s" % uuid.uuid4().hex
        self.mot_de_passe = User.objects.make_random_password(length=8)
        super(CliniqueVirtuelle, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.titre or ("CliniqueVirtuelle N° %s" % self.id)}'
