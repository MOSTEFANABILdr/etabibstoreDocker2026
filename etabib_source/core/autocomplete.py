from cities_light.models import Region, Country, City
from dal import autocomplete
from django.contrib.auth.models import User, Permission
from django.db.models import Q
from django.utils import timezone
from taggit.models import Tag

from appointements.models import DemandeRendezVous
from core.enums import Role
from core.models import Medecin, CarteProfessionnelle, Grade, Qualification, Specialite, Contact, Operateur, \
    OffrePrepaye, OffrePartenaire, Licence, Article, Annonce, Bank, Facture, Patient, Stand, CategorieProduit, \
    Partenaire
from core.templatetags.avatar_tags import avatar
from core.templatetags.event_tags import is_tech_intervention, is_punctual_tracking, is_active_tracking
from core.templatetags.partner_tags import renderAnnonceType
from crm.models import Ville
from drugs.models import DciAtc, NomCommercial, Medicament, MedicamentCnas
from smsgateway.models import SmsModel, Listenvoi, EmailModel
from teleconsultation.models import Tdemand


class RecentlyDoctorAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Medecin.objects.none()
        recentlyDoctors = []
        tMedecins = Tdemand.objects.filter(patient__user=self.request.user) \
            .values_list('medecin__user', flat=True)
        dMedecins = DemandeRendezVous.objects.filter(demandeur=self.request.user) \
            .values_list('destinataire', flat=True)
        for p in tMedecins:
            if p not in recentlyDoctors:
                recentlyDoctors.append(p)
        for d in dMedecins:
            if d not in recentlyDoctors:
                recentlyDoctors.append(d)

        qs = Medecin.objects.filter(user__id__in=recentlyDoctors)
        if self.q:
            qs = qs.filter(
                Q(user__first_name__istartswith=self.q) | Q(user__last_name__istartswith=self.q)
            )
        return qs

    def get_result_label(self, item):
        return '{}{}'.format(avatar(item.user, width='40px', height='40px'), item.full_name)


class SpecialityAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        qs = Specialite.objects.all()
        if self.q:
            qs = qs.filter(Q(libelle__icontains=self.q) | Q(libelle_ar__icontains=self.q))
        return qs

    def get_result_label(self, item):
        return item.__str__()


class QualificationAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Qualification.objects.none()
        qs = Qualification.objects.all()
        if self.q:
            qs = qs.filter(libelle__icontains=self.q)
        return qs


class CountryAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        qs = Country.objects.all()
        if self.q:
            qs = qs.filter(name__istartswith=self.q)
        return qs


class CityAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        qs = City.objects.all()
        country = self.forwarded.get('country', None)
        region = self.forwarded.get('region', None)
        if country:
            qs = qs.filter(country__id=country)
        if region:
            qs = qs.filter(region__id=region)
        if self.q:
            qs = qs.filter(name__icontains=self.q)
        return qs

    def get_result_label(self, item):
        self.simple_label = self.forwarded.get('simple_label', False)
        if self.simple_label:
            return f'{item.name if item else ""} - {item.region.name if item.region else ""}'
        else:
            return super(CityAutocomplete, self).get_result_label(item)


class VilleAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        qs = Ville.objects.all()
        pays = self.forwarded.get('pays', None)
        wilaya = self.forwarded.get('wilaya', None)
        if pays:
            qs = qs.filter(pays__id=pays)
        if wilaya:
            qs = qs.filter(wilaya__id=wilaya)
        if self.q:
            qs = qs.filter(Q(nom__icontains=self.q) | Q(nom_ar__icontains=self.q))
        return qs

    def get_result_label(self, item):
        return f"{item.nom},  {item.nom_ar} - {item.wilaya.nom}"


class RegionAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Region.objects.none()
        qs = Region.objects.all()
        country = self.forwarded.get('country', None)
        if country:
            qs = qs.filter(country__id=country)
        if self.q:
            qs = qs.filter(name__istartswith=self.q)
        return qs

    def get_result_label(self, item):
        self.simple_label = self.forwarded.get('simple_label', False)
        if self.simple_label:
            return item.name
        else:
            return super(RegionAutocomplete, self).get_result_label(item)


class CityGoogleAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        qs = City.objects.all()
        country = self.forwarded.get('country', None)
        if country:
            qs = qs.filter(country__id=country)
        if self.q:
            qs = qs.filter(Q(name__istartswith=self.q) | Q(alternate_names__icontains=self.q))
        return qs


class TagAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Tag.objects.none()
        qs = Tag.objects.all()
        if self.q:
            qs = qs.filter(name__icontains=self.q)
        return qs


class UserAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return User.objects.none()
        qs = User.objects.all()
        if self.q:
            qs = qs.filter(
                Q(first_name__icontains=self.q) | Q(last_name__icontains=self.q) | Q(username__icontains=self.q))
        return qs


class CarteAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return CarteProfessionnelle.objects.none()
        qs = CarteProfessionnelle.objects.all()
        if self.q:
            CarteProfessionnelle.objects.all()
        return qs


class GradeAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Grade.objects.none()
        qs = Grade.objects.all()
        if self.q:
            qs = qs.filter(Q(libelle__icontains=self.q))
        return qs


class ContactAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Contact.objects.none()
        qs = Contact.objects.all()
        if self.q:
            qs = qs.filter(Q(nom__istartswith=self.q) | Q(prenom__istartswith=self.q))
            qs = qs.filter(partenaire=None)
        return qs


class ContactGoogleSpecialiteAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Specialite.objects.all()
        if self.q:
            qs = qs.filter(libelle__icontains=self.q)
        return qs

    def get_result_label(self, item):
        return item.libelle_ar or item.libelle


class OperateurAutocomplete(autocomplete.Select2QuerySetView):

    def get_result_label(self, result):
        groups = []
        for group in result.user.groups.all():
            groups.append(group.name)
        return "{} {} ({})".format(result.user.first_name, result.user.last_name, ', '.join(groups))

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Operateur.objects.none()
        qs = Operateur.objects.all()
        action_type = self.forwarded.get('type', None)
        if action_type:
            Permission
            if is_tech_intervention(action_type):
                qs = qs.filter(Q(user__groups__name=Role.TECHNICIAN.value))
            elif is_punctual_tracking(action_type) or is_active_tracking(action_type):
                qs = qs.filter(
                    Q(user__groups__name=Role.COMMERCIAL.value) | Q(user__groups__name=Role.COMMUNICATION.value))
        if self.q:
            qs = qs.filter(Q(user__first_name__istartswith=self.q) | Q(user__last_name__istartswith=self.q))
        return qs


class MedecinAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Medecin.objects.none()
        qs = Medecin.objects.all()
        if self.q:
            qs = qs.filter(Q(contact__nom__istartswith=self.q) | Q(contact__prenom__istartswith=self.q) | Q(
                user__username__istartswith=self.q))
        return qs


class PartnerAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Partenaire.objects.none()
        qs = Partenaire.objects.all()
        if self.q:
            qs = qs.filter(Q(contact__nom__istartswith=self.q) | Q(contact__prenom__istartswith=self.q) | Q(
                user__username__istartswith=self.q))
        return qs


class OffrePrepayeAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return OffrePrepaye.objects.none()
        disable_filter = self.forwarded.get('disable_filter', None)
        if disable_filter:
            qs = OffrePrepaye.objects.all()
        else:
            qs = OffrePrepaye.objects.filter(Q(date_expiration__gte=timezone.now()) & Q(date_debut__lte=timezone.now()))
        if self.q:
            qs = qs.filter(Q(libelle__istartswith=self.q))
        return qs


class OffrePartenaireAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return OffrePartenaire.objects.none()
        disable_filter = self.forwarded.get('disable_filter', None)
        if disable_filter:
            qs = OffrePrepaye.objects.all()
        else:
            qs = OffrePartenaire.objects.filter(
                Q(date_expiration__gte=timezone.now()) & Q(date_debut__lte=timezone.now()))
        if self.q:
            qs = qs.filter(Q(libelle__istartswith=self.q))
        return qs


class LicenseAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Licence.objects.none()
        if not self.request.user.groups.filter(name=Role.COMMERCIAL.value).exists():
            return Licence.objects.none()
        qs = Licence.objects.filter(fol_licensce_set__isnull=True, offre_perso_licence_set__isnull=True)
        if self.q:
            qs = qs.filter(Q(clef__istartswith=self.q))
        return qs


class DciAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return DciAtc.objects.none()
        qs = DciAtc.objects.all()
        if self.q:
            qs = qs.filter(Q(designation_fr__istartswith=self.q))
        return qs


class NomCommercialAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return NomCommercial.objects.none()
        qs = NomCommercial.objects.all()
        if self.q:
            qs = qs.filter(Q(nom_fr__istartswith=self.q))
        return qs


class MedicamentAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Medicament.objects.none()
        qs = Medicament.objects.all()
        if self.q:
            qs = qs.filter(
                Q(nom_commercial__nom_fr__istartswith=self.q)
                | Q(dci_atc__designation_fr__istartswith=self.q)
                | Q(dci_pays__istartswith=self.q)
            )
        return qs


class MedicamentCnasAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return MedicamentCnas.objects.none()
        qs = MedicamentCnas.objects.all()
        if self.q:
            qs = qs.filter(
                Q(nom_commercial__istartswith=self.q)
                | Q(nom_dci__istartswith=self.q)
                | Q(n_enregistrement__istartswith=self.q)
            )
        return qs


class ArticleAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Article.objects.none()
        qs = Article.soft_objects.filter(partenaire__user=self.request.user)
        if self.q:
            qs = qs.filter(Q(libelle__istartswith=self.q, partenaire__user=self.request.user))
        return qs


class AnnonceAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Annonce.objects.none()
        qs = Annonce.soft_objects.filter(partenaire__user=self.request.user)
        if self.q:
            qs = qs.filter(Q(libelle__contains=self.q, partenaire__user=self.request.user))
        return qs

    def get_result_label(self, item):
        return renderAnnonceType(item) + " %s" % item.libelle

    def get_selected_result_label(self, item):
        return item.libelle


class BankAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Bank.objects.none()
        qs = Bank.objects.all()
        if self.q:
            qs = qs.filter(name__icontains=self.q)
        return qs


class SmsModelAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return SmsModel.objects.none()
        if not self.request.user.groups.filter(
                name=Role.COMMUNICATION.value).exists() and not self.request.user.groups.filter(
            name=Role.COMMERCIAL.value).exists():
            return SmsModel.objects.none()
        qs = SmsModel.objects.all()
        return qs


class SmsListeAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Listenvoi.objects.none()
        if not self.request.user.groups.filter(name=Role.COMMUNICATION.value).exists() \
                and not self.request.user.groups.filter(name=Role.COMMERCIAL.value).exists():
            return Listenvoi.objects.none()
        qs = Listenvoi.objects.filter(cree_par=self.request.user.operateur)
        return qs


class EmailModelAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return EmailModel.objects.none()
        if not self.request.user.groups.filter(
                name=Role.COMMUNICATION.value).exists() and not self.request.user.groups.filter(
            name=Role.COMMERCIAL.value).exists():
            return EmailModel.objects.none()
        qs = EmailModel.objects.all()
        return qs


class DrugsModelAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return DciAtc.objects.none()
        qs = DciAtc.objects.all()
        if self.q:
            qs1 = qs.filter(medicament__nom_commercial__nom_fr__icontains=self.q)
            qs2 = qs.filter(designation_fr__istartswith=self.q)
            qs = (qs1 | qs2)
        return qs.exclude(
            medicament__nom_commercial__isnull=True
        ).exclude(
            medicament__isnull=True
        ).distinct()


class FactureAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Facture.objects.none()
        contact = self.forwarded.get('contact', None)
        if contact:
            qs = Facture.objects.filter(
                Q(medecin__contact=contact) | Q(partenaire__contact=contact)
            )
        else:
            qs = Facture.objects.none()
        if self.q:
            qs = qs.filter(
                Q(fol_facture_set__offre__libelle__icontains=self.q) |
                Q(fop_facture_set__offre__libelle__icontains=self.q)
            )
        return qs.distinct()

    def get_result_label(self, item):
        if item.offre_prepa:
            return "%s (%s DA)" % (
                item.offre_prepa.libelle, item.total_prix
            )
        elif item.offre_partenaire:
            return "%s (%s DA)" % (
                item.offre_partenaire.libelle, item.total_prix
            )


class PatientAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Patient.objects.none()
        qs = Patient.objects.all()
        if self.q:
            qs.filter(user__first_name__icontains=self.q, user__last_name__icontains=self.q)
        return qs


class StandsModelAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Stand.objects.none()
        qs = Stand.objects.filter(publie=True)
        if self.q:
            qs = qs.filter(Q(signaletique__icontains=self.q) |
                           Q(slogan__icontains=self.q) |
                           Q(partner__user__last_name__icontains=self.q) |
                           Q(partner__user__first_name__icontains=self.q))
        return qs


class CategorieProduitAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return CategorieProduit.objects.none()
        qs = CategorieProduit.objects.all()
        if self.q:
            qs = qs.filter(
                Q(titre_fr__icontains=self.q) | Q(titre_en__icontains=self.q) | Q(titre_ar__icontains=self.q))
        return qs

    def get_result_label(self, item):
        return item.titre_fr

    def create_object(self, text):
        return self.get_queryset().get_or_create(titre_fr=text, titre_en=text, titre_ar=text)[0]


class TypeExerciceAutocomplete(autocomplete.Select2ListView):
    def get_list(self):
        return Contact.TYPE_EXERCICE_CHOICES
