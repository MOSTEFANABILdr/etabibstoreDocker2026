import hashlib
import logging
import re
import traceback
from datetime import datetime

import pytz
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_auth.serializers import UserModel
from rest_framework import serializers

from core.enums import LicenceStatus
from core.models import Licence, Facture_OffrePrep_Licence, OffrePersonnalise_Service, Poste, Etabib, \
    Updater, Installation, Version, DemandeIntervention, Eula, IbnHamzaFeed, Patient
from core.utils import generateJwtToken
from drugs.models import Interaction, DciAtc, NomCommercial
from econgre.models import Congre, Webinar
from nomenclature.models import Dictionary
from stats.models import AtcdciStats, NomComercialStats

logger = logging.getLogger(__name__)


class UniqueIdentifierSerializer(serializers.Serializer):
    mac = serializers.CharField(max_length=255)

    def save(self):
        mac = self.validated_data['mac']
        return hashlib.sha256(mac.encode()).hexdigest()


class ActivationServiceSerializer(serializers.Serializer):
    mac = serializers.CharField(max_length=255)
    poste = serializers.CharField(max_length=255)
    key = serializers.CharField(max_length=255)

    # TODO: detect reinstallation if the client has 2 license in the same poste
    # Case: DR abou shamala ahmed

    def save(self):
        mac = self.validated_data['mac']
        poste_libelle = self.validated_data['poste']
        key = self.validated_data['key']

        result = {}
        try:
            licence = Licence.objects.get(clef=key)
            if not hasattr(licence, 'poste'):
                logger.info('licence %s has no poste' % licence)
                co = licence.current_offre()
                if co:
                    if isinstance(co, Facture_OffrePrep_Licence):
                        logger.info('current offer %s' % co.offre)
                        if not co.facture.medecin:
                            result['code'] = 405
                            result['status'] = _('https://store.etabib.dz')
                        else:
                            poste = Poste()
                            poste.licence = licence
                            poste.libelle = poste_libelle
                            poste.medecin = co.facture.medecin
                            poste.mac = mac
                            co.facture.medecin.points += co.offre.points

                            co.facture.medecin.save()
                            poste.save()

                            licence.date_actiavtion_licence = timezone.now()
                            poste.save()
                            licence.save()

                            result['code'] = 201
                            result['status'] = _("Installation")

                    elif isinstance(co, OffrePersonnalise_Service):
                        logger.info('current offer %s' % co.offre)
                        if co.offre.facture_pers_set.count() > 0:
                            facture = co.offre.facture_pers_set.all()[0]
                            if not facture.medecin:
                                result['code'] = 405
                                result['status'] = _('https://store.etabib.dz')
                            else:
                                poste = Poste()
                                poste.licence = licence
                                poste.libelle = poste_libelle
                                poste.medecin = facture.medecin
                                poste.mac = mac
                                facture.medecin.points = co.service.nb_jours

                                licence.date_actiavtion_licence = timezone.now()
                                poste.save()
                                licence.save()
                                facture.medecin.save()
                                result['code'] = 201
                                result['status'] = _("Installation")
                else:
                    result['code'] = 405
                    result['status'] = _('https://store.etabib.dz')
                    return result
            else:
                # reinstallation
                if licence.poste.mac == mac:
                    # TODO: case multiple offer
                    # case: the key is not expired
                    logger.info("license remaining days: %s " % licence.remaining_days)
                    if licence.remaining_days == LicenceStatus.UNLIMITED.value or licence.remaining_days > 0:
                        licence.poste.libelle = poste_libelle
                        licence.poste.save()
                        result['code'] = 200
                        result['status'] = _("Réinstallation")
                    else:
                        result['code'] = 403
                        result['status'] = _("La clé est déjà  consommée")
                else:
                    result['code'] = 403
                    result['status'] = _("La clé est associée à  un autre compte")

        except Licence.DoesNotExist:
            logger.info('invalid license key %s ' % key)
            result['code'] = 404
            result['status'] = _("La clé n'est pas valide")

        return result


