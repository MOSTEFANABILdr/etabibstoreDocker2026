from cities_light.models import Country, City
from django.http import Http404
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.utils_serializers import CountrySerializer, CitySerializer, SpecialiteSerializer, BankSerializer
from core.models import Specialite, Bank, Qualification


class ContrytDetail(APIView):

    def get_object(self, pk):
        try:
            return Country.objects.get(pk=pk)
        except Country.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        snippet = self.get_object(pk)
        serializer = CountrySerializer(snippet)
        return Response(serializer.data)


class CitytDetail(APIView):

    def get_object(self, pk):
        try:
            return City.objects.get(pk=pk)
        except City.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        snippet = self.get_object(pk)
        serializer = CitySerializer(snippet)
        return Response(serializer.data)


class SpecialityDetail(APIView):

    def get_object(self, pk):
        try:
            return Specialite.objects.get(pk=pk)
        except Specialite.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        snippet = self.get_object(pk)
        serializer = SpecialiteSerializer(snippet)
        return Response(serializer.data)


class QualificationDetail(APIView):

    def get_object(self, pk):
        try:
            return Qualification.objects.get(pk=pk)
        except Qualification.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        snippet = self.get_object(pk)
        serializer = SpecialiteSerializer(snippet)
        return Response(serializer.data)


class BankDetail(APIView):

    def get_object(self, pk):
        try:
            return Bank.objects.get(pk=pk)
        except Bank.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        snippet = self.get_object(pk)
        serializer = BankSerializer(snippet)
        return Response(serializer.data)
