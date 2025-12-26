from django.http import Http404
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_tracking.mixins import LoggingMixin

from api.serializers.serializers import PatientSerializer
from core.models import Patient
from core.templatetags.utils_tags import offer_id_unhash


class PatientIdView(LoggingMixin, APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    serializer_class = PatientSerializer

    def get_object(self, pk):
        try:
            return Patient.objects.get(pk=pk)
        except Patient.DoesNotExist:
            raise Http404

    def get(self, request, hash_pk, format=None):
        pk = offer_id_unhash(hash_pk)
        patient_pk = self.get_object(pk)
        serializer = PatientSerializer(patient_pk)
        return Response(serializer.data)


