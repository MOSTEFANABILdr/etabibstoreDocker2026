from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers

from appointements.models import DemandeRendezVous
from core.models import Medecin
from dicom.models import Dicom_Patient


class PatientDicomSerializer(serializers.ModelSerializer):
    get_ptient_id = serializers.SerializerMethodField()
    get_ptient_file = serializers.SerializerMethodField()
    get_ptient_full_name = serializers.SerializerMethodField()

    def get_ptient_id(self, obj):
        return obj.patient.pk

    def get_ptient_file(self, obj):
        return obj.dicom

    def get_ptient_full_name(self, obj):
        return obj.full_name

    class Meta:
        model = Dicom_Patient
        fields = ['patient','full_name', 'dicom']
