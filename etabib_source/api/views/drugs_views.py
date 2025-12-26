import traceback

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_tracking.mixins import LoggingMixin

from api.serializers.drugs_serializers import ChageLogSerializer, ChageDrugsSerializer
from api.views.views import MACPermission
from core.models import Poste
from drugs.models import ChangeLog, ChangeDrugs


class ChangeLogView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]
    serializer_class = ChageLogSerializer
    queryset = ChangeLog.objects.none()

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(ChangeLogView, self).handle_log()

    def get(self, request):
        try:
            uuid = request.GET.get("uuid", None)
            data = {"uuid": uuid}
            serializer = ChageLogSerializer(
                data=data
            )
            if serializer.is_valid():
                data = serializer.save()
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            traceback.print_exc()
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChangeDrugsView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]
    serializer_class = ChageDrugsSerializer
    queryset = ChangeDrugs.objects.none()

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(ChangeDrugsView, self).handle_log()

    def get(self, request):
        try:
            uuid = request.GET.get("uuid", None)
            data = {"uuid": uuid}
            serializer = ChageDrugsSerializer(
                data=data
            )
            if serializer.is_valid():
                data = serializer.save()
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            traceback.print_exc()
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