class SIDSerializer(serializers.Serializer):
    sid = serializers.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac = self.context.get("mac")

    def save(self):
        sid = self.validated_data['sid']
        poste = Poste.objects.get(mac=self.mac)
        if not poste.sid:
            poste.sid = sid
            poste.save()
        elif poste.sid != sid:
            return False
        return True


class CheckForUpdatesSerializer(serializers.Serializer):
    etabib_version = serializers.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac = self.context.get("mac")
        self.request = self.context.get("request")

    def validate_etabib_version(self, etabib_version):
        if etabib_version == "UNK":
            return etabib_version
        matcher = re.match("(^\d+\.\d+\.\d+)(.*)", etabib_version)
        if not bool(matcher):
            raise serializers.ValidationError(_("Version number must be in the format X.Y.Z"))

        return etabib_version

    def etabibLastVersion(self):
        etabib = Etabib.getLastVersion()
        if etabib:
            return {'id': etabib.pk, 'version': etabib.version,
                    'path': self.request.build_absolute_uri(etabib.zipfile.url)}
        return None

    def etabibNewestVersions(self, id):
        etabibs = []
        etbs = Etabib.getNewestVersions(id)
        if etbs:
            for etabib in etbs:
                etabibs.append({'id': etabib.pk, 'version': etabib.version,
                                'path': self.request.build_absolute_uri(etabib.zipfile.url)})
        return etabibs

    def save(self):
        etabib_version = self.validated_data['etabib_version']
        poste = Poste.objects.get(mac=self.mac)
        etabibs = []
        updater = {}
        plugins_to_install = []
        plugins_to_uninstall = []
        plugins_to_update = []
        plugins_to_disactivate = []

        if poste.blocked:
            return {
                "etabibs": etabibs,
                "updater": updater,
                "plugins": plugins_to_install,
                "plugins_to_uninstall": plugins_to_uninstall,
                "plugins_to_update": plugins_to_update,
                "plugins_to_disactivate": plugins_to_disactivate
            }

        """
            Check for eTabib workspace updates
        """
        if etabib_version == "UNK":
            if self.etabibLastVersion():
                etabibs.append(self.etabibLastVersion())
        else:
            # Case: the client has a record in the database
            if poste.etabibappliction:
                # Case: enregistred client version == client version sent
                if poste.etabibappliction.version == etabib_version:
                    if not poste.etabibappliction.lastversion:
                        env = self.etabibNewestVersions(poste.etabibappliction.id)
                        if env:
                            etabibs.extend(env)
                    else:
                        env = self.etabibNewestVersions(poste.etabibappliction.id)
                        if env:
                            etabibs.extend(env)
                else:
                    # Case: enregistred client version != client version sent
                    env = self.etabibNewestVersions(etabib_version)
                    if env:
                        etabibs.extend(env)
            else:
                # Case: client has not a record in the database
                # Insert a record
                lv = Etabib.getLastVersion()
                if lv:
                    # Case: client version == lastversion
                    if etabib_version == lv.version:
                        poste.etabibappliction = lv
                        poste.save()
                    else:
                        # Case: client version != lastversion
                        if Etabib.isValidVersion(etabib_version):
                            # Case: client has a valid version
                            poste.etabibappliction = Etabib.getByVersion(etabib_version)
                            poste.save()

                            env = self.etabibNewestVersions(etabib_version)
                            if env:
                                etabibs.extend(env)

        """
            Check for the updater updates
        """
        if poste.updater:
            if not poste.updater.last_version:
                upd = Updater.getLastVersion()
                updater.update({'id': upd.id, 'version': upd.version,
                                'path': self.request.build_absolute_uri(upd.zipfile.url)})

        """
            Check for plugins installations ,uninstallations and updates
        """
        if poste.modules.exists():
            for vers in poste.modules.all():
                inst = Installation.objects.get(poste=poste, version=vers)
                if inst.a_installer:
                    plugins_to_install.append({'installationID': inst.id, 'libelle': inst.version.module.libelle,
                                               'version': inst.version.number,
                                               'path': self.request.build_absolute_uri(inst.version.zipfile.url),
                                               'image': self.request.build_absolute_uri(inst.version.module.icon.url)
                                               })

                elif inst.a_desinstaller:
                    plugins_to_uninstall.append({'installationID': inst.id, 'unique_id': inst.version.module.unique_id,
                                                 'libelle': inst.version.module.libelle})

                elif inst.a_mettre_a_jour:
                    lv = inst.version.module.getLastVersion()
                    plugins_to_update.append({'installationID': inst.id, 'libelle': lv.module.libelle,
                                              'version': lv.number,
                                              'versionID': lv.id,
                                              'path': self.request.build_absolute_uri(lv.zipfile.url),
                                              'image': self.request.build_absolute_uri(lv.module.icon.url)})
        """
            Check for plugins to deactivate
        """
        if poste.desactive_apps:
            if poste.modules.exists():
                for vers in poste.modules.all():
                    if vers.module:
                        if vers.module.consomation > 0:
                            if vers.module.unique_id:
                                plugins_to_disactivate.append(
                                    vers.module.unique_id
                                )

        result = {
            "etabibs": etabibs,
            "updater": updater,
            "plugins": plugins_to_install,
            "plugins_to_uninstall": plugins_to_uninstall,
            "plugins_to_update": plugins_to_update,
            "plugins_to_disactivate": plugins_to_disactivate
        }
        return result


