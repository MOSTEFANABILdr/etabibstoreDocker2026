from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers

from appointements.models import DemandeRendezVous
from core.models import Medecin


class DemandeRDVSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField(required=False)
    destinataire_id = serializers.IntegerField(required=False)
    rdv_choice = serializers.ChoiceField(choices=DemandeRendezVous.TYPE_CHOICES, default='1')
    description = serializers.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.demandeur = self.context.get("demandeur", None)
        self.medecin = None
        self.destinataire = None

    def validate_doctor_id(self, doctor_id):
        if doctor_id:
            try:
                medecin = Medecin.objects.get(id=doctor_id)
                self.destinataire = medecin.user
            except Medecin.DoesNotExist:
                raise serializers.ValidationError("doctor id  is not valid")
        return doctor_id
    def validate_destinataire_id(self, destinataire_id):
        if destinataire_id:
            try:
                self.destinataire = User.objects.get(id=destinataire_id)
            except User.DoesNotExist:
                raise serializers.ValidationError("destinataire id  is not valid")
        return destinataire_id

    def validate(self, attrs):
        attrs = super(DemandeRDVSerializer, self).validate(attrs)
        destinataire_id = attrs.get('destinataire_id', None)
        doctor_id = attrs.get('doctor_id', None)
        if destinataire_id or doctor_id:
            return attrs
        else:
            raise serializers.ValidationError("destinataire_id or doctor_id are missed")
        return attrs

    def isSimilarDemandExists(self):
        return DemandeRendezVous.objects.filter(
            destinataire=self.destinataire,
            demandeur=self.demandeur,
            acceptee=False,
            annulee=False,
            refusee=False
        ).exists()

    def getExistingDemande(self):
        dmds = DemandeRendezVous.objects.filter(
            destinataire=self.destinataire,
            demandeur=self.demandeur,
            acceptee=False,
            annulee=False,
            refusee=False
        )
        if dmds.exists():
            return dmds.first()
        return None

    def detectFlood(self):
        time_threshold = timezone.localtime() - timedelta(seconds=30)
        dmds = DemandeRendezVous.objects.filter(
            destinataire=self.destinataire,
            demandeur=self.demandeur,
            date_creation__gte=time_threshold
        )
        return dmds.exists()

    def save(self):
        rdv_choice = self.validated_data['rdv_choice']
        description = self.validated_data.get('description', None)
        obj = DemandeRendezVous()
        obj.destinataire = self.destinataire
        obj.type = rdv_choice
        obj.demandeur = self.demandeur
        obj.description = description
        obj.save()
        return obj


class CancelDemandeRdvSerializer(serializers.Serializer):
    demande_id = serializers.IntegerField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate_demand_id(self, demande_id):
        if not DemandeRendezVous.objects.get(id=demande_id).exists():
            raise serializers.ValidationError("demande id is not valid")
        return demande_id

    def annuleeDemande(self):
        return DemandeRendezVous.objects.filter(id=self.validated_data['demande_id']).update(annulee=True,
                                                                                             date_traitement=datetime.now())


class RdvSerializer(serializers.ModelSerializer):
    medecin_nom = serializers.SerializerMethodField()
    medecin_prenom = serializers.SerializerMethodField()
    salle_discussion = serializers.SerializerMethodField()

    def get_medecin_nom(self, obj):
        return obj.destinataire.first_name

    def get_medecin_prenom(self, obj):
        return obj.destinataire.last_name

    def get_salle_discussion(self, obj):
        if hasattr(obj, 'tdemand'):
            if obj.tdemand.salle_discussion:
                return obj.tdemand.salle_discussion
        return ""

    class Meta:
        model = DemandeRendezVous
        fields = ['id', 'acceptee', 'refusee', 'annulee', "medecin_nom", "medecin_prenom", "date_rendez_vous",
                  "salle_discussion"]


class PatientRdvSerializer(serializers.ModelSerializer):
    ptient_nom = serializers.SerializerMethodField()
    ptient_prenom = serializers.SerializerMethodField()

    def get_ptient_nom(self, obj):
        return obj.demandeur.first_name

    def get_ptient_prenom(self, obj):
        return obj.demandeur.last_name

    class Meta:
        model = DemandeRendezVous
        fields = ['id', "ptient_nom", "ptient_prenom", "date_creation"]
