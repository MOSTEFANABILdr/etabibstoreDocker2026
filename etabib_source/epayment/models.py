from django.contrib.auth.models import User
from django.db import models


class OrdreDePaiement(models.Model):
    ETATS_ORDRE = (("En cours", "En cours"),
                   ("Validé", "Validé"),
                   ("Expiré", "Expiré"),
                   ("Echec", "Echec"),
                   ("Annulé", "Annulé"))
    MOYEN_PAIEMENT = (("1","Carte EDAHABIA"),)

    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, null=True)
    numero_ordre = models.IntegerField()
    numero_autorisation = models.IntegerField(blank=True, null=True)
    moyen_paiement = models.CharField(max_length=2, choices=MOYEN_PAIEMENT, default="1")
    etat = models.CharField(max_length=50, choices=ETATS_ORDRE, default=ETATS_ORDRE[0][0])
    ordre_uuid = models.CharField(blank=True, null=True, max_length=255)
    montant = models.IntegerField()  # en dinars
    date_creation = models.DateTimeField(null=True, auto_now_add=True)
    # TODO add expiration signal (it expires in 20 min  if not confirmed)


class ValeurPoint(models.Model):
    date_maj = models.DateTimeField(null=True, auto_now_add=True)
    derniere_maj = models.BooleanField(default=True)
    valeur_dun_point = models.IntegerField()  # en dinars
