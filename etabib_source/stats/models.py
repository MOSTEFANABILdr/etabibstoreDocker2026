from django.db import models
from core.models import Poste
from drugs.models import DciAtc, NomCommercial


class AtcdciStats(models.Model):
    atcdci = models.ForeignKey(DciAtc, on_delete=models.PROTECT)
    poste = models.ForeignKey(Poste, on_delete=models.PROTECT)
    date_insertion = models.DateTimeField()


class NomComercialStats(models.Model):
    nomCommercial = models.ForeignKey(NomCommercial, on_delete=models.PROTECT)
    poste = models.ForeignKey(Poste, on_delete=models.PROTECT)
    date_insertion = models.DateTimeField()
