import random
import traceback
from itertools import chain

import basehash
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_tracking.mixins import LoggingMixin

from api.serializers.ads_serializers import AdImpressionSerializer, AdDownloadConfirationSerializer, \
    UploadCampaignsStatisticsSerializer, AdCongreImpressionSerializer
from api.views.views import MACPermission
from core.enums import AdsDestination, AdsStatsType, AdTypeHelper
from core.models import Poste, Campagne, AnnonceDisplay, AnnonceFeed, AnnonceVideo
from etabibWebsite import settings


#####################################
# HELPERS
#####################################
def get_active_campaigns(partner=None, dest=None, region_id=None, cible_id=None):
    # TODO: limit the number of campaign
    # TODO: Find a better way to select active campaigns
    if partner:
        campagnes = Campagne.soft_objects.filter(partenaire=partner).distinct()
    else:
        campagnes = Campagne.soft_objects.all()
    if dest:
        # filter by dest
        campagnes = campagnes.filter(campagneimpression__reseaux__icontains=dest.value).distinct()
    if region_id:
        # filter by zone
        campagnes = campagnes.filter(Q(campagneimpression__zones=None) | Q(campagneimpression__zones__id=region_id) |
                                     Q(campagneimpression__toutes_zones=True)).distinct()
    if cible_id:
        # filter by specialities
        campagnes = campagnes.filter(
            Q(campagneimpression__cibles=None) | Q(campagneimpression__cibles__id=cible_id) |
            Q(campagneimpression__toutes_specialites=True)
        ).distinct()
    return [c for c in campagnes if c.is_active and c.is_valid]


def uniq_chain(self, *args, **kwargs):
    seen = set()
    for x in chain(*args, **kwargs):
        if x in seen:
            continue
        seen.add(x)
        yield x


def campaign_to_json(request, campaign, type=None):
    d = dict()
    hash_fn = basehash.base36(32)
    d['campgin_id'] = hash_fn.hash(campaign.pk)
    d['date_debut'] = campaign.date_debut
    d['date_fin'] = campaign.date_fin
    ads = []
    for annonce in campaign.annonces.all():
        dan = dict()
        hash_fn = basehash.base52(32)
        dan["annonce_id"] = hash_fn.hash(annonce.pk)
        # filter annonce by type FEED or DISPLAY
        if isinstance(annonce, AnnonceFeed):
            dan["type"] = AdTypeHelper.FEED.value[0]
            dan["titre"] = annonce.titre
            dan["corps"] = annonce.corps
        if isinstance(annonce, AnnonceDisplay):
            dan["type"] = AdTypeHelper.DISPLAY.value[0]
            imgs = []
            for image in annonce.images.all():
                dim = dict()
                dim['url'] = request.build_absolute_uri(image.image.url)
                if settings.ENVIRONMENT != settings.Environment.DEV:
                    dim['url'] = dim['url'].replace("http://", "https://")
                dim['size'] = image.type
                imgs.append(dim)
            dan['images'] = imgs
        if isinstance(annonce, AnnonceVideo):
            dan["type"] = AdTypeHelper.VIDEO.value[0]
            dan['video_url'] = request.build_absolute_uri(annonce.video.url)
            if settings.ENVIRONMENT != settings.Environment.DEV:
                dim['url'] = dim['url'].replace("http://", "https://")

        # add annonce url
        dan["url"] = request.build_absolute_uri(
            reverse("ads-click", args=(d['campgin_id'], dan["annonce_id"], type.value))
        )

        if settings.ENVIRONMENT != settings.Environment.DEV:
            dan["url"] = dan["url"].replace("http://", "https://")
        ads.append(dan)
    d['annonces'] = ads
    return d


def adsToJson(campaigns_json, adTypeHelper, size=None, multiple=False):
    """
        :param request:
        :param adTypeHelper: see class AdTypeHelper
        :param size of the image: 1 , 2 or 3
        :return:
        """
    l = []
    lsresult = []
    if adTypeHelper == AdTypeHelper.DISPLAY and size == None:
        return dict()
    # extract ads with the same requested "adTypeHelper"
    for item in campaigns_json:
        annonces = item['annonces']
        for annonce in annonces:
            if annonce['type'] == adTypeHelper.value[0]:
                if annonce['type'] == adTypeHelper.DISPLAY.value[0]:
                    # check if inside this display ads there is an image with size = size
                    # if yes add the ad to the list
                    for image in annonce["images"]:
                        if image["size"] == size:
                            l.append((item['campgin_id'], annonce))
                            break
                else:
                    l.append((item['campgin_id'], annonce))

    result = dict()
    if len(l) > 0:
        if multiple:
            for tuple in l:
                annonce = tuple[1]
                result["campagne_id"] = tuple[0]
                result["annonce_id"] = annonce["annonce_id"]
                result["annonce_url"] = annonce["url"]
                if adTypeHelper == AdTypeHelper.DISPLAY:
                    for image in annonce["images"]:
                        if image["size"] == size:
                            result["image_url"] = image["url"]
                elif adTypeHelper == AdTypeHelper.VIDEO:
                    result["video_url"] = annonce["video_url"]
                elif adTypeHelper == AdTypeHelper.FEED:
                    result["titre"] = annonce["titre"]
                    result["corps"] = annonce["corps"]
                lsresult.append(result)
            return lsresult
        else:
            tuple = random.choice(l)
            annonce = tuple[1]
            result["campagne_id"] = tuple[0]
            result["annonce_id"] = annonce["annonce_id"]
            result["annonce_url"] = annonce["url"]
            if adTypeHelper == AdTypeHelper.DISPLAY:
                for image in annonce["images"]:
                    if image["size"] == size:
                        result["image_url"] = image["url"]
            elif adTypeHelper == AdTypeHelper.VIDEO:
                result["video_url"] = annonce["video_url"]
            elif adTypeHelper == AdTypeHelper.FEED:
                result["titre"] = annonce["titre"]
                result["corps"] = annonce["corps"]
            return result


