from datetime import timedelta

from allauth.account.models import EmailAddress
from dal import autocomplete, forward
from django import forms
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.sites.models import Site
from django.db import transaction
from django.db.models import Q
from django.forms import DateInput
from django.shortcuts import redirect
from django.template.defaultfilters import safe
from django.urls import reverse
from import_export.fields import Field
from django.utils.html import escape, mark_safe
from django.utils.translation import gettext as _
from imagekit.admin import AdminThumbnail
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from post_office import mail
from post_office.admin import EmailAdmin
from post_office.models import Email
from rangefilter.filters import DateRangeFilter
from taggit.models import Tag
from tracking.models import Pageview, Visitor
from translated_fields import TranslatedFieldAdmin

from core.enums import Role
from core.models import *
from core.templatetags.partner_tags import renderCampagneStatus
from core.templatetags.role_tags import has_no_role
from core.utils import createCommand
from dicom.models import Dicom_Patient
from etabibWebsite import settings
from smsgateway.utils import verify_number
from smsicosnet.utils import send_sms_icosnet


# ===============================================================================
# Custom ModelResources
# ===============================================================================
class ModuleResource(resources.ModelResource):
    class Meta:
        model = Module
        fields = ('id', 'libelle', 'type_consomation', 'consomation')


class UserResource(resources.ModelResource):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'username', 'email', 'password', 'last_login', 'groups',
                  'is_active')


class EtabibResource(resources.ModelResource):
    class Meta:
        model = Etabib


class VersionResource(resources.ModelResource):
    class Meta:
        model = Version


class MedecinResource(resources.ModelResource):
    class Meta:
        model = Medecin
        fields = ('id', 'contact', 'num_ordre', 'num_agrement', 'user')


class RegistredUserResource(resources.ModelResource):
    telephone = Field()
    profile = Field()

    class Meta:
        model = RegistredUser
        fields = ('id', 'first_name', 'last_name', 'email', 'profile', 'date_joined', 'telephone')
        export_order = ('id', 'first_name', 'last_name', 'email', 'profile', 'date_joined', 'telephone')

    def dehydrate_telephone(self, obj):
        if hasattr(obj, "patient"):
            return obj.patient.telephone
        if hasattr(obj, "medecin"):
            tels = []
            if obj.medecin.contact.mobile:
                tels.append(obj.medecin.contact.mobile)
            if obj.medecin.contact.mobile_1:
                tels.append(obj.medecin.contact.mobile_1)
            if obj.medecin.contact.mobile_2:
                tels.append(obj.medecin.contact.mobile_2)
            if obj.medecin.contact.fixe:
                tels.append(obj.medecin.contact.fixe)
            return " | ".join(tel for tel in tels)

    def dehydrate_profile(self, obj):
        return " | ".join(group.name for group in obj.groups.all())

class ContactResource(resources.ModelResource):
    class Meta:
        model = Contact
        fields = ('id', 'nom', 'prenom', 'adresse', 'fixe', 'mobile', 'specialite', 'departement',
                  'pays', 'carte')


class GradeResource(resources.ModelResource):
    class Meta:
        model = Grade
        fields = ('id', 'libelle',)


# ===============================================================================
# Custom Forms
# ===============================================================================
class OperateurForm(forms.ModelForm):
    zones = forms.ModelMultipleChoiceField(
        required=False,
        label=_('Zones'),
        queryset=Region.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(
            url='region-autocomplete',
            attrs={'data-html': True}
        ),
    )

    class Meta:
        model = Operateur
        # exclude = ['zones']
        fields = "__all__"
        widgets = {
            "user": autocomplete.ModelSelect2(url='user-autocomplete', )
        }

    class Media:
        js = [
            "admin/js/vendor/jquery/jquery.js",
            "autocomplete_light/jquery.init.js",
            "vendor/select2/dist/js/select2.full.js",
            "admin/js/vendor/select2/select2.full.js",
        ]


class OperateurAdmin(admin.ModelAdmin):
    form = OperateurForm
    list_display = ("id", "get_name", "phone", "sexe")

    def get_name(self, obj):
        if obj.user:
            return f'{obj.user.first_name} {obj.user.last_name}'


class ContactForm(forms.ModelForm):
    pays = forms.ModelChoiceField(
        label=_('Pays'),
        queryset=Country.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='country-autocomplete',
            attrs={
                'data-placeholder': _('Choisir un pays ...'),
            }
        ),
    )
    ville = forms.ModelChoiceField(
        label=_('Ville'),
        queryset=City.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='city-autocomplete',
            forward=[forward.Field('pays', 'country')],
            attrs={
                'data-placeholder': _('Choisir une ville ...')
            }
        ),
    )

    class Meta:
        model = Contact
        fields = ('__all__')
        widgets = {
            'specialite': autocomplete.ModelSelect2(url='speciality-autocomplete'),
        }

    class Media:
        js = [
            "admin/js/vendor/jquery/jquery.js",
            "autocomplete_light/jquery.init.js",
            "vendor/select2/dist/js/select2.full.js",
            "admin/js/vendor/select2/select2.full.js",
        ]


