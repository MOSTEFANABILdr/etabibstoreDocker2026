from drf_multiple_model.views import ObjectMultipleModelAPIView
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_tracking.mixins import LoggingMixin

from api.serializers.nomenclature_serializers import MotifSerializer, \
    FR18LinguisticVariantSerializer, NABMSerializer, LOINCSerializer, FindNomenclatureSerializer
from api.views.views import MACPermission
from core.models import Poste
from nomenclature.models import Motif, FR18LinguisticVariant, NABM, LOINC


class FindNomenclatureView(LoggingMixin, generics.GenericAPIView):
    serializer_class = FindNomenclatureSerializer
    queryset = ''

    # permission_classes = [MACPermission]

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(FindNomenclatureView, self).handle_log()

    def should_log(self, request, response):
        return response.status_code >= 400

    def get(self, request):
        """
        Find Nomenclature view
        :param request:
        :return: 200
                 400 BAD REQUEST
                 500 INTERNAL SERVER ERROR
        """
        q = request.GET.get('q', None)
        v = request.GET.get('v', None)
        serializer = FindNomenclatureSerializer(
            data={"q": q, "v": v}
        )
        if serializer.is_valid():
            d = serializer.save()
            return Response(d, status=status.HTTP_200_OK)
        else:
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FindLoincNabmAPIView(LoggingMixin, ObjectMultipleModelAPIView):
    permission_classes = [MACPermission]

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(FindLoincNabmAPIView, self).handle_log()

    def should_log(self, request, response):
        return response.status_code >= 400

    def get_querylist(self):
        q = self.request.GET.get('q', None)
        lang = self.request.GET.get('lang', 'fr')
        if lang == "fr":
            querylist = (
                {
                    'queryset': Motif.objects.filter(motif__icontains=q, categorie__id=17)[:10],
                    'serializer_class': MotifSerializer
                },
                {
                    'queryset': FR18LinguisticVariant.objects.filter(long_common_name__icontains=q)[:10],
                    'serializer_class': FR18LinguisticVariantSerializer
                },
                {
                    'queryset': NABM.objects.filter(libelle__icontains=q)[:10],
                    'serializer_class': NABMSerializer
                },
            )
            return querylist
        return (
            {
                'queryset': Motif.objects.filter(motif_en__icontains=q, categorie__id=17)[:10],
                'serializer_class': MotifSerializer
            },
            {
                'queryset': LOINC.objects.filter(long_common_name__icontains=q)[:10],
                'serializer_class': LOINCSerializer
            },
            {
                'queryset': NABM.objects.filter(libelle__icontains=q)[:10],
                'serializer_class': NABMSerializer
            },
        )

class FindMotifView(LoggingMixin, ReadOnlyModelViewSet):
    serializer_class = MotifSerializer
    queryset = ''

    # permission_classes = [MACPermission]

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(FindNomenclatureView, self).handle_log()

    def should_log(self, request, response):
        return response.status_code >= 400

    def get_queryset(self):
        q = self.request.GET.get('q', "")
        cat_ids = self.request.GET.get('cat_ids', None)
        if cat_ids and "," in cat_ids:
            cat_ids = cat_ids.split(",")
            return Motif.objects.filter(categorie__id__in=cat_ids, motif__icontains=q)[:20]
        elif cat_ids:
            return Motif.objects.filter(categorie__id=cat_ids, motif__icontains=q)[:20]
        return Motif.objects.filter(motif__icontains=q)[:20]