def getAd(request, dest, type_ad, size_image=None, multiple=False):
    out = []
    region_id = None
    cible_id = None
    is_medecin =False
    is_prof = False

    if hasattr(request.user, 'medecin'):
        is_medecin = True
        contact = request.user.medecin.contact
    elif hasattr(request.user, 'professionnelsante'):
        is_prof = True
        contact = request.user.professionnelsante.contact

    if is_medecin or is_prof:
        if contact.ville:
            if contact.ville.region:
                region_id = contact.ville.region.id
        if contact.specialite:
            cible_id = contact.specialite.id

        # get active campaigns according to network and region and specialite
        if dest:
            default_campaigns = get_active_campaigns(
                dest=dest,
                cible_id=cible_id,
                region_id=region_id,
            )

            if is_medecin:
                # check if doctor license has a partner
                for poste in request.user.medecin.postes.all():
                    if poste.licence:
                        if poste.licence.partenaire:
                            # return all partner active camapign
                            partner_campaigns = get_active_campaigns(
                                poste.licence.partenaire,
                                AdsDestination.WEB,
                                cible_id=cible_id,
                                region_id=region_id
                            )
                            out = list(uniq_chain(out, partner_campaigns))
                        else:
                            out = list(uniq_chain(out, default_campaigns))

            if not out:
                out = default_campaigns

            result = []
            for c in out:
                result.append(campaign_to_json(request, c, type=AdsDestination.WEB))

            """
                type_ad choices:
                DISPLAY == 1
                FEED == 2
                VIDEO == 3
                Size choices:
                 == 1
                 == 2
                 == 3
            """
            rad = adsToJson(
                result,
                type_ad,
                size_image,
                multiple
            )
            return rad

        return dict()
    return dict()