class ConfirmEtabibInstallationSerializer(serializers.Serializer):
    id = serializers.IntegerField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac = self.context.get("mac")

    def validate_id(self, id):
        if not Etabib.objects.filter(pk=id).exists():
            raise serializers.ValidationError(_("Etabib id is not valid"))
        return id

    def save(self):
        id = self.validated_data['id']
        poste = Poste.objects.get(mac=self.mac)
        etabib = Etabib.objects.get(id=id)

        poste.etabibappliction = etabib
        poste.save()


class ConfirmPluginInstallationSerializer(serializers.Serializer):
    id = serializers.IntegerField()

    def validate_id(self, id):
        if not Installation.objects.filter(pk=id).exists():
            raise serializers.ValidationError(_("Installation id is not valid"))
        return id

    def save(self):
        id = self.validated_data['id']
        installation = Installation.objects.get(id=id)
        installation.a_installer = False
        installation.save()


class ConfirmPluginUninstallationSerializer(serializers.Serializer):
    id = serializers.IntegerField()

    def validate_id(self, id):
        if not Installation.objects.filter(pk=id, a_desinstaller=True).exists():
            raise serializers.ValidationError(_("Installation id is not valid"))
        return id

    def save(self):
        id = self.validated_data['id']
        installation = Installation.objects.get(id=id)
        installation.delete()


class ConfirmPluginUpdateSerializer(serializers.Serializer):
    inst_id = serializers.IntegerField()
    vers_id = serializers.IntegerField()

    def validate_inst_id(self, inst_id):
        inst = Installation.objects.filter(pk=inst_id)
        if not inst.exists():
            raise serializers.ValidationError(_("Installation id is not valid"))
        elif not inst.first().a_mettre_a_jour:
            raise serializers.ValidationError(_("Installation id is not valid"))
        return inst_id

    def validate_vers_id(self, vers_id):
        version = Version.objects.filter(pk=vers_id)
        if not version.exists():
            raise serializers.ValidationError(_("Version id is not valid"))
        return vers_id

    def save(self):
        vers_id = self.validated_data['vers_id']
        inst_id = self.validated_data['inst_id']
        installation = Installation.objects.get(id=inst_id)
        version = Version.objects.get(id=vers_id)

        installation.version = version
        installation.save()


class CheckForMigrationSerializer(serializers.Serializer):
    old_mac = serializers.CharField(max_length=255, required=True)

    def validate_old_mac(self, old_mac):
        try:
            Poste.objects.get(Q(old_mac=old_mac) | Q(mac=old_mac))
        except Poste.DoesNotExist:
            raise serializers.ValidationError(_("mac is not valid"))
        return old_mac

    def save(self, **kwargs):
        old_mac = self.validated_data['old_mac']
        poste = Poste.objects.get(Q(old_mac=old_mac) | Q(mac=old_mac))
        return poste


