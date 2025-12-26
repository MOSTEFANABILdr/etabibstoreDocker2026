import base64

import pyDes
from PIL import Image
from rest_auth.views import UserDetailsView
from rest_framework import status, permissions, generics
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.exceptions import ParseError
from rest_framework.parsers import FileUploadParser, FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_tracking.mixins import LoggingMixin
from rest_framework_xml.renderers import XMLRenderer

from api.serializers.auth_serializers import RegisterFromInstallerSerializer
from api.serializers.serializers import *
from core.enums import LicenceStatus
from core.models import Poste, DemandeInterventionImage, BddScript
from etabibWebsite import settings


class MACPermission(permissions.BasePermission):
    message = 'Only eTabib user can access APIs'

    def has_permission(self, request, view):
        mac = request.META.get('HTTP_MAC', None)
        if mac:
            try:
                Poste.objects.get(mac=mac)
            except Poste.DoesNotExist:
                return False
        else:
            return False
        return True


class GenerateUniqueIdentifierView(LoggingMixin, generics.GenericAPIView):
    serializer_class = UniqueIdentifierSerializer

    def get(self, request, mac):
        """
            generating a unique id for clients
        """
        serializer = UniqueIdentifierSerializer(data={'mac': mac})
        if serializer.is_valid():
            uniqueid = serializer.save()
            return Response({"id": "%s" % uniqueid}, status=status.HTTP_201_CREATED)
        else:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ActivateLicenceView(LoggingMixin, generics.GenericAPIView):
    serializer_class = ActivationServiceSerializer

    def handle_log(self):
        super(ActivateLicenceView, self).handle_log()

    def post(self, request):
        """
        Avtivation service
        """
        serializer = ActivationServiceSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SetLastConnectionDateView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(SetLastConnectionDateView, self).handle_log()

    def get(self, request):
        mac = request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            poste.date_derniere_connexion = timezone.now()
            poste.save()
            return Response(status=status.HTTP_200_OK)
        except Poste.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CheckSIDView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]
    serializer_class = SIDSerializer

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(CheckSIDView, self).handle_log()

    def post(self, request):
        """
        Check the security identifier
        """
        mac = request.META.get('HTTP_MAC', None)
        try:
            serializer = SIDSerializer(data=request.data, context={'mac': mac})
            if serializer.is_valid():
                result = serializer.save()
                if result:
                    return Response(status=status.HTTP_200_OK)
                else:
                    return Response(status=status.HTTP_403_FORBIDDEN)
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateCertificatesView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(GenerateCertificatesView, self).handle_log()

    def get(self, request):
        """
        Generate Certificates
        """
        try:
            mac = request.META.get('HTTP_MAC', None)
            poste = Poste.objects.get(mac=mac)
            if poste.licence:
                licence = poste.licence
                # date de ref certificat
                drCert = timezone.now().strftime("%d/%m/%Y")
                # user's credits certificat in seconds
                creditInDays = licence.remaining_days if licence.remaining_days != LicenceStatus.UNLIMITED.value else 7600
                if creditInDays > 90:
                    creditCert = 90 * 24 * 60 * 60;
                else:
                    creditCert = 0 if creditInDays <= 0 else creditInDays * 24 * 60 * 60
                # encrypt certificats
                key = "a3s5D7D5"
                d = pyDes.des(key, padmode=pyDes.PAD_PKCS5)
                return Response({"dateref": "%s" % base64.b64encode(d.encrypt(drCert)).decode('utf-8'),
                                 "credit": "%s" % base64.b64encode(d.encrypt(str(creditCert))).decode('utf-8')},
                                status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CheckForUpdatesView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]
    serializer_class = CheckForUpdatesSerializer

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(CheckForUpdatesView, self).handle_log()

    def get(self, request, version):
        """
            Check for updates
        """
        try:
            mac = request.META.get('HTTP_MAC', None)
            serializer = CheckForUpdatesSerializer(
                data={'etabib_version': version}, context={'mac': mac, 'request': request}
            )
            if serializer.is_valid():
                result = serializer.save()
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfirmEtabibInstallationView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]
    serializer_class = ConfirmEtabibInstallationSerializer

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(ConfirmEtabibInstallationView, self).handle_log()

    def post(self, request):
        """
            Confirm etabib installation
        """
        try:
            mac = request.META.get('HTTP_MAC', None)
            serializer = ConfirmEtabibInstallationSerializer(
                data=request.data, context={'mac': mac}
            )
            if serializer.is_valid():
                result = serializer.save()
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfirmUpdaterInstallationView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]
    serializer_class = ConfirmUpdaterInstallationSerializer

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(ConfirmUpdaterInstallationView, self).handle_log()

    def post(self, request):
        """
            Confirm updater installation
        """
        try:
            mac = request.META.get('HTTP_MAC', None)
            serializer = ConfirmUpdaterInstallationSerializer(
                data=request.data, context={'mac': mac}
            )
            if serializer.is_valid():
                result = serializer.save()
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfirmPluginInstallationView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]
    serializer_class = ConfirmPluginInstallationSerializer

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(ConfirmPluginInstallationView, self).handle_log()

    def post(self, request):
        """
            Confirm plugin installation
        """
        try:
            serializer = ConfirmPluginInstallationSerializer(
                data=request.data
            )
            if serializer.is_valid():
                result = serializer.save()
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfirmPluginUninstallationView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]
    serializer_class = ConfirmPluginUninstallationSerializer

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(ConfirmPluginUninstallationView, self).handle_log()

    def post(self, request):
        """
            Confirm plugin uninstallation
        """
        serializer = ConfirmPluginUninstallationSerializer(
            data=request.data
        )
        try:
            if serializer.is_valid():
                result = serializer.save()
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfirmPluginUpdateView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]
    serializer_class = ConfirmPluginUpdateSerializer

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(ConfirmPluginUpdateView, self).handle_log()

    def post(self, request):
        """
            Confirm plugin update
        """
        try:
            serializer = ConfirmPluginUpdateSerializer(
                data=request.data
            )
            if serializer.is_valid():
                result = serializer.save()
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LuXMLRenderer(XMLRenderer):
    root_tag_name = 'item'


