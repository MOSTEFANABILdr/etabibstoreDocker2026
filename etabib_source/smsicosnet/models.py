from collections import namedtuple

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _

from core.models import Operateur

STATUS = namedtuple('STATUS', 'sent failed queued requeued')._make(range(4))


class Smsicosnet(models.Model):
    STATUS_CHOICES = [(STATUS.sent, _("sent")), (STATUS.failed, _("failed")),
                      (STATUS.queued, _("queued")), (STATUS.requeued, _("requeued"))]

    message = models.CharField(verbose_name=_("Message"), max_length=160, null=True, blank=True)
    reponse = models.TextField(verbose_name=_("Reponse"), null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    source_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True, )
    source_id = models.PositiveIntegerField(blank=True, null=True)
    source = GenericForeignKey('source_type', 'source_id')
    date_creation = models.DateTimeField(auto_now_add=True)
    cree_par = models.ForeignKey(Operateur, blank=True, null=True, on_delete=models.PROTECT)

    status = models.PositiveSmallIntegerField(
        _("Status"),
        choices=STATUS_CHOICES, db_index=True,
        blank=True, null=True
    )

    @property
    def status_message(self):
        txt = self.reponse.split('|')
        return (txt)

    def __str__(self):
        return f"SMS N°: {self.id}"