class DoMigrationSerializer(serializers.Serializer):
    new_mac = serializers.CharField(max_length=255, required=True)
    old_mac = serializers.CharField(max_length=255, required=True)

    def validate_old_mac(self, old_mac):
        try:
            Poste.objects.get(old_mac=old_mac)
        except Poste.DoesNotExist:
            raise serializers.ValidationError(_("Old mac is not valid"))
        return old_mac

    def validate(self, data):
        poste = Poste.objects.get(old_mac=data['old_mac'])
        if poste.mac:
            raise serializers.ValidationError(_("Mac already set"))
        return data

    def save(self, **kwargs):
        old_mac = self.validated_data['old_mac']
        new_mac = self.validated_data['new_mac']
        poste = Poste.objects.get(old_mac=old_mac)
        poste.mac = new_mac
        return poste


class ConfirmUpdaterInstallationSerializer(serializers.Serializer):
    id = serializers.IntegerField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac = self.context.get("mac")

    def validate_id(self, id):
        if not Updater.objects.filter(pk=id).exists():
            raise serializers.ValidationError(_("Updater id is not valid"))
        return id

    def save(self):
        id = self.validated_data['id']
        poste = Poste.objects.get(mac=self.mac)
        updater = Updater.objects.get(id=id)

        poste.updater = updater
        poste.save()


class DrugInteractionSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.CharField()
    )

    def save(self, **kwargs):
        ids = self.validated_data['ids']
        # create pairs
        d = []
        for i, m in enumerate(ids, start=1):
            for j, p in enumerate(ids[i:]):
                d.append((m, p))

        # check interaction
        result = []
        for pair in d:
            inters = Interaction.objects.filter(
                Q(dci_atc_a__unique_id=pair[0], dci_atc_b__unique_id=pair[1]) |
                Q(dci_atc_b__unique_id=pair[0], dci_atc_a__unique_id=pair[1])
            ).distinct()
            for int in inters:
                d = dict()
                d['type'] = int.type_interraction
                d['risque'] = int.risque
                d['cat'] = int.cat
                d['dciAtcA'] = int.dci_atc_a.unique_id
                d['dciAtcB'] = int.dci_atc_b.unique_id
                result.append(d)

        return result




class CollectStatisticsChildSerializer(serializers.Serializer):
    dci = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    nc = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    date = serializers.CharField(max_length=255, required=True)

    def validate_dci(self, dci):
        return dci

    def validate_nc(self, nc):
        return nc


