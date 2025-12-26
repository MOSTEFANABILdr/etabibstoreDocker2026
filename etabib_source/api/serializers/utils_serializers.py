from cities_light.models import Country, City
from rest_framework import serializers

from core.models import Specialite, Bank


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['name', ]


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['name', ]


class SpecialiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialite
        fields = ['libelle', 'libelle_ar']


class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = ['name', ]
