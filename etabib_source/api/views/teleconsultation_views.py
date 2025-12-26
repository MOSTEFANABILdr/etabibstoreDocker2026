import datetime
from django.utils import timezone

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User
from django.http import Http404
from rest_auth.views import LoginView
from rest_framework import generics, status
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_tracking.mixins import LoggingMixin

from api.serializers.serializers import PatientSerializer
from api.serializers.teleconsultation_serializers import StandardResultsSetPagination, DoctorSerializer, \
    OnlyPatientLoginSerialiser, SpeakerStatsSerializer, OnlyDoctorLoginSerialiser
from core.enums import WebsocketCommand
from core.models import Contact
from core.utils import getListDoctorsUsingeTabibCare
from etabibWebsite import settings
from teleconsultation.models import Presence, Tdemand


class OnlyPatientLoginView(LoggingMixin, LoginView):
    serializer_class = OnlyPatientLoginSerialiser


class OnlyDoctorLoginView(LoggingMixin, LoginView):
    serializer_class = OnlyDoctorLoginSerialiser


class DoctorsListView(LoggingMixin, generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    pagination_class = StandardResultsSetPagination
    serializer_class = DoctorSerializer

    def should_log(self, request, response):
        return response.status_code >= 400

    def get_queryset(self):
        en_ligne = self.request.query_params.get('en_ligne', None)
        sexe = self.request.query_params.get('sexe', None)
        q = self.request.query_params.get('q', None)

        filtred_list = getListDoctorsUsingeTabibCare(sexe=sexe, q=q)

        if en_ligne == "1":
            return filtred_list.filter(is_online=True)
        elif en_ligne == "0":
            return filtred_list.filter(is_online=False)
        else:
            return filtred_list


class SpeakerStatsView(LoggingMixin, generics.GenericAPIView):
    serializer_class = SpeakerStatsSerializer

    def post(self, request):
        serializer = SpeakerStatsSerializer(
            data=request.data
        )
        if serializer.is_valid():
            serializer.save()
            return Response({}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SoldeView(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    queryset = User.objects.all()
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    serializer_class = PatientSerializer

    def get(self, request, *args, **kwargs):
        if request.user != self.get_object().user:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return super().get(request, *args, **kwargs)

    def get_object(self):
        user = super(SoldeView, self).get_object()
        if hasattr(user, "patient"):
            return user.patient
        else:
            raise Http404("Patient inexistant")


class BusyDoctorView(LoggingMixin, generics.GenericAPIView):
    serializer_class = Tdemand
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication, )

    def post(self, request, *args, **kwargs):
        # TODO: mark notification as read

        # send rejected notification
        choice = request.data['busy_time']
        tdemandId = request.data['tdemand_id']
        if tdemandId:
            tdemand = Tdemand.objects.get(pk=tdemandId)
            cmd = WebsocketCommand.TELECONSULTATION_DEMAND_REJECTED.value
            channel_layer = get_channel_layer()
            room_group_name = 'chat_%s' % tdemand.patient.user.pk

            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'notification_message',
                    'data': {
                        'command': cmd,
                        'code': "BUSY",
                    }
                }
            )
            # setting doctor to busy stat
            # TODO remove redundancy with doctor_forms.getChosenTime()
            time = None
            if choice == "1":
                time = timezone.now() + datetime.timedelta(minutes=5)
            elif choice == "2":
                time = timezone.now() + datetime.timedelta(minutes=10)
            elif choice == "3":
                time = timezone.now() + datetime.timedelta(minutes=30)
            elif choice == "4":
                time = timezone.now() + datetime.timedelta(minutes=60)
            tdemand.annulee = True
            Presence.objects.setBusy(tdemand.medecin.user, True, time)
            # update demand
            tdemand.save()

        return Response(status=status.HTTP_200_OK)


