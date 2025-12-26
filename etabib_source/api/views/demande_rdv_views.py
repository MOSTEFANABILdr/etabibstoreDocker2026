from django.db.models.query import QuerySet
from rest_framework import generics, status
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_tracking.mixins import LoggingMixin

from api.serializers.demande_rdv_serializers import DemandeRDVSerializer, CancelDemandeRdvSerializer, RdvSerializer, \
    PatientRdvSerializer
from api.serializers.teleconsultation_serializers import StandardResultsSetPagination
from api.views.views import MACPermission
from appointements.models import DemandeRendezVous
from core.models import Poste


class AddDemandeRdv(LoggingMixin, generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    serializer_class = DemandeRDVSerializer

    def post(self, request):
        serializer = DemandeRDVSerializer(
            data=request.data, context={'demandeur': request.user}
        )
        if serializer.is_valid():
            if serializer.isSimilarDemandExists():
                dmd = serializer.getExistingDemande()
                return Response({'demande_id': dmd.id}, status=status.HTTP_200_OK)
            elif serializer.detectFlood():
                return Response({}, status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                result = serializer.save()
                return Response({'demande_id': result.id}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CancelDemandeRdv(LoggingMixin, generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    serializer_class = CancelDemandeRdvSerializer

    def post(self, request):
        serializer = CancelDemandeRdvSerializer(
            data=request.data
        )
        if serializer.is_valid():
            data = serializer.annuleeDemande()
            if data:
                return Response(status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RdvListView(LoggingMixin, generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    pagination_class = StandardResultsSetPagination
    serializer_class = RdvSerializer

    def should_log(self, request, response):
        return response.status_code >= 400

    def get_queryset(self):
        patient = self.request.user.patient
        status = self.request.query_params.get('status', None)
        if status == "accepted":
            return DemandeRendezVous.objects.filter(demandeur=patient.user, acceptee=True)
        if status == "canceled":
            return DemandeRendezVous.objects.filter(demandeur=patient.user, annulee=True)
        if status == "refused":
            return DemandeRendezVous.objects.filter(demandeur=patient.user, refusee=True)
        if status == "waiting":
            return DemandeRendezVous.objects.filter(demandeur=patient.user, acceptee=False, refusee=False, annulee=False)

        return DemandeRendezVous.objects.filter(demandeur=patient.user).order_by('-date_creation')


class RdvDoctorNotificationListView(LoggingMixin, generics.ListAPIView):
    permission_classes = (MACPermission,)
    pagination_class = StandardResultsSetPagination
    serializer_class = PatientRdvSerializer

    def should_log(self, request, response):
        return response.status_code >= 400

    def get_queryset(self):
        mac = self.request.META.get('HTTP_MAC', None)
        lastrdv = self.request.META.get('HTTP_LASTRDV', None)

        try:
            poste = Poste.objects.get(mac=mac)
        except Poste.DoesNotExist:
            return DemandeRendezVous.objects.none()

        medecin = poste.medecin
        return DemandeRendezVous.objects.filter(
            pk__gt=lastrdv, destinataire=medecin.user, acceptee=False, refusee=False, annulee=False
        ).order_by('-date_creation')