class CustomContactForm(ContactForm):

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists() or EmailAddress.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "Ce mail existe dèja"
            )
        return email

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.pk:  # Case of insert
            nom = cleaned_data.get("nom")
            prenom = cleaned_data.get("prenom")
            if Contact.objects.filter(nom__iexact=nom, prenom__iexact=prenom).exists():
                raise forms.ValidationError(
                    _("Ce contact existe dèja")
                )

    class Meta:
        model = Contact
        fields = (
            "nom", "prenom", "date_naissance", "sexe", "fixe", "mobile", "email", "specialite", "fonction", "organisme",
            "pays", "ville", "commune", "adresse", "pageweb", "facebook", "twitter", "linkedin", "instagram", "source",
            "motif",
            "carte", "commentaire"
        )
        widgets = {
            'specialite': autocomplete.ModelSelect2(url='speciality-autocomplete'),
            'date_naissance': DateInput(attrs={'type': 'date'}),
            'date_ouverture': DateInput(attrs={'type': 'date'}),
            'date_debut_exercice': DateInput(attrs={'type': 'date'}),
        }
        labels = {
            "carte": _("Carte professionnelle")
        }
        required = [
            "nom", "prenom", "email", "mobile"
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.Meta.required:
            self.fields[field].required = True


class FactureForm(forms.ModelForm):
    class Meta:
        model = Facture
        fields = "__all__"
        widgets = {
            "medecin": autocomplete.ModelSelect2(url='medecin-autocomplete', ),
            "partenaire": autocomplete.ModelSelect2(url='partner-autocomplete', ),
            "commercial": autocomplete.ModelSelect2(url='user-autocomplete', )
        }


class MedecinForm(forms.ModelForm):
    class Meta:
        model = Medecin
        fields = ('__all__')
        widgets = {
            'contact': autocomplete.ModelSelect2(url='contact-autocomplete'),
            'user': autocomplete.ModelSelect2(url='user-autocomplete'),
            'carte': autocomplete.ModelSelect2(url='carte-autocomplete'),
        }

    class Media:
        js = [
            "admin/js/vendor/jquery/jquery.js",
            "autocomplete_light/jquery.init.js",
            "vendor/select2/dist/js/select2.full.js",
            "admin/js/vendor/select2/select2.full.js",
        ]


class ProfForm(forms.ModelForm):
    class Meta:
        model = ProfessionnelSante
        fields = "__all__"
        widgets = {
            'contact': autocomplete.ModelSelect2(url='contact-autocomplete'),
            'user': autocomplete.ModelSelect2(url='user-autocomplete'),
            'carte': autocomplete.ModelSelect2(url='carte-autocomplete'),
        }

    class Media:
        js = [
            "admin/js/vendor/jquery/jquery.js",
            "autocomplete_light/jquery.init.js",
            "vendor/select2/dist/js/select2.full.js",
            "admin/js/vendor/select2/select2.full.js",
        ]


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ('__all__')
        widgets = {
            'user': autocomplete.ModelSelect2(url='user-autocomplete'),
            'pays': autocomplete.ModelSelect2(url='country-autocomplete'),
            'ville': autocomplete.ModelSelect2(url='city-autocomplete', forward=[forward.Field('pays', 'country')]),
            'wilaya': autocomplete.ModelSelect2(url='region-autocomplete', forward=[forward.Field('pays', 'country')]),
        }

    class Media:
        js = [
            "admin/js/vendor/jquery/jquery.js",
            "autocomplete_light/jquery.init.js",
            "vendor/select2/dist/js/select2.full.js",
            "admin/js/vendor/select2/select2.full.js",
        ]


class UserCreationFormExtended(UserCreationForm):
    email = forms.EmailField(required=True)
    group = forms.ModelChoiceField(label=_("group"), queryset=Group.objects.all(), required=True)
    first_name = forms.CharField(label=_('first name'), max_length=30, required=True)
    last_name = forms.CharField(label=_('last name'), max_length=150, required=True)

    class Meta:
        model = User
        fields = ("email", "password1", "password2", "first_name", "last_name", "group")

    def save(self, commit=True):
        user = super(UserCreationFormExtended, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["email"]
        user.save()
        user.groups.clear()
        if self.cleaned_data["group"].name == Role.DATA_ENTRY_PERSON.value:
            user.is_staff = True
        user.groups.add(self.cleaned_data["group"])
        email = EmailAddress()
        email.user = user
        email.verified = True
        email.email = user.email
        email.primary = True
        email.save()
        return user


class CarteProfessionnelleForm(forms.ModelForm):
    PROFILES = (
        ('', '-----------', None),
        ('1', "Médecin", Role.DOCTOR),
        ('2', "Pharmacien", Role.PHARMACIST),
        ('3', "ch.dentiste", Role.DENTIST),
        ('4', "etudiant", Role.STUDENT),
        ('5', "administration", Role.ADMINISTRATION),
        ('6', "ministère", Role.MINISTRY),
        ('7', "responsable achat medical", Role.MEDICAL_PURCHASING_MANAGER),
        ('8', "psychologue", Role.PSYCHOLOGIST),
        ('9', "auxiliare", Role.AUXILIARY),
        ('10', "paramédical", Role.PARAMEDICAL),
        ('11', "biologiste", Role.BIOLOGISTE),
        ('12', "chercheur", Role.RESEARCHER),
        ('13', "enseignant", Role.TEACHER),
        ('14', "chef entreprise médical", Role.MEDICAL_COMPANY_MANAGER),
        ('15', "comm/marketing", Role.COMM_MARKETING),
    )

    profile = forms.ChoiceField(choices=((t[0], t[1]) for t in PROFILES))
    fonction = forms.CharField(required=False)
    organisme = forms.CharField(required=False)

    class Meta:
        model = CarteProfessionnelle
        fields = ("profile", "image", "fonction", "organisme", "checked",)

    def clean_checked(self):
        checked = self.cleaned_data['checked']
        if not checked:
            raise forms.ValidationError('Ce champ est obligatoire')
        return checked

    def __init__(self, *args, **kwargs):
        super(CarteProfessionnelleForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance:
            if instance.medecin_set.all():
                self.fields['profile'].initial = self.PROFILES[1][0]
                self.fields['fonction'].initial = instance.medecin_set.first().contact.fonction
                self.fields['organisme'].initial = instance.medecin_set.first().contact.organisme
            elif instance.professionnelsante_set.all():
                self.fields['fonction'].initial = instance.professionnelsante_set.first().contact.fonction
                self.fields['organisme'].initial = instance.professionnelsante_set.first().contact.organisme
                user = instance.professionnelsante_set.first().user

                for t in self.PROFILES:
                    if t[2]:
                        if user.groups.filter(Q(name=t[2].value)).exists():
                            self.fields['profile'].initial = t[0]

            if instance.pk and instance.checked:
                self.fields['profile'].widget.attrs['disabled'] = True

    def save(self, commit=True):
        carte = super(CarteProfessionnelleForm, self).save(commit=False)
        profile = self.cleaned_data['profile']
        fonction = self.cleaned_data['fonction']
        organisme = self.cleaned_data['organisme']
        doctor = None
        professional = None

        if carte.medecin_set.all():
            doctor = carte.medecin_set.first()
        elif carte.professionnelsante_set.all():
            professional = carte.professionnelsante_set.first()

        pfl = None
        for t in self.PROFILES:
            if t[0] == profile:
                pfl = t
                break

        if profile == self.PROFILES[1][0]:
            with transaction.atomic():
                if professional:
                    doctor = Medecin()
                    doctor.user = professional.user
                    doctor.contact = professional.contact
                    doctor.contact.fonction = fonction
                    doctor.contact.organisme = organisme
                    doctor.carte = professional.carte
                    doctor.contact.save()
                    doctor.save()

                    professional.user = None
                    professional.contact = None
                    professional.carte = None
                    professional.save()
                    professional.delete()
                if doctor:
                    doctor.user.groups.set([Group.objects.get(name=pfl[2].value)])
                    doctor.user.save()
                    if doctor.has_no_offer():
                        freemium_offers = OffrePrepaye.objects.filter(prix=0, date_expiration__gt=timezone.now())
                        if freemium_offers.exists():
                            createCommand(freemium_offers.first(), doctor)


        elif profile:
            with transaction.atomic():
                if doctor:
                    professional = ProfessionnelSante()
                    professional.user = doctor.user
                    professional.contact = doctor.contact
                    professional.contact.fonction = fonction
                    professional.contact.organisme = organisme
                    professional.carte = doctor.carte
                    professional.contact.save()
                    professional.save()

                    doctor.user = None
                    doctor.contact = None
                    doctor.carte = None
                    doctor.save()
                    doctor.delete()
                if professional:
                    professional.user.groups.set([Group.objects.get(name=pfl[2].value)])
                    professional.user.save()
        carte.save()
        return carte


class EquipeSoinsForm(forms.ModelForm):
    class Meta:
        model = EquipeSoins
        fields = "__all__"
        widgets = {
            "patient": autocomplete.ModelSelect2(url='patient-autocomplete', ),
            "professionnel": autocomplete.ModelSelect2(url='user-autocomplete', )
        }

    class Media:
        js = [
            "admin/js/vendor/jquery/jquery.js",
            "autocomplete_light/jquery.init.js",
            "vendor/select2/dist/js/select2.full.js",
            "admin/js/vendor/select2/select2.full.js",
        ]


class TrackingPixelForm(forms.ModelForm):
    class Meta:
        model = TrackingPixel
        fields = '__all__'


# ===============================================================================
# Custom Model Admin
# ===============================================================================
class ModuleAdmin(ImportExportModelAdmin):
    resource_class = ModuleResource
    list_display = ('libelle', 'get_tags')
    exclude = ('slug',)
    search_fields = ['libelle', 'tags__name']

    def get_tags(self, obj):
        return ", ".join([tag.name for tag in obj.tags.all()])

    get_tags.short_description = _("Mots clés")


class TagAdmin(ImportExportModelAdmin):
    list_display = ('name', 'slug')
    exclude = ('slug',)


class OffrePrepayeAdmin(ImportExportModelAdmin):
    list_display = ('id', 'libelle', 'date_debut', 'date_expiration', 'prix', "status")

    def status(self, obj):
        if obj.status:
            return obj.status.value
        return ""


class SpecialitesAdmin(ImportExportModelAdmin):
    list_display = ('id', 'libelle', "libelle_ar", 'point')
    list_editable = ('libelle', 'libelle_ar')
    search_fields = ("libelle", "libelle_ar", "point")


class BankAdmin(ImportExportModelAdmin):
    list_display = ('code', 'name', 'bic')


class QualificationAdmin(ImportExportModelAdmin):
    list_display = ('id', 'libelle',)
    search_fields = ('libelle',)


class DciAdmin(ImportExportModelAdmin):
    list_display = ('id', 'unique_id', 'designation_fr')
    search_fields = ['id', 'unique_id', 'designation_fr']


class StandAdmin(admin.ModelAdmin):
    list_display = ('id', 'partner', 'slogan', 'signaletique')
    ordering = ("slogan",)


class CarteProfessionnelleAdmin(admin.ModelAdmin):
    change_form_template = "admin/change_carte_professionnelle.html"
    form = CarteProfessionnelleForm

    list_display = (
        'id', 'name', 'profile', 'telephone', 'image_thumbnail', 'date_creation', 'checked', 'date_validation')
    search_fields = ('medecin__contact__nom', 'medecin__contact__prenom')
    image_thumbnail = AdminThumbnail(image_field='image')
    ordering = ('-id',)
    list_per_page = 5

    def __init__(self, model, admin_site):
        self.request = None
        super().__init__(model, admin_site)

    def has_add_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        self.request = request
        if obj and obj.checked == True:
            return self.readonly_fields + ('checked',)
        return self.readonly_fields

    def name(self, obj):
        if obj.medecin_set.first():
            user = obj.medecin_set.first().user
            return "{} {}".format(user.first_name, user.last_name)
        elif obj.professionnelsante_set.first():
            user = obj.professionnelsante_set.first().user
            return "{} {}".format(user.first_name, user.last_name)
        elif obj.professionnelsante_set.first():
            user = obj.professionnelsante_set.first().user
            return "{} {}".format(user.first_name, user.last_name)
        return ""

    def profile(self, obj):
        if obj.medecin_set.first():
            return _("Médecin")
        elif obj.professionnelsante_set.first():
            user = obj.professionnelsante_set.first().user
            return ",".join(group.name for group in user.groups.all())
        return ""

    def telephone(self, obj):
        medecin = obj.medecin_set.first()
        professionnelsante = obj.professionnelsante_set.first()
        if medecin:
            return "{} / {}".format(medecin.contact.mobile, medecin.contact.fixe)
        elif professionnelsante:
            return "{} / {}".format(professionnelsante.contact.mobile, professionnelsante.contact.fixe)
        return ""

    def get_queryset(self, request):
        qs = super(CarteProfessionnelleAdmin, self).get_queryset(request)
        return qs.exclude(Q(medecin=None, professionnelsante=None))

    @staticmethod
    @staff_member_required
    def changeCardView(request, pk):
        try:
            obj = CarteProfessionnelle.objects.get(pk=pk)
            if not obj.rejected:
                medecin = obj.medecin_set.first()
                professionnelsante = obj.professionnelsante_set.first()
                if medecin:
                    email = medecin.user.email
                    user = medecin.user
                if professionnelsante:
                    email = professionnelsante.user.email
                    user = professionnelsante.user
                if email:
                    url = "https://{}/{}".format(Site.objects.get_current().domain,
                                                 "doctor/cp/upload/")
                    mail.send(
                        email,
                        settings.DEFAULT_FROM_EMAIL,
                        template='demande_renvoyer_carte_professionnelle',
                        context={
                            'nom': user.first_name,
                            'prenom': user.last_name,
                            'url': url
                        },
                    )
                    obj.rejected = True
                    obj.save()
                    messages.success(request, "The email was sent to %s" % user.get_full_name())
                else:
                    message = "Doctor has not an email address in our system"
                    messages.warning(request, message)
            else:
                messages.warning(request, "The email was already sent")
        except CarteProfessionnelle.DoesNotExist:
            messages.warning(request, "The item does not exist")

        return redirect(reverse("admin:core_carteprofessionnelle_change", args=[pk]))

    name.short_description = _('Nom & Prénom')
    telephone.short_description = _('Mobile/Fixe')
    image_thumbnail.short_description = _("Image")


class CertificatAdmin(admin.ModelAdmin):
    list_display = ('id', 'contact', 'date_creation', 'verifie')
    search_fields = (
        'contact_agrement_certificat__nom',
        'contact_agrement_certificat__prenom',
        'contact_qualifications_certificats__nom',
        'contact_qualifications_certificats__prenom',
        'contact_specialite_certificat__nom',
        'contact_specialite_certificat__prenom'
    )
    ordering = ('-id',)
    list_per_page = 10

    def __init__(self, model, admin_site):
        self.request = None
        super().__init__(model, admin_site)

    def get_readonly_fields(self, request, obj=None):
        self.request = request
        if obj and obj.verifie == True:
            return self.readonly_fields + ('verifie',)
        return self.readonly_fields

    def contact(self, obj):
        contact = None
        if obj.contact_agrement_certificat.first():
            contact = obj.contact_agrement_certificat.first()
        if obj.contact_qualifications_certificats.first():
            contact = obj.contact_qualifications_certificats.first()
        if obj.contact_specialite_certificat.first():
            contact = obj.contact_specialite_certificat.first()
        if contact:
            return "{} {}".format(contact.nom, contact.prenom)
        return ""

    def get_queryset(self, request):
        qs = super(CertificatAdmin, self).get_queryset(request)
        return qs.exclude(
            Q(contact_agrement_certificat=None) & Q(contact_qualifications_certificats=None) & Q(
                contact_specialite_certificat=None)
        )


class AvatarAdmin(admin.ModelAdmin):
    image_thumbnail = AdminThumbnail(image_field='image')
    list_display = ('id', 'user', 'image_thumbnail', 'date_creation', 'date_maj')


class ArticleImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'article', 'image_thumbnail', 'date_creation')
    image_thumbnail = AdminThumbnail(image_field='image')


class ProfessionnelSanteAdmin(admin.ModelAdmin):
    form = ProfForm
    list_display = ('id', 'user_link', 'contact_link', 'carte', 'date_creation')

    def contact_link(self, obj):
        link = reverse("admin:core_contact_change", args=[obj.contact.id])
        return mark_safe('<a href="%s">%s</a>' % (link, escape(obj.contact.__str__())))

    def user_link(self, obj):
        link = reverse("admin:auth_user_change", args=[obj.user.id])
        return mark_safe('<a href="%s">%s</a>' % (link, escape(obj.user.get_full_name())))

    contact_link.short_description = "Contact"
    contact_link.admin_order_field = "contact"

    user_link.short_description = "User"
    user_link.admin_order_field = "user"


class ContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom', 'prenom', 'cree_par', 'date_creation')
    search_fields = ['nom', 'prenom']

    def get_list_display(self, request):
        if request.user.groups.filter(name=Role.DATA_ENTRY_PERSON.value).exists():
            return self.list_display + ("get_demande_commercial_status", "get_account_creation_status")
        return self.list_display

    def get_list_filter(self, request):
        if request.user.groups.filter(name=Role.DATA_ENTRY_PERSON.value).exists():
            return self.list_filter
        return self.list_filter + ("cree_par",)

    def get_form(self, request, obj=None, change=False, **kwargs):
        if request.user.groups.filter(name=Role.DATA_ENTRY_PERSON.value).exists():
            return CustomContactForm
        else:
            return ContactForm

    def get_demande_commercial_status(self, obj):
        if Action.objects.filter(contact=obj, type=Action.CHOICES[4][0]).exists():
            return mark_safe('<img src="/static/admin/img/icon-yes.svg" alt="True">')
        else:
            return mark_safe('<img src="/static/admin/img/icon-no.svg" alt="False">')

    def get_account_creation_status(self, obj):
        if not has_no_role(obj):
            return mark_safe('<img src="/static/admin/img/icon-yes.svg" alt="True">')
        else:
            return mark_safe('<img src="/static/admin/img/icon-no.svg" alt="False">')

    get_demande_commercial_status.short_description = 'Demande commerciale créée ?'
    get_account_creation_status.short_description = 'Compte créée ?'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.cree_par = request.user.operateur
        super(ContactAdmin, self).save_model(request, obj, form, change)


def open_commercial_request(modeladmin, request, queryset):
    date_debut = (timezone.now() + timedelta(days=1)).date()
    date_fin = (timezone.now() + timedelta(days=8)).date()
    type = Action.CHOICES[4][0]
    attribuee_a = Group.objects.get(name=Role.COMMERCIAL.value)
    nbr = 0
    nbs = 0
    for contact in queryset:
        ats = Action.objects.filter(Q(contact=contact, date_debut__range=[date_debut, date_fin])
                                    | Q(contact=contact, date_fin__range=[date_debut, date_fin])
                                    | Q(contact=contact, date_debut__lte=date_debut, date_fin__gte=date_fin))
        if ats.filter(type=Action.CHOICES[4][0]).exists():
            nbr += 1
        else:
            action = Action()
            action.date_fin = date_fin
            action.date_debut = date_debut
            action.type = type
            action.contact = contact
            action.attribuee_a = attribuee_a
            action.cree_par = request.user.operateur

            action.save()
            nbs += 1

    messages.info(request, "%s demandes commerciales créées, %s demandes commerciales existent déjà" % (nbs, nbr))


def open_account(modeladmin, request, queryset):
    # create user
    nbr = 0
    nbs = 0
    for contact in queryset:
        with transaction.atomic():
            if has_no_role(contact):
                print("has_no_role")
                user = User()

                user.first_name = contact.nom
                user.last_name = contact.prenom
                password = User.objects.make_random_password()
                contact.mdp_genere = password
                user.set_password(password)
                user.username = contact.email
                user.email = contact.email
                user.save()
                user.groups.add(Group.objects.get(name=Role.VISITOR.value))

                email = EmailAddress()
                email.user = user
                email.primary = True
                email.verified = True
                email.email = contact.email
                email.save()

                pro = ProfessionnelSante()
                pro.user = user
                pro.contact = contact
                pro.save()

                to = [user.email]
                from_email = "eTabib <{}>".format(settings.EMAIL_HOST_USER)
                mail.send(
                    to,
                    from_email,
                    template='expo_registration',
                    context={
                        "username": contact.email,
                        "password": password,
                        "login_link": "{}://{}".format(request.scheme, request.get_host())
                    },
                )
                if verify_number(contact):
                    message = "bonjour et bienvenue sur eTabib, pour acceder au salon virtuel utiliser " \
                              "le nom d'utilisateur: {0} et le mot de pass: {1}".format(
                        contact.email, password
                    )
                    send_sms_icosnet(obj=contact, message=message, operateur=request.user.operateur)

                nbs += 1
            else:
                nbr += 1

    messages.info(request, "%s comptes créées, %s déjà créées" % (nbs, nbr))


open_commercial_request.short_description = _("Ouvrir une demande commerciale")
open_account.short_description = _("Ouvrir un compte et envoyer un sms et un mail")


class ContactImportExportAdmin(ContactAdmin, ImportExportModelAdmin):
    resource_class = ContactResource
    actions = [open_commercial_request, open_account]

    def changelist_view(self, request, extra_context=None):
        if request.user.groups.filter(name=Role.DATA_ENTRY_PERSON.value).exists():
            self.change_list_template = None
        return super(ContactImportExportAdmin, self).changelist_view(request, extra_context)

    def get_queryset(self, request):
        queryset = super(ContactImportExportAdmin, self).get_queryset(request)
        if request.user.groups.filter(name=Role.DATA_ENTRY_PERSON.value):
            return queryset.filter(cree_par__user=request.user)
        else:
            return queryset


class ClientAdmin(admin.ModelAdmin):
    form = ContactForm

    list_display = ('id', 'nom', 'prenom', 'adresse', 'specialite', "sexe",
                    'fixe', 'mobile', 'mobile_1', 'mobile_2', 'pays', 'ville', "compte_test")
    list_editable = ('nom', 'prenom', 'adresse', 'specialite', "sexe",
                     'fixe', 'mobile', 'mobile_1', 'mobile_2', 'pays', 'ville', "compte_test")
    list_per_page = 10
    autocomplete_fields = ["specialite", "pays", "ville"]

    class Meta:
        model = Client

    def get_queryset(self, request):
        return Contact.objects.filter(medecin__isnull=False).exclude(medecin__postes__isnull=True).order_by("id")

    def has_view_or_change_permission(self, request, obj=None):
        return request.user.has_perm("core.can_view_client_list")

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("core.can_view_client_list")

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("core.can_view_client_list")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("core.can_view_client_list")


class RoleListFilter(admin.SimpleListFilter):
    title = _('Profile')
    parameter_name = 'profile'

    def lookups(self, request, model_admin):
        return (
            (Role.DOCTOR.value, Role.DOCTOR.value),
            (Role.PATIENT.value, Role.PATIENT.value),
            ("visiteur", "Visiteur"),
            ("pas_de_profile", "Pas de profile"),
        )

    def queryset(self, request, queryset):
        if self.value() == 'visiteur':
            return queryset.filter(groups__name__in=[
                Role.VISITOR.value,
            ])

        if self.value() == Role.DOCTOR.value:
            return queryset.filter(groups__name__in=[
                Role.DOCTOR.value
            ])

        if self.value() == Role.PATIENT.value:
            return queryset.filter(groups__name__in=[
                Role.PATIENT.value
            ])
        if self.value() == "pas_de_profile":
            return queryset.filter(groups=None)


class RegistredUserAdmin(ImportExportModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'email', 'date_joined', 'get_telephone', "get_groups")
    search_fields = ('id', 'first_name', 'last_name', 'email', 'patient__telephone',
                     "medecin__contact__mobile", "medecin__contact__mobile_1", "medecin__contact__mobile_2", "medecin__contact__fixe")
    list_filter = (
        ('date_joined', DateRangeFilter),
        RoleListFilter
    )
    list_display_links = None
    list_per_page = 50
    resource_class = RegistredUserResource

    class Meta:
        model = RegistredUser

    def get_groups(self, obj):
        return " | ".join(group.name for group in obj.groups.all())

    def get_telephone(self, obj):
        if hasattr(obj, "patient"):
            return obj.patient.telephone
        if hasattr(obj, "medecin"):
            tels = []
            if obj.medecin.contact.mobile:
                tels.append(obj.medecin.contact.mobile)
            if obj.medecin.contact.mobile_1:
                tels.append(obj.medecin.contact.mobile_1)
            if obj.medecin.contact.mobile_2:
                tels.append(obj.medecin.contact.mobile_2)
            if obj.medecin.contact.fixe:
                tels.append(obj.medecin.contact.fixe)
            return " | ".join(tel for tel in tels)

    def get_queryset(self, request):
        queryset = super(RegistredUserAdmin, self).get_queryset(request)
        return queryset.filter(
            Q(groups__name__in=[Role.DOCTOR.value, Role.PATIENT.value, Role.VISITOR.value]) | Q(groups=None)
        )

    get_groups.admin_order_field = 'groups'
    get_groups.short_description = _('Profile')
    get_telephone.short_description = _('Téléphone')

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_import_permission(self, request):
        return False


class MedecinImportExportAdmin(ImportExportModelAdmin):
    change_list_template = "admin/doctor_change_list.html"
    form = MedecinForm
    resource_class = MedecinResource
    list_display = ('id', 'user', 'contact_link')
    search_fields = ['user__username', 'contact__nom', 'contact__prenom']

    def contact_link(self, obj):
        link = reverse("admin:core_contact_change", args=[obj.contact.id])
        return mark_safe('<a href="%s">%s</a>' % (link, escape(obj.contact.__str__())))


class VersionImportExportAdmin(ImportExportModelAdmin):
    resource_class = VersionResource
    list_display = ('id', 'module', 'number', "lastversion", 'zipfile')


class UpdaterImportExportAdmin(ImportExportModelAdmin):
    list_display = ('id', 'version', "last_version", 'zipfile')


class InterventionAdmin(admin.ModelAdmin):
    list_display = ('attribue_a', 'detail_action', 'probleme')

    def attribue_a(self, obj):
        return obj.detail_action.action.attribuee_a

    attribue_a.admin_order_field = 'detail_action__action__attribuee_a'
    attribue_a.short_description = 'Operateur'


class LicenseStatusListFilter(admin.SimpleListFilter):
    title = _('License status')
    parameter_name = 'decade'

    def lookups(self, request, model_admin):
        return (
            ('used', _('Used')),
            ('unused', _('Unused')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'used':
            return queryset.exclude(fol_licensce_set__isnull=True, offre_perso_licence_set__isnull=True)
        if self.value() == 'unused':
            return queryset.filter(fol_licensce_set__isnull=True, offre_perso_licence_set__isnull=True)


class LicenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'clef', 'date_actiavtion_licence', 'date_creation', 'partenaire')
    ordering = ['id']
    search_fields = ['clef']
    list_filter = [LicenseStatusListFilter]


class Facture_OffrePrep_LicenceAdmin(admin.ModelAdmin):
    change_list_template = "admin/offre_change_list.html"

    list_display = ('id', 'contact_link', 'licence', 'offre_link', 'facture_link', 'date_creation', 'date_expiration')
    ordering = ['-date_creation']
    search_fields = ['facture__medecin__contact__nom', 'facture__medecin__contact__prenom', 'offre__libelle',
                     'licence__clef']

    def contact_link(self, obj):
        link = reverse("admin:core_contact_change", args=[obj.facture.medecin.contact.id])
        return mark_safe('<a href="%s">%s</a>' % (link, escape(obj.facture.medecin.contact.__str__())))

    contact_link.admin_order_field = 'facture__medecin__contact'
    contact_link.short_description = _('Contact')

    def offre_link(self, obj):
        link = reverse("admin:core_offreprepaye_change", args=[obj.offre.id])
        return mark_safe('<a href="%s">%s</a>' % (link, escape(obj.offre.__str__())))

    offre_link.short_description = _('Offre')
    offre_link.admin_order_field = 'offre'

    def facture_link(self, obj):
        link = reverse("admin:core_facture_change", args=[obj.facture.id])
        return mark_safe('<a href="%s">%s</a>' % (link, escape(obj.facture.__str__())))

    facture_link.short_description = _('Facture')
    facture_link.admin_order_field = 'facture'


class Facture_Offre_Partenaire_Admin(admin.ModelAdmin):
    list_display = ('id', 'partner_link', 'offre_link', 'facture_link', 'date_creation')
    ordering = ['-date_creation']
    search_fields = ['facture__partenaire__contact__nom', 'facture__partenaire__contact__prenom', 'offre__libelle']

    def partner_link(self, obj):
        link = reverse("admin:core_partenaire_change", args=[obj.facture.partenaire.id])
        return mark_safe('<a href="%s">%s</a>' % (link, escape(obj.facture.partenaire.__str__())))

    partner_link.admin_order_field = 'facture__partenaire'
    partner_link.short_description = _('Partenaire')

    def offre_link(self, obj):
        link = reverse("admin:core_offrepartenaire_change", args=[obj.offre.id])
        return mark_safe('<a href="%s">%s</a>' % (link, escape(obj.offre.__str__())))

    offre_link.short_description = _('Offre')
    offre_link.admin_order_field = 'offre'

    def facture_link(self, obj):
        link = reverse("admin:core_facture_change", args=[obj.facture.id])
        return mark_safe('<a href="%s">%s</a>' % (link, escape(obj.facture.__str__())))

    facture_link.short_description = _('Facture')
    facture_link.admin_order_field = 'facture'


class OffrePersonnaliseAdmin(admin.ModelAdmin):
    list_display = ('id', 'contact', 'services_set', 'avantages_set', 'facture', 'date_creation', 'date_mise_a_jour')
    ordering = ['-date_creation']

    # search_fields = ['facture__contact__nom', 'facture__contact__prenom', 'offre__libelle', 'facture__numero',
    #                  'licence__clef']

    def avantages_set(self, obj):
        return ", ".join([p.libelle for p in obj.avantages.all()])

    avantages_set.short_description = _('Avantages')

    def services_set(self, obj):
        services = obj.services
        if services:
            return ", ".join([str(p) for p in obj.services.all()])

    services_set.short_description = _('Services')

    def facture(self, obj):
        if obj.facture_pers_set.count() > 0:
            link = reverse("admin:core_facture_change", args=[obj.facture_pers_set.all()[0].id])
            return mark_safe('<a href="%s">%s</a>' % (link, escape(obj.facture_pers_set.all()[0].__str__())))
        else:
            return ""

    def contact(self, obj):
        if obj.facture_pers_set.count() > 0:
            link = reverse("admin:core_contact_change", args=[obj.facture_pers_set.all()[0].contact.id])
            return mark_safe('<a href="%s">%s</a>' % (link, escape(obj.facture_pers_set.all()[0].contact.__str__())))
        else:
            return ""


class PosteAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'libelle', 'username', 'medecin_link', 'blocked', 'mac', 'old_mac', 'etabibappliction', 'licence_link',
        "date_creation")
    search_fields = ['medecin__user__username', 'libelle', 'mac', 'old_mac', 'medecin__contact__nom',
                     'medecin__contact__prenom', 'licence__clef']

    def username(self, obj):
        if obj.medecin:
            if obj.medecin.user:
                return obj.medecin.user.username

    def medecin_link(self, obj):
        if obj.medecin:
            link = reverse("admin:core_medecin_change", args=[obj.medecin.id])
            return mark_safe('<a href="%s">%s</a>' % (link, escape(obj.medecin.__str__())))
        else:
            return ""

    medecin_link.short_description = _('Médecin')
    medecin_link.admin_order_field = 'medecin'

    def licence_link(self, obj):
        if obj.licence:
            link = reverse("admin:core_licence_change", args=[obj.licence.id])
            return mark_safe('<a href="%s">%s</a>' % (link, escape(obj.licence.__str__())))
        else:
            return ""

    licence_link.short_description = _('Licence')
    licence_link.admin_order_field = 'licence'


class EtabibAdmin(admin.ModelAdmin):
    list_display = ('id', 'version', 'lastversion', 'zipfile')
    search_fields = ['id', 'version']


class EtabibImportExportAdmin(EtabibAdmin, ImportExportModelAdmin):
    resource_class = EtabibResource


class BddScriptAdmin(admin.ModelAdmin):
    list_display = ('id', 'version', 'last_version', 'date_creation')
    ordering = ['-date_creation']


class PointsHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'medecin', 'poste', 'partenaire', 'points', 'description', 'date_creation')
    ordering = ['-date_creation']


class FactureAdmin(admin.ModelAdmin):
    form = FactureForm
    list_display = ('id', 'medecin', 'partenaire', 'total', 'tva', 'total_prix', 'coupon', 'date_creation')
    search_fields = ("id", "medecin__contact__nom", "medecin__contact__prenom", "partenaire__contact__nom",
                     "partenaire__contact__prenom")
    ordering = ['-date_creation']


class CampagneImpressionAdmin(admin.ModelAdmin):
    change_list_template = "admin/campagne_imp_change_list.html"
    list_display = (
        "libelle", "partenaire", "get_reseaux_display", "get_annonces", "date_debut", "date_fin", "verifie", "status",
        "is_deleted", "deleted_at")
    actions = ['make_verified']

    zones = forms.ModelMultipleChoiceField(
        label=_('Ville'),
        queryset=City.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(
            url='city-autocomplete',
        ),
    )

    def status(self, obj):
        return safe(renderCampagneStatus(obj))

    def get_annonces(self, obj):
        out = ""
        for annonce in obj.annonces.all():
            if isinstance(annonce, AnnonceFeed):
                out += "<li>Titre: %s, corps: %s</li>" % (annonce.titre, annonce.corps)
            if isinstance(annonce, AnnonceDisplay):
                imgs = ""
                for item in annonce.images.all():
                    if item.image:
                        imgs += '<a class="image-link" data-lightbox="roadtrip" href="{0}">' \
                                '<img src="{0}"/></a>'.format(item.image.url)
                out += "<li>%s</li>" % imgs if imgs else ""
            if isinstance(annonce, AnnonceVideo):
                out += '<li><video width="100%" height="100%" controls>' \
                       '<source src="' + annonce.video.url + '" type="video/ogg">' \
                                                             'Your browser does not support the video tag.' \
                                                             '</video></li>'
        return mark_safe(out)

    def make_verified(self, request, queryset):
        queryset.update(verifie=True)

    def make_non_verified(self, request, queryset):
        queryset.update(verifie=False)

    make_verified.short_description = "Mark selected campaigns as verified"
    make_non_verified.short_description = "Mark selected campaigns as non verified"

    class Meta:
        model = CampagneImpression
        fields = ('__all__')

    get_annonces.short_description = _('Annonces')

    class Media:
        js = [
            "admin/js/vendor/jquery/jquery.js",
            "autocomplete_light/jquery.init.js",
            "vendor/select2/dist/js/select2.full.js",
            "admin/js/vendor/select2/select2.full.js",
        ]


class PartenaireAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_firstname', 'get_lastname', 'raisonsocial', 'verifie')
    search_fields = ('user__first_name', "user__last_name", "raisonsocial", "id")
    list_filter = ("verifie",)
    ordering = ['-date_creation']

    def get_firstname(self, obj):
        return obj.user.first_name

    def get_lastname(self, obj):
        return obj.user.last_name

    get_firstname.admin_order_field = 'user'
    get_firstname.short_description = _('Nom')

    get_lastname.admin_order_field = 'user'
    get_lastname.short_description = _('Prénom')


class EmailAddressAdmin(ImportExportModelAdmin):
    list_display = ('id', 'user', 'email', 'verified')
    search_fields = ['user__username', 'email']


class AnnonceFeedBackAdmin(ImportExportModelAdmin):
    list_display = ('id', 'user', 'annonce', 'feedback')
    search_fields = ['user__username', 'feedback']


class EulaAdmin(admin.ModelAdmin):
    list_display = ('id', 'version', 'date_creation')
    ordering = ['-date_creation']


class DemandeInterventionAdmin(admin.ModelAdmin):
    list_display = ('medecin', 'poste', 'en_rapport_avec', 'description', 'capture_link')

    def medecin(self, obj):
        return obj.poste.medecin

    def capture_link(self, obj):
        if obj.capture:
            link = reverse("admin:core_demandeinterventionimage_change", args=[obj.capture.id])
            return mark_safe('<a href="%s">%s</a>' % (link, escape(obj.capture.__str__())))
        return ""


class IbnHamzaFeedAdmin(admin.ModelAdmin):
    list_display = ('id', 'libelle', 'description', 'date_expiration')


class PatientAdmin(admin.ModelAdmin):
    form = PatientForm
    list_display = ('id', 'user', 'mail', 'nom', 'prenom', 'pays')
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']

    def mail(self, obj):
        if obj.user:
            return obj.user.email
        return ""


class InstallationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'medecin', 'poste_link', 'module', 'version', 'date_creation', 'a_installer', 'a_desinstaller')

    def module(self, obj):
        link = reverse("admin:core_module_change", args=[obj.version.module.id])
        return mark_safe('<a href="%s">%s</a>' % (link, escape(obj.version.module.__str__())))

    def poste_link(self, obj):
        link = reverse("admin:core_poste_change", args=[obj.poste.id])
        return mark_safe('<a href="%s">%s</a>' % (link, escape(obj.poste.__str__())))

    def medecin(self, obj):
        link = reverse("admin:core_medecin_change", args=[obj.poste.medecin.id])
        return mark_safe('<a href="%s">%s</a>' % (link, escape(obj.poste.medecin.__str__())))


