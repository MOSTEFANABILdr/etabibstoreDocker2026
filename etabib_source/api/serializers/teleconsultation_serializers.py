from datetime import datetime, timedelta

from django.utils.translation import gettext as _
from rest_auth.serializers import LoginSerializer
from rest_framework import serializers, exceptions
from rest_framework.pagination import PageNumberPagination

from core.models import Medecin
from etabibWebsite import settings
from teleconsultation.models import Presence, Tdemand, Tsession, TspeakerStats


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 30


class DoctorSerializer(serializers.ModelSerializer):
    specialite = serializers.SerializerMethodField()
    en_ligne = serializers.SerializerMethodField()
    ville = serializers.SerializerMethodField()
    sexe = serializers.SerializerMethodField()

    def get_specialite(self, obj):
        if hasattr(obj, "contact"):
            if obj.contact.specialite:
                return obj.contact.specialite
        return ""

    def get_sexe(self, obj):
        if obj.contact.sexe:
            return obj.contact.sexe
        return ""

    def get_ville(self, obj):
        if obj.contact.ville:
            return "%s, %s" % (obj.contact.ville.country, obj.contact.ville.region.name)
        return ""

    def get_en_ligne(self, obj):
        return Presence.objects.filter(
            room__channel_name=settings.DOCTORS_CHANNEL, user=obj.user
        ).exists()

    class Meta:
        model = Medecin
        fields = ['id', 'nom', "prenom", "specialite", "ville", "sexe", "en_ligne", "tarif_consultation"]


class OnlyPatientLoginSerialiser(LoginSerializer):
    """
    Validate user account before login
    if the account is a patient login
    else raise an exception
    """

    def validate(self, attrs):
        attrs = super(OnlyPatientLoginSerialiser, self).validate(attrs)
        user = attrs['user']
        if hasattr(user, "patient"):
            return attrs
        else:
            raise exceptions.ValidationError(_("Veuillez saisir un compte patient valide"))


class OnlyDoctorLoginSerialiser(LoginSerializer):
    """
    Validate user account before login
    if the account is a 'medecin' login
    else raise an exception
    """

    def validate(self, attrs):
        attrs = super(OnlyDoctorLoginSerialiser, self).validate(attrs)
        user = attrs['user']
        if hasattr(user, "medecin"):
            return attrs
        else:
            raise exceptions.ValidationError(_("Veuillez saisir un compte 'medecin' valide"))


class SpeakerStatsSerializer(serializers.Serializer):
    created_timestamp = serializers.IntegerField()
    jid = serializers.CharField()
    speakerStats = serializers.JSONField()

    def validate_jid(self, jid):
        self.room_name = jid.split("@")[0]
        try:
            self.tdemand = Tdemand.objects.get(salle_discussion=self.room_name)
        except Tdemand.DoesNotExist:
            raise serializers.ValidationError(_("Not a valid econsultation room name"))

    def validate(self, data):
        speakerStats = data["speakerStats"]
        for key in speakerStats:
            if isinstance(speakerStats[key], dict):
                displayName = speakerStats[key]['displayName']
                if displayName not in (self.tdemand.patient.full_name, self.tdemand.medecin.full_name):
                    # TODO: Find another way to check user identity
                    # raise serializers.ValidationError(_("Not a valid username"))
                    pass
        return data

    def save(self, **kwargs):
        created_timestamp = self.validated_data['created_timestamp']
        created_timestamp = int(created_timestamp) / 1000
        speakerStats = self.validated_data['speakerStats']
        session = Tsession()
        session.date_creation = datetime.utcfromtimestamp(created_timestamp)
        session.save()

        for key in speakerStats:
            if isinstance(speakerStats[key], dict):
                displayName = speakerStats[key]['displayName']
                obj = TspeakerStats()
                if self.tdemand.patient.full_name == displayName:
                    obj.user = self.tdemand.patient.user
                elif self.tdemand.medecin.full_name == displayName:
                    obj.user = self.tdemand.medecin.user
                totalDominantSpeakerTime = speakerStats[key]['totalDominantSpeakerTime']
                obj.total_dominant_speaker_time = timedelta(milliseconds=totalDominantSpeakerTime)
                obj.save()

                session.statistiques_conférenciers.add(obj)

        self.tdemand.sessions.add(session)