#####################################
# VIEWS
#####################################
class AdImpressionView(LoggingMixin, generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (SessionAuthentication,)
    serializer_class = AdImpressionSerializer

    def get(self, request, campagne_id, annonce_id, user_id, reseau):
        try:
            hash_fn = basehash.base52(32)
            annonce_id = hash_fn.unhash(annonce_id)
        except:
            pass
        try:
            hash_cmp = basehash.base36(32)
            campagne_id = hash_cmp.unhash(campagne_id)
        except:
            pass
        serializer = AdImpressionSerializer(
            data={'annonce': annonce_id,
                  "user": user_id,
                  "campagne": campagne_id
                  }
        )
        if serializer.is_valid():
            obj = serializer.save(date_impression=timezone.now(), reseau=reseau)
            #TODO: add special treatment for annonce feed
            if not isinstance(obj.annonce, AnnonceFeed):
                obj.campagne.partenaire.consumePoints(
                    AdsStatsType.DISPLAY,
                    obj
                )
            return Response(status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdCongreImpressionView(LoggingMixin, generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (SessionAuthentication,)
    serializer_class = AdCongreImpressionSerializer

    def get(self, request, wvideo_id, user_id, duree):
        serializer = AdCongreImpressionSerializer(
            data={'wvideo': wvideo_id,
                  "user": user_id,
                  "duree": duree
                  }
        )
        if serializer.is_valid():
            obj = serializer.save(date_vision=timezone.now())
            return Response(status=status.HTTP_201_CREATED)
        else:
            print("is not valid")
            print(serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetAdsList(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission | IsAuthenticated]
    queryset = ''
    authentication_classes = (
        TokenAuthentication, SessionAuthentication
    )

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(GetAdsList, self).handle_log()

    def get(self, request):
        """
        Get a list of active campaigns
        - Mac exists -> Ads for eTabib workspace
        - Authenticated user -> Ads for the web
        -
        :param request:
        :return: list of active campaigns with theirs ads
        """
        self.request = request
        mac = request.META.get('HTTP_MAC', None)
        version = request.GET.get('v', None)
        # if version == 2 , disable the test "Campaign is downloaded"
        # else activate the test
        try:
            if mac:  # from etabib
                if not settings.ENABLE_WORKSPACE_ADS:
                    return Response([], status=status.HTTP_200_OK)
                poste = Poste.objects.get(mac=mac)
                region_id = None
                cible_id = None
                if poste.medecin.contact.ville:
                    region_id = poste.medecin.contact.ville.region.id
                if poste.medecin.contact.specialite:
                    cible_id = poste.medecin.contact.specialite.id
                if poste.licence:
                    if poste.licence.partenaire:
                        # return all partner active camapign
                        default_campaigns = get_active_campaigns(
                            poste.licence.partenaire,
                            AdsDestination.ETABIB_WORKSPACE,
                            region_id=region_id,
                            cible_id=cible_id
                        )
                    else:
                        # return different campaigns
                        default_campaigns = get_active_campaigns(
                            dest=AdsDestination.ETABIB_WORKSPACE,
                            region_id=region_id,
                            cible_id=cible_id
                        )

                    result = []
                    for c in default_campaigns:
                        # TODO: remove is_downloaded
                        if version != "2":
                            if c.is_downloaded(poste):
                                result.append(campaign_to_json(request, c, type=AdsDestination.ETABIB_WORKSPACE))
                        else:
                            result.append(campaign_to_json(request, c, type=AdsDestination.ETABIB_WORKSPACE))

                    return Response(result, status=status.HTTP_200_OK)
                else:
                    return Response(status=status.HTTP_400_BAD_REQUEST)
            else:  # from web
                if request.user.is_authenticated:
                    if not settings.ENABLE_WEB_ADS:
                        return Response([], status=status.HTTP_200_OK)
                    if hasattr(request.user, 'medecin'):
                        out = []
                        region_id = None
                        cible_id = None
                        medecin = request.user.medecin

                        if medecin.contact.ville:
                            region_id = medecin.contact.ville.region.id
                        if medecin.contact.specialite:
                            cible_id = medecin.contact.specialite.id

                        # return different campaigns
                        default_campaigns = get_active_campaigns(
                            dest=AdsDestination.WEB,
                            cible_id=cible_id,
                            region_id=region_id,
                        )

                        for poste in request.user.medecin.postes.all():
                            if poste.licence:
                                if poste.licence.partenaire:
                                    # return all partner active camapign
                                    partner_campaigns = get_active_campaigns(
                                        poste.licence.partenaire,
                                        AdsDestination.WEB,
                                        cible_id=cible_id,
                                        region_id=region_id
                                    )
                                    out = list(uniq_chain(out, partner_campaigns))
                                else:
                                    out = list(uniq_chain(out, default_campaigns))

                        if not out:
                            out = default_campaigns

                        result = []
                        for c in out:
                            result.append(campaign_to_json(request, c, type=AdsDestination.WEB))
                        return Response(result, status=status.HTTP_200_OK)
                return Response(status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            traceback.print_exc()
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetAdView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    queryset = ''
    authentication_classes = (
        TokenAuthentication, SessionAuthentication
    )

    def get(self, request):
        """
        /annonce/get/?dest={1,5}&type={1|2|3}&size={}
        dest values:
            see AdsDestination class
        type values:
            DISPLAY == 1
            FEED == 2
            VIDEO == 3
        size values:
            see ADS_IMAGE_SIZE_CHOICES settings
        :param request:
        :return:
        """
        try:
            if not settings.ENABLE_WEB_ADS:
                return Response([], status=status.HTTP_200_OK)

            dest = request.GET.get('dest', None)
            type = request.GET.get('type', None)
            size = request.GET.get('size', None)
            rad = getAd(request, AdsDestination(dest), AdTypeHelper.get(type), size)
            if rad:
                return Response(rad, status=status.HTTP_200_OK)
            elif rad != None:
                return Response(status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            traceback.print_exc()
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdDownloadConfirationView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]
    serializer_class = AdDownloadConfirationSerializer

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(AdDownloadConfirationView, self).handle_log()

    def post(self, request):
        mac = request.META.get('HTTP_MAC', None)
        try:
            serializer = AdDownloadConfirationSerializer(
                data=request.data, context={'mac': mac}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            traceback.print_exc()
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UploadCampaignsStatisticsView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]
    serializer_class = UploadCampaignsStatisticsSerializer

    def should_log(self, request, response):
        return response.status_code >= 400

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(UploadCampaignsStatisticsView, self).handle_log()

    def post(self, request):
        mac = request.META.get('HTTP_MAC', None)
        try:
            serializer = UploadCampaignsStatisticsSerializer(
                data=request.data, context={'mac': mac}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            traceback.print_exc()
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