class UserCustomAdmin(UserAdmin, ImportExportModelAdmin):
    resource_class = UserResource
    ordering = ['-pk']


UserCustomAdmin.add_form = UserCreationFormExtended
UserCustomAdmin.add_fieldsets = (
    (None, {
        'classes': ('wide',),
        'fields': ('email', 'password1', 'password2', 'last_name', 'first_name', 'group')
    }),
)


class GradeAdmin(ImportExportModelAdmin):
    resource_class = GradeResource
    list_display = ('id', 'libelle',)
    search_fields = ("libelle",)


class ProspectAdmin(ImportExportModelAdmin):
    list_display = ('id', 'contact', 'cree_par')
    search_fields = ("contact__nom", "contact__prenom")


class ListeProspectAdmin(admin.ModelAdmin):
    list_display = ('id', 'cree_par', "date_creation", "commune", "specialite")
    search_fields = ("cree_par__user__first_name", "cree_par__user__last_name")


class SuiviAdmin(ImportExportModelAdmin):
    list_display = ('id', 'contact', 'cree_par')
    search_fields = ("contact__nom", "contact__prenom")


class EquipeSoinsAdmin(ImportExportModelAdmin):
    form = EquipeSoinsForm
    list_display = ('id', 'patient', 'get_professionnel', 'confirme')
    search_fields = (
        "patient__user__first_name", "patient__user__last_name",
        "professionnel__first_name", "professionnel__last_name", "professionnel__username"
    )

    def get_professionnel(self, obj):
        return "{0}, {1} {2}".format(
            obj.professionnel.username,
            obj.professionnel.first_name,
            obj.professionnel.last_name
        )

    get_professionnel.short_description = _("Professionnel(le) de santé")


