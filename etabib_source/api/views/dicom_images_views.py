from rest_framework import generics

from api.serializers.dicom_image_serializers import PatientDicomSerializer
from dicom.models import Dicom_Patient


class DicomImage(generics.ListAPIView):
    serializer_class = PatientDicomSerializer

    def should_log(self, request, response):
        return response.status_code >= 400

    def get_queryset(self):
        return Dicom_Patient.objects.all()
