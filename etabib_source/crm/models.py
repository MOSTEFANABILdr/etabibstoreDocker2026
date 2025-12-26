from cities_light.models import City
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _

from core.utils import applyTVA

class Pays(models.Model):
    nom = models.CharField(max_length=255)
    nom_ar = models.CharField(max_length=255)

    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = "Pays"
        verbose_name_plural = "Pays"


class Wilaya(models.Model):
    nom = models.CharField(max_length=255)
    nom_ar = models.CharField(max_length=255)
    pays = models.ForeignKey(Pays, on_delete=models.CASCADE)

    def __str__(self):
        return self.nom


class Ville(models.Model):
    nom = models.CharField(max_length=255)
    nom_ar = models.CharField(max_length=255)
    daira_code = models.CharField(max_length=255, blank=True, null=True)
    daira_nom = models.CharField(max_length=255, blank=True, null=True)
    daira_nom_ar = models.CharField(max_length=255, blank=True, null=True)
    pays = models.ForeignKey(Pays, on_delete=models.CASCADE)
    wilaya = models.ForeignKey(Wilaya, on_delete=models.CASCADE)
    cl_map = models.ForeignKey(City, on_delete=models.CASCADE, blank=True, null=True)
    latitude = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        null=True,
        blank=True)

    longitude = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        null=True,
        blank=True)

    def __str__(self):
        return self.nom


class CommandeImage(models.Model):
    user = models.ForeignKey(User, verbose_name=_("Créée par"), on_delete=models.CASCADE)
    image = models.ImageField(upload_to="commandes")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)


class Commande(models.Model):
    OFFER_CHOICES = (
        ('', '----'),
        ("0", _("Abonement Trimestriel")),
        ("1", _("Abonement Annuel")),
        ("2", _("Abonement 18 Mois")),
    )
    PAYMENT_CHOICES = (
        ('', '----'),
        ("0", _("Espèce")),
        ("1", _("Chèque")),
        ("2", _("TPE")),
    )
    cree_par = models.ForeignKey(User, verbose_name=_("Créée par"), on_delete=models.CASCADE,
                                 related_name="commandes_crees")
    user = models.ForeignKey(User, verbose_name=_("User"), on_delete=models.CASCADE)
    offre = models.CharField(max_length=5, verbose_name=_("Offre"), choices=OFFER_CHOICES, default="", blank=True)
    quantite = models.IntegerField(default=1, verbose_name=_("Quantité"))
    methode_paiement = models.CharField(
        max_length=5, verbose_name=_("Méthode de paiement"), choices=PAYMENT_CHOICES, default="", blank=True
    )
    image = models.ForeignKey(CommandeImage, verbose_name=_("Image"), on_delete=models.CASCADE)
    versement_initial = models.IntegerField(verbose_name=_("Versement initial"), default=0)
    detail_action = models.OneToOneField('core.DetailAction', on_delete=models.PROTECT, null=True, blank=True)
    traitee = models.BooleanField(verbose_name=_("Traitée"), default=False)
    totalHt = models.FloatField(null=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)
    bordereau = models.ForeignKey("BordereauVersement", on_delete=models.CASCADE, null=True, blank=True)

    @property
    def ttc(self):
        if self.totalHt:
            return applyTVA(self.totalHt)
        return 0

    @property
    def ttctimb(self):
        ttc = self.ttc
        timbre = ttc * 1 / 100
        return ttc + timbre


class BordereauVersement(models.Model):
    date_creation = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)
    cree_par = models.ForeignKey(User, verbose_name=_("Créée par"), on_delete=models.CASCADE,
                                 related_name="bordereau_crees")
    total = models.FloatField()

    class Media:
        verbose_name = _("Bordereau de versement")
        verbose_name_plural = _("Bordereau de versement")