class CategorieProduitAdmin(TranslatedFieldAdmin, admin.ModelAdmin):
    pass


class PageViewUserFilter(SimpleListFilter):
    title = 'Operator'
    parameter_name = 'operator_id'

    def lookups(self, request, model_admin):
        ops = Operateur.objects.filter(user__groups__name=Role.DATA_ENTRY_PERSON.value)
        return [(op.id, op.full_name) for op in ops]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                Q(visitor__user__medecin__contact__cree_par__id=self.value()) |
                Q(visitor__user__professionnelsante__contact__cree_par__id=self.value())
            )
        return queryset


class PageviewAdmin(admin.ModelAdmin):
    date_hierarchy = 'view_time'
    list_filter = (PageViewUserFilter,)

    list_display = ('url', 'get_user', 'get_creator', 'view_time')
    search_fields = (
        "visitor__user__first_name", "visitor__user__last_name", "url",
        "visitor__user__medecin__contact__cree_par__user__first_name",
        "visitor__user__medecin__contact__cree_par__user__last_name",
    )

    def get_user(self, obj):
        return "{0} ({1} {2})".format(
            obj.visitor.user,
            obj.visitor.user.first_name,
            obj.visitor.user.last_name
        )

    def get_creator(self, obj):
        operator = ""
        if hasattr(obj.visitor.user, 'medecin'):
            operator = obj.visitor.user.medecin.contact.cree_par
        elif hasattr(obj.visitor.user, 'professionnelsante'):
            operator = obj.visitor.user.professionnelsante.contact.cree_par
        return operator.full_name if operator else " "

    get_creator.short_description = _("Opérator")
    get_user.short_description = _("User")