class CollectStatisticsSerializer(serializers.Serializer):
    items = CollectStatisticsChildSerializer(many=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac = self.context.get("mac")

    def save(self, **kwargs):
        items = self.validated_data['items']

        results = []
        for item in items:
            dci = item.get("dci", None)
            nc = item.get("nc", None)
            date = item.get("date", None)
            if dci:
                try:
                    dciAtc = DciAtc.objects.get(unique_id=dci)
                    poste = Poste.objects.get(mac=self.mac)
                    d = datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f')

                    localtz = pytz.timezone('Africa/Algiers')
                    dt_aware = localtz.localize(d)

                    ncs = AtcdciStats()
                    ncs.poste = poste
                    ncs.date_insertion = dt_aware
                    ncs.atcdci = dciAtc

                    results.append(ncs)
                except Exception as e:
                    traceback.print_exc()
                    print(e)

            if nc:
                try:
                    nomCommercial = NomCommercial.objects.get(unique_id=nc)
                    poste = Poste.objects.get(mac=self.mac)
                    d = datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f')

                    localtz = pytz.timezone('Africa/Algiers')
                    dt_aware = localtz.localize(d)

                    ncs = NomComercialStats()
                    ncs.poste = poste
                    ncs.date_insertion = dt_aware
                    ncs.nomCommercial = nomCommercial

                    results.append(ncs)
                except Exception as e:
                    traceback.print_exc()
                    print(e)
        return results


class MacAuthSerializer(serializers.Serializer):
    mac = serializers.CharField(max_length=255, required=True)

    def validate_mac(self, mac):
        if not Poste.objects.filter(mac=mac).exists():
            raise serializers.ValidationError("Mac does not exits")
        return mac

    def save(self, **kwargs):
        mac = self.validated_data['mac']
        poste = Poste.objects.get(mac=mac)
        if poste.medecin:
            if poste.medecin.user:
                return poste.medecin.user
        return None


class DemandeIntervetionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemandeIntervention
        fields = ['id', 'en_rapport_avec', 'description', 'capture']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac = self.context.get("mac")

    def hasAnotherDemand(self):
        poste = Poste.objects.get(mac=self.mac)

        today = timezone.now().today()

        fday = datetime.combine(today, datetime.min.time())
        ldat = datetime.combine(today, datetime.max.time())

        if DemandeIntervention.objects.filter(
                poste=poste, date_demande__lte=ldat,
                date_demande__gte=fday).exists():
            return True
        return False

    def create(self, validated_data):
        obj = DemandeIntervention()
        obj.en_rapport_avec = self.validated_data.get('en_rapport_avec', None)
        obj.description = self.validated_data.get('description', None)
        obj.capture = self.validated_data.get('capture', None)
        obj.poste = Poste.objects.get(mac=self.mac)
        obj.save()
        return obj


class DictionarySerializer(serializers.Serializer):
    q = serializers.CharField(max_length=255, required=True)
    lang = serializers.CharField(max_length=255, required=True)

    def get_list(self, snippets, lang):
        out = []
        for s in snippets:
            if lang == "fr":
                out.append(s.designation_fr)
            if lang == "en":
                out.append(s.designation_en)
            if lang == "es":
                out.append(s.designation_es)
            if lang == "ar":
                out.append(s.designation_ar)
        return out

    def save(self, **kwargs):
        q = self.validated_data['q']
        lang = self.validated_data['lang']

        snippets = None;
        if lang == 'fr':
            snippets = Dictionary.objects.filter(designation_fr__istartswith=q)[:5]
        elif lang == 'en':
            snippets = Dictionary.objects.filter(designation_en__istartswith=q)[:5]
        elif lang == 'ar':
            snippets = Dictionary.objects.filter(designation_ar__istartswith=q)[:5]
        elif lang == 'es':
            snippets = Dictionary.objects.filter(designation_es__istartswith=q)[:5]

        return self.get_list(snippets, lang)


class CheckEulaSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac = self.context.get("mac")

    def save(self, **kwargs):
        poste = Poste.objects.get(mac=self.mac)
        eulalv = Eula.getLastVersion()
        return not eulalv or eulalv == poste.eula


class AcceptEulaSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True)

    def validate_id(self, id):
        if not Eula.objects.filter(id=id).exists():
            raise serializers.ValidationError("Eula id does not exits")
        return id

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac = self.context.get("mac")

    def save(self, **kwargs):
        id = self.validated_data['id']
        poste = Poste.objects.get(mac=self.mac)
        eula = Eula.objects.get(id=id)
        poste.eula = eula
        poste.save()


class IbnHamzaFeedSerializer(serializers.Serializer):

    def save(self, **kwargs):
        feeds = IbnHamzaFeed.objects.filter(date_expiration__gt=timezone.now())
        out = []
        for feed in feeds:
            d = dict()
            d['libelle'] = feed.libelle
            d['description'] = feed.description
            d['date_expiration'] = feed.date_expiration
            d['date_creation'] = feed.date_expiration
            d['lien'] = feed.lien
            out.append(d)
        return out


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'solde', 'nom', 'prenom']


class EcongreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Congre
        exclude = ['date_maj', 'date_creation']


class WebinarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webinar
        exclude = ['salle_discussion', 'mot_de_passe', 'date_maj', 'date_creation']


class CustomUserDetailsSerializer(serializers.ModelSerializer):
    jwt = serializers.SerializerMethodField()

    def get_jwt(self, obj):
        return generateJwtToken(obj)

    class Meta:
        model = UserModel
        fields = ('pk', 'username', 'email', 'first_name', 'last_name', 'jwt')
        read_only_fields = ('email',)


