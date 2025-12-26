from rest_framework import generics
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework_tracking.mixins import LoggingMixin

from api.serializers.serializers import EcongreSerializer, WebinarSerializer
from api.serializers.teleconsultation_serializers import StandardResultsSetPagination
from econgre.models import Congre, Webinar


class IsDoctor(BasePermission):
    """
    Allows access only to authenticated Doctors.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and hasattr(request.user, "medecin"))


class ListEcongre(LoggingMixin, generics.ListAPIView):
    permission_classes = (IsAuthenticated, IsDoctor,)
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    pagination_class = StandardResultsSetPagination
    serializer_class = EcongreSerializer
    queryset = Congre.objects.filter(publie=True).order_by("-id")

    def should_log(self, request, response):
        return response.status_code >= 400


class ListWebinar(LoggingMixin, generics.ListAPIView):
    permission_classes = (IsAuthenticated, IsDoctor,)
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    pagination_class = StandardResultsSetPagination
    serializer_class = WebinarSerializer
    queryset = Webinar.objects.filter(publie=True).order_by("-id")

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(congre__id=self.kwargs['congre_id'])

    def should_log(self, request, response):
        return response.status_code >= 400