class VisitorAdmin(admin.ModelAdmin):
    date_hierarchy = 'start_time'

    list_display = ('session_key', 'user', 'start_time', 'session_over',
                    'pretty_time_on_site', 'ip_address', 'user_agent')
    search_fields = (
        "user__first_name", "user__last_name", "ip_address",
    )

    def session_over(self, obj):
        return obj.session_ended() or obj.session_expired()

    session_over.boolean = True

    def pretty_time_on_site(self, obj):
        if obj.time_on_site is not None:
            return timedelta(seconds=obj.time_on_site)

    pretty_time_on_site.short_description = 'Time on site'


class ArticleAdmin(admin.ModelAdmin):
    list_display = ('id', 'libelle', 'date_creation', 'partenaire', "is_deleted", "deleted_at")


class VirementAdmin(admin.ModelAdmin):
    list_display = ('id', 'contact', 'montant', "date_maj", 'date_creation', 'methode_paiement', "verifie")
    search_fields = ("facture__medecin__contact__nom", "facture__medecin__contact__prenom")
    autocomplete_fields = ["facture", "ajouter_par"]

    def contact(self, obj):
        if obj.facture and obj.facture.medecin:
            return obj.facture.medecin.contact.full_name
        return ""


class AnnonceImpressionLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'campagne', 'annonce', 'date_impression', "user", "get_reseau_display", "cout")
    list_filter = ("reseau", "date_impression")
    autocomplete_fields = ("user",)

    def get_reseau_display(self, obj):
        if obj.reseau:
            for choice in CampagneImpression.CHOICES:
                if choice[0] == int(obj.reseau):
                    return choice[1]
        return ""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    get_reseau_display.short_description = "Réseau"
    get_reseau_display.admin_order_field = "reseau"


class AnnonceClickLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'campagne', 'annonce', 'date_click', "user", "get_reseau_display", "cout")
    list_filter = ("reseau", "date_click")
    autocomplete_fields = ("user",)

    def get_reseau_display(self, obj):
        if obj.reseau:
            for choice in CampagneImpression.CHOICES:
                if choice[0] == int(obj.reseau):
                    return choice[1]
        return ""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    get_reseau_display.short_description = "Réseau"
    get_reseau_display.admin_order_field = "reseau"


class AnnonceAdmin(admin.ModelAdmin):
    list_display = ('id', 'libelle', 'date_creation', 'partenaire', "is_deleted", "deleted_at")


class ComptePreCreeAdmin(ImportExportModelAdmin):
    list_display = ('id', 'username', 'password', 'get_status')
    search_fields = ("username", "password")

    def get_status(self, obj):
        if User.objects.filter(username=obj.username).exists():
            return mark_safe('<img src="/static/admin/img/icon-no.svg" alt="True">')
        else:
            return mark_safe('<img src="/static/admin/img/icon-yes.svg" alt="False">')

    get_status.short_description = _("Available?")


class CustomGroupAdmin(GroupAdmin):
    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == 'permissions':
            qs = kwargs.get('queryset', db_field.remote_field.model.objects)
            qs = qs.filter(content_type__model="rightssupport")
            # Avoid a major performance hit resolving permission names which
            # triggers a content_type load:
            kwargs['queryset'] = qs.select_related('content_type')
        return super(GroupAdmin, self).formfield_for_manytomany(
            db_field, request=request, **kwargs)


