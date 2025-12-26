from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from appointements.enums import RdvStatus
from core.mime_types import FileMimeTypeValidator
from core.models import Contact


def lettre_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'lettres/demande_{0}/{1}'.format(instance.demande.id, filename)


class LettreOrientation(models.Model):
    date_creation = models.DateTimeField(auto_now_add=True)
    lettre = models.FileField(
        blank=True, null=True, upload_to=lettre_path, default="lettre.jpg",
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'jpg', 'png', "jpeg"]),
            FileMimeTypeValidator(
                allowed_extensions=[
                    'pdf', "doc", "jpg", "png", "jpeg"
                ]
            )
        ]
    )
    demande = models.ForeignKey('DemandeRendezVous', on_delete=models.CASCADE, related_name="lettres")


class DemandeRendezVous(models.Model):
    TYPE_CHOICES = (
        ('1', _('En ligne')),
        ('2', _('À domicile')),
        ('3', _('Au cabinet')),
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    demandeur = models.ForeignKey(User, on_delete=models.CASCADE, related_name="applicant_drdv", blank=True, null=True)
    destinataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recipient_drdv", blank=True,
                                     null=True)
    destinataire_contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="recipient_drdv_annuaire",
                                             blank=True, null=True)
    description = models.TextField(max_length=255, null=True, blank=True)
    type = models.CharField(max_length=2, choices=TYPE_CHOICES, default="1")
    acceptee = models.BooleanField(default=False)
    refusee = models.BooleanField(default=False)
    annulee = models.BooleanField(default=False)
    gratuit = models.BooleanField(default=False, help_text="Si cela est vrai, le rendez-vous est gratuit.")
    motif_refus = models.TextField(null=True, blank=True)
    date_rendez_vous = models.DateTimeField(null=True, blank=True)
    # TODO @deprecated field may be removed in the future use LettreOrientation model instead
    lettre_orientation = models.FileField(blank=True, null=True, upload_to='lettres/%Y/%m/%d/', default="lettre.png")

    @property
    def status(self):
        if hasattr(self, "tdemand"):
            if self.tdemand.facturee:
                return RdvStatus.DONE
        if self.acceptee:
            if self.date_rendez_vous:
                if self.date_rendez_vous < timezone.now():
                    return RdvStatus.EXPIRED
            return RdvStatus.ACCEPTED
        elif self.refusee:
            return RdvStatus.REFUSED
        elif self.annulee:
            return RdvStatus.CANCELED
        else:
            return RdvStatus.WAITING

    def is_expired(self):
        return self.status == RdvStatus.EXPIRED