class LastUpdaterView(LoggingMixin, generics.GenericAPIView):
    renderer_classes = [LuXMLRenderer]

    def get(self, request):
        try:
            lupdater = Updater.getLastVersion()
            updater_xml = dict()
            updater_xml['id'] = lupdater.id
            updater_xml['version'] = lupdater.version
            updater_xml['url'] = request.build_absolute_uri(lupdater.zipfile.url)
            updater_xml['mandatory'] = "true"

            if lupdater:
                return Response(updater_xml, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CheckForMigrationView(LoggingMixin, generics.GenericAPIView):
    serializer_class = CheckForMigrationSerializer

    def post(self, request):
        """
        Check for migration
        :param request:
        :return: 200 {"migrate": true}
                 200 {"migrate": false}
                 400 BAD REQUEST : if old_mac does not exist in the database
                 500 INTERNAL SERVER ERROR: internal error
        """
        try:
            serializer = CheckForMigrationSerializer(
                data=request.data
            )
            if serializer.is_valid():
                poste = serializer.save()
                result = {"migrate": True if not poste.mac else False}
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DoMigrationView(LoggingMixin, generics.GenericAPIView):
    serializer_class = DoMigrationSerializer

    def post(self, request):
        """
        Do migration
        :param request:
        :return: 200
                 400 BAD REQUEST : if old_mac does not exist in the database or new_mac is None or new_mac is already set
                 500 INTERNAL SERVER ERROR: internal error
        """
        try:
            serializer = DoMigrationSerializer(
                data=request.data
            )
            if serializer.is_valid():
                poste = serializer.save()
                poste.save()
                return Response(status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DrugInteractionView(LoggingMixin, generics.GenericAPIView):
    serializer_class = DrugInteractionSerializer
    permission_classes = [MACPermission]

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(DrugInteractionView, self).handle_log()

    def post(self, request):
        """
        Drug interaction view
        :param request:
        :return: 200
                 400 BAD REQUEST
                 500 INTERNAL SERVER ERROR
        """
        try:
            serializer = DrugInteractionSerializer(
                data=request.data
            )
            if serializer.is_valid():
                d = serializer.save()
                return Response(d, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CollectStatisticsView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]
    serializer_class = CollectStatisticsSerializer

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(CollectStatisticsView, self).handle_log()

    def post(self, request):
        """
        :param request:
        :return: 200
                 400 BAD REQUEST
                 500 INTERNAL SERVER ERROR
        """
        mac = request.META.get('HTTP_MAC', None)
        try:
            serializer = CollectStatisticsSerializer(
                data=request.data, context={'mac': mac}
            )
            if serializer.is_valid():
                results = serializer.save()
                for res in results:
                    res.save()
                return Response(status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MacAuthToken(ObtainAuthToken):
    serializer_class = MacAuthSerializer

    def post(self, request, *args, **kwargs):
        serializer = MacAuthSerializer(data=request.data,
                                       context={'request': request})
        try:
            if serializer.is_valid():
                user = serializer.save()
                if user:
                    token, created = Token.objects.get_or_create(user=user)
                    return Response({
                        'token': token.key
                    })
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DemandeIntervetionCreate(LoggingMixin, generics.GenericAPIView):
    """
    Create a new Demande Intervetion
    """
    serializer_class = DemandeIntervetionSerializer
    permission_classes = [MACPermission]

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:

            pass
        super(DemandeIntervetionCreate, self).handle_log()

    def post(self, request, format=None):
        try:
            mac = request.META.get('HTTP_MAC', None)
            serializer = DemandeIntervetionSerializer(data=request.data, context={'mac': mac})
            if serializer.is_valid():
                if serializer.hasAnotherDemand():
                    return Response(serializer.data, status=status.HTTP_406_NOT_ACCEPTABLE)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ImageUploadParser(FileUploadParser):
    media_type = 'image/*'


class DiImageUploadView(APIView):
    parser_class = (ImageUploadParser,)
    permission_classes = [MACPermission]

    def put(self, request, format=None):
        if 'file' not in request.data:
            raise ParseError("Empty content")

        file = request.data['file']

        try:
            img = Image.open(file)
            img.verify()
        except:
            raise ParseError("Unsupported image type")

        dimg = DemandeInterventionImage()
        dimg.image = file
        dimg.save()

        return Response({"image": dimg.pk}, status=status.HTTP_201_CREATED)


class DictionaryViewSet(APIView):
    serializer_class = DictionarySerializer
    permission_classes = [MACPermission]
    queryset = ''

    def get(self, request, format=None):
        lang = request.GET.get('lang', 'fr')
        q = request.GET.get('q', None)

        try:
            serializer = DictionarySerializer(
                data={"q": q, "lang": lang}
            )
            if serializer.is_valid():
                d = serializer.save()
                return Response(d, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CheckEulaView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]
    serializer_class = CheckEulaSerializer

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(CheckEulaView, self).handle_log()

    def get(self, request):
        """
        Check Eula
        :param request:
        :return: 200 up to date
                 201 not uptodate get last version
                 400 BAD REQUEST
                 500 INTERNAL SERVER ERROR
        """
        mac = request.META.get('HTTP_MAC', None)
        try:
            serializer = CheckEulaSerializer(
                data=request.data, context={'mac': mac}
            )
            if serializer.is_valid():
                updated = serializer.save()
                if updated:
                    return Response(status=status.HTTP_200_OK)
                else:
                    eula = Eula.getLastVersion()
                    d = dict()
                    d["id"] = eula.id
                    d["contenu"] = eula.description
                    return Response(d, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AcceptEulaView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]
    serializer_class = AcceptEulaSerializer

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(AcceptEulaView, self).handle_log()

    def get(self, request, id):
        """
        Check Eula
        :param request:
        :return: 200
                 400 BAD REQUEST
                 500 INTERNAL SERVER ERROR
        """
        mac = request.META.get('HTTP_MAC', None)
        try:
            serializer = AcceptEulaSerializer(
                data={"id": id}, context={'mac': mac}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IbnHamzaFeedView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]
    serializer_class = IbnHamzaFeedSerializer

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(IbnHamzaFeedView, self).handle_log()

    def get(self, request):
        """
        Get Ibnhamza feeds
        :param request:
        :return: 200 LIST OF IBNHAMZAFEED OBjects
                 400 BAD REQUEST
                 500 INTERNAL SERVER ERROR
        """
        try:
            serializer = IbnHamzaFeedSerializer(data=request.data)
            if serializer.is_valid():
                feeds = serializer.save()
                return Response(feeds, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetEconsultationDomain(LoggingMixin, generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication, SessionAuthentication)

    def get(self, request):
        domain = settings.ECONSULTATION_JITSI_DOMAIN_NAME
        return Response({"domain": domain}, status=status.HTTP_200_OK)


class CustomUserDetailsView(UserDetailsView):
    serializer_class = CustomUserDetailsSerializer
    permission_classes = (IsAuthenticated,)


class RegisterFromInstallerView(LoggingMixin, generics.GenericAPIView):
    serializer_class = RegisterFromInstallerSerializer
    """
        register a doctor from eTabib workspace installer
    """

    def post(self, request):
        serializer = RegisterFromInstallerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(request=request)
            return Response({}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetBddScriptView(LoggingMixin, generics.GenericAPIView):
    permission_classes = [MACPermission]

    def handle_log(self):
        mac = self.request.META.get('HTTP_MAC', None)
        try:
            poste = Poste.objects.get(mac=mac)
            self.log['user'] = poste.medecin.user
        except Exception as e:
            pass
        super(GetBddScriptView, self).handle_log()

    def get(self, request):
        bddscript = BddScript.getLastVersion()
        if bddscript:
            out = dict()
            out['id'] = bddscript.id
            out['version'] = bddscript.version
            out['url'] = request.build_absolute_uri(bddscript.zipfile.url)
            return Response(out, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)