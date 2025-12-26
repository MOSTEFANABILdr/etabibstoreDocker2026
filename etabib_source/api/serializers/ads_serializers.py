from datetime import datetime

import basehash
import pytz
from rest_framework import serializers

from core.models import AnnonceImpressionLog, Campagne, CampagneStatistique, Poste, Annonce, CampagneImpression
from econgre.models import WebinarStatistique


class AdImpressionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnonceImpressionLog
        fields = ['campagne', 'annonce', 'user']


class StringListField(serializers.ListField):
    child = serializers.CharField()


class AdDownloadConfirationSerializer(serializers.Serializer):
    downloaded_compaigns = StringListField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac = self.context.get("mac")

    def save(self):
        downloaded_compaigns = self.validated_data['downloaded_compaigns']
        poste = Poste.objects.get(mac=self.mac)
        hash_fn = basehash.base36(32)

        for d in downloaded_compaigns:
            campagn_id = hash_fn.unhash(d)
            c = Campagne.objects.get(id=campagn_id)
            try:
                obj, created = CampagneStatistique.objects.get_or_create(
                    campagne=c, user=poste.medecin.user, poste=poste
                )
                if not created:
                    obj.save()
            except Exception as e:
                pass


class UploadCampaignsStatisticsChild1Serializer(serializers.Serializer):
    campgin_id = serializers.CharField(max_length=255, required=False)
    annonce_id = serializers.CharField(max_length=255, required=False)
    date_impression = serializers.CharField(max_length=255, required=True)


class UploadCampaignsStatisticsChild2Serializer(serializers.Serializer):
    campgin_id = serializers.CharField(max_length=255, required=False)
    annonce_id = serializers.CharField(max_length=255, required=False)
    date_click = serializers.CharField(max_length=255, required=True)


class UploadCampaignsStatisticsSerializer(serializers.Serializer):
    impressions = UploadCampaignsStatisticsChild1Serializer(many=True)
    clicks = UploadCampaignsStatisticsChild2Serializer(many=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac = self.context.get("mac")

    def save(self):
        impression_items = self.validated_data['impressions']
        click_items = self.validated_data['clicks']

        poste = Poste.objects.get(mac=self.mac)
        hash_cmp = basehash.base36(32)
        hash_ads = basehash.base52(32)

        for item in impression_items:
            campgin_id = item.get("campgin_id", None)
            annonce_id = item.get("annonce_id", None)
            date_impression = item.get("date_impression", None)
            if annonce_id and campgin_id:
                imp = AnnonceImpressionLog()
                campagne = Campagne.objects.get(id=hash_cmp.unhash(campgin_id))
                annonce = Annonce.objects.get(id=hash_ads.unhash(annonce_id))
                d = datetime.strptime(date_impression, '%Y-%m-%d %H:%M:%S.%f')
                localtz = pytz.timezone('Africa/Algiers')
                dt_aware = localtz.localize(d)

                imp.annonce = annonce
                imp.campagne = campagne
                imp.user = poste.medecin.user
                imp.date_impression = dt_aware
                imp.reseau = CampagneImpression.CHOICES[1][0]  # eTabib Workspace
                imp.save()
                # campagne.partenaire.consumePoints(
                #     AdsStatsType.DISPLAY,
                #     imp
                # )
        #NOTE: click_items are calculated with "ads-click" view

class AdCongreImpressionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebinarStatistique
        fields = ['wvideo', 'user', 'duree']
