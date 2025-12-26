from django.db import models
from django.utils.translation import ugettext_lazy as _

# Create your models here.
from core.models import Patient


class Dicom_Patient(models.Model):
    patient = models.ForeignKey(Patient, verbose_name=_("Patient"),
                                on_delete=models.CASCADE, related_name="dicom_patient")
    dicom = models.FileField(upload_to='uploads/dicom/', null=False, blank=False)

    @property
    def full_name(self):
        return self.patient.full_name