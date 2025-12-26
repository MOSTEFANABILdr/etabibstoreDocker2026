from hashlib import sha256

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_tracking.mixins import LoggingMixin

from api.views.views import MACPermission
from core.models import Poste, Facture_OffrePrep_Licence


class DoctorLscView(LoggingMixin, generics.GenericAPIView):
    permission_classes = (MACPermission,)

    def should_log(self, request, response):
        return response.status_code >= 200

    def post(self, request):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
        except Poste.DoesNotExist:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)

        if isinstance(poste.licence.current_offre(), Facture_OffrePrep_Licence):
            if poste.licence.current_offre().offre.prix == 0:
                data = sha256(('Freemium').encode()).hexdigest()
            else:
                data = sha256(('Premium').encode()).hexdigest()

            return Response({data}, status=status.HTTP_200_OK)
