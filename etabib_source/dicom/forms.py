# -*- coding: utf-8 -*-
from django import forms

from dicom.models import Dicom_Patient


class PatientDicomForm(forms.ModelForm):
    class Meta:
        model = Dicom_Patient
        fields = ['patient', 'dicom']