class TrackingPixelAdmin(ImportExportModelAdmin):
    list_display = ('id', 'user_agent', 'ip_address', 'type', 'label', "source", "create_at")
    ordering = ("-id",)
    search_fields = ("user_agent", "ip_address", "type", "label")
    list_filter = ("type", "label")


class TrackingPixelInline(GenericTabularInline):
    ct_field = "source_type"
    ct_fk_field = "source_id"
    model = TrackingPixel
    form = TrackingPixelForm
    readonly_fields = ('create_at',)
    can_delete = False
    extra = 0
    can_delete = False


class CustomEmailAdmin(EmailAdmin):
    class Media:
        css = {
            'all': ('css/font-awesome.min.css',)
        }

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Override change_view to catch DNS resolution errors in development"""
        import socket
        try:
            return super(CustomEmailAdmin, self).change_view(request, object_id, form_url, extra_context)
        except socket.gaierror as e:
            # Catch DNS resolution errors (e.g., when email server hostname can't be resolved)
            # This can happen in development when the SMTP server is not accessible
            messages.warning(request, 
                f"Warning: Could not connect to email server ({e}). "
                "Email preview may not be fully functional in development mode.")
            # Return the view anyway, just without the connection-dependent features
            return super(EmailAdmin, self).change_view(request, object_id, form_url, extra_context)

    def get_inlines(self, request, obj):
        inlines = super(CustomEmailAdmin, self).get_inlines(request, obj)
        if TrackingPixelInline not in inlines:
            inlines.append(TrackingPixelInline)
        return inlines

    def get_list_display(self, request):
        list_display = super(CustomEmailAdmin, self).get_list_display(request)
        if "opened" not in list_display:
            list_display.append("opened")
        return list_display

    def opened(self, obj):
        if "ptrack" in obj.html_message:
            if TrackingPixel.objects.filter(source_type__model="email", source_id=obj.id).exists():
                return mark_safe('<img src="/static/admin/img/icon-yes.svg" alt="True">')
            return mark_safe('<img src="/static/admin/img/icon-no.svg" alt="False">')
        return mark_safe('<i class="fa fa-question-circle" aria-hidden="true"></i>')


# ===============================================================================
# Register
# ===============================================================================
admin.site.register(Contact, ContactImportExportAdmin)
admin.site.register(Client, ClientAdmin)
admin.site.register(RegistredUser, RegistredUserAdmin)
admin.site.register(Medecin, MedecinImportExportAdmin)
admin.site.register(Annonce, AnnonceAdmin)
admin.site.register(AnnonceImage)
admin.site.register(UserAgreement)
admin.site.register(PrecommandeArticle)
admin.site.register(Poste, PosteAdmin)
admin.site.register(Operateur, OperateurAdmin)
admin.site.register(Specialite, SpecialitesAdmin)
admin.site.register(Bank, BankAdmin)
admin.site.register(Qualification, QualificationAdmin)
admin.site.register(Etabib, EtabibImportExportAdmin)
admin.site.register(BddScript, BddScriptAdmin)
admin.site.register(Installation, InstallationAdmin)
admin.site.register(ArticleImage, ArticleImageAdmin)
admin.site.register(Article, ArticleAdmin)
admin.site.register(Intervention, InterventionAdmin)
admin.site.register(Licence, LicenceAdmin)
admin.site.register(Medic, ArticleAdmin)
admin.site.register(AutreProduit, ArticleAdmin)
# admin.site.register(Campagne)
admin.site.register(CampagneStatistique)
admin.site.register(CampagneImpression, CampagneImpressionAdmin)
admin.site.register(AnnonceClickLog, AnnonceClickLogAdmin)
admin.site.register(AnnonceImpressionLog, AnnonceImpressionLogAdmin)
admin.site.register(Catalogue)
admin.site.register(Stand, StandAdmin)
admin.site.register(PinBoard)
admin.site.register(CarteProfessionnelle, CarteProfessionnelleAdmin)
admin.site.register(Module, ModuleAdmin)
admin.site.unregister(Tag)
admin.site.register(Tag, TagAdmin)
admin.site.register(Partenaire, PartenaireAdmin)
admin.site.register(Probleme)
admin.site.register(Produit, ArticleAdmin)
admin.site.register(CategorieProduit, CategorieProduitAdmin)
admin.site.register(Updater, UpdaterImportExportAdmin)
admin.site.register(Version, VersionImportExportAdmin)
admin.site.register(Virement, VirementAdmin)
admin.site.register(Commentaire)
admin.site.register(OffrePrepaye, OffrePrepayeAdmin)
admin.site.register(OffrePartenaire)
admin.site.register(Facture_Offre_Partenaire, Facture_Offre_Partenaire_Admin)
admin.site.register(Facture, FactureAdmin)
admin.site.register(FactureCompany)
admin.site.register(FactureCompanyDetail)
admin.site.register(ServiceFedilite)
admin.site.register(Service)
admin.site.register(Facture_OffrePrep_Licence, Facture_OffrePrep_LicenceAdmin)
# admin.site.register(OffrePersonnalise_Service)
# admin.site.register(OffrePersonnalise, OffrePersonnaliseAdmin)
admin.site.register(Action)
admin.site.register(Eula, EulaAdmin)
admin.site.register(DetailAction)
admin.site.register(DemandeIntervention, DemandeInterventionAdmin)
admin.site.register(DemandeInterventionImage)
admin.site.register(PointsHistory, PointsHistoryAdmin)
admin.site.register(IbnHamzaFeed, IbnHamzaFeedAdmin)
admin.site.register(Patient, PatientAdmin)
admin.site.register(Avatar, AvatarAdmin)
admin.site.register(Documentation)
admin.site.register(Certificat, CertificatAdmin)
admin.site.unregister(User)
admin.site.unregister(EmailAddress)
admin.site.register(User, UserCustomAdmin)
admin.site.register(EmailAddress, EmailAddressAdmin)
admin.site.unregister(Group)
admin.site.register(Group, CustomGroupAdmin)
admin.site.register(AnnonceFeedBack, AnnonceFeedBackAdmin)
admin.site.register(Grade, GradeAdmin)
admin.site.register(Video)
admin.site.register(ProfessionnelSante, ProfessionnelSanteAdmin)
admin.site.register(Tache)
admin.site.register(Prospect, ProspectAdmin)
admin.site.register(ListeProspect, ListeProspectAdmin)
admin.site.register(Suivi, SuiviAdmin)
admin.site.register(ProchaineRencontre)
admin.site.register(Imagemodule)
admin.site.register(EquipeSoins, EquipeSoinsAdmin)
admin.site.unregister(Pageview)
admin.site.unregister(Visitor)
admin.site.register(Pageview, PageviewAdmin)
admin.site.register(Visitor, VisitorAdmin)
admin.site.register(ComptePreCree, ComptePreCreeAdmin)
admin.site.register(TrackingPixel, TrackingPixelAdmin)
admin.site.unregister(Email)
admin.site.register(Email, CustomEmailAdmin)
admin.site.register(Dicom_Patient)
admin.site.register(CarteID)

admin.site.site_header = 'eTabib Store Administration'
admin.site.site_title = 'eTabib Store Administration'
