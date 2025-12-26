# -*- coding: utf-8 -*-
import datetime

from allauth.account.models import EmailAddress
from bootstrap_datepicker_plus import DatePickerInput, TimePickerInput
from bootstrap_datepicker_plus import DateTimePickerInput
from cities_light.models import City, Country
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Div, Field, Row
from dal import autocomplete
from dal import forward
from django import forms
from django.contrib.auth.models import Group, User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q
from django.forms import ModelForm, formset_factory, NumberInput
from django.template.defaultfilters import filesizeformat
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from durationwidget.widgets import TimeDurationWidget

from core.enums import Role
from core.forms.forms import VersionedMediaJS
from core.models import Action, DetailAction, DetailActionFile, Contact, Operateur, PinBoard, \
    DetailActionAudioFile, ProchaineRencontre, ClotureAction, Prospect, CarteProfessionnelle, \
    Suivi, Specialite, ListeProspect
from core.models import Intervention, Screenshot, Medecin, OffrePrepaye, Facture, Service, \
    ServiceFedilite, OffrePersonnalise, OffrePersonnalise_Service, Facture_OffrePrep_Licence, Poste, \
    Probleme, Tache, OffrePartenaire, Facture_Offre_Partenaire, Virement, \
    FactureCompany
from core.templatetags.event_tags import is_formation
from core.templatetags.offer_tags import is_including_etabib_workspace
from core.utils import getAvailableLicenses, generate_username, generate_random_email
from core.widgets import AudioFileWidget
from core.widgets import CustomAutoCompleteWidgetSingle
from crm.models import CommandeImage, Ville
from dropzone.forms import DropzoneInput


class ContactForm(forms.ModelForm):
    pays = forms.ModelChoiceField(
        required=False,
        label=_('Pays'),
        queryset=Country.objects.all(),
        widget=CustomAutoCompleteWidgetSingle(
            url='country-autocomplete',
            attrs={

                'data-placeholder': _('Choisir un pays ...'),
                'class': "form-control",
                'data-theme': 'bootstrap'
            }
        ),
    )
    ville = forms.ModelChoiceField(
        required=False,
        label=_('Ville'),
        queryset=City.objects.all(),
        widget=CustomAutoCompleteWidgetSingle(
            url='city-autocomplete',
            forward=[forward.Field('pays', 'country')],
            attrs={
                'data-placeholder': _('Choisir une ville ...'),
                'class': "form-control",
                'data-theme': 'bootstrap'
            }
        ),
    )

    class Meta:
        model = Contact
        exclude = ['cree_par']
        labels = {
            'source': _("Origine")
        }
        widgets = {
            'date_naissance': DatePickerInput(options={"locale": "fr"}),
            'date_ouverture': DatePickerInput(options={"locale": "fr"}),
            'date_debut_exercice': DatePickerInput(options={"locale": "fr"}),
            'specialite': CustomAutoCompleteWidgetSingle(
                url='speciality-autocomplete',
            ),
        }
        required = (
            'nom',
            'prenom',
            'ville',
            'pays',
            'sexe',
            'mobile',
            'source',
            'specialite'
        )

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.pk:  # Case of insert
            nom = cleaned_data.get("nom")
            prenom = cleaned_data.get("prenom")
            if Contact.objects.filter(nom__iexact=nom, prenom__iexact=prenom).exists():
                raise forms.ValidationError(
                    _("Ce contact existe dèja")
                )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        enable_required_fields = True
        if self.instance:
            if hasattr(self.instance, "partenaire"):
                enable_required_fields = False
        if enable_required_fields:
            for field in self.Meta.required:
                self.fields[field].required = True
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.add_input(Submit('submit', _('Submit'), css_class='btn-etabib'))
        self.helper.form_method = 'POST'
        self.helper.layout = Layout(
            Div(
                Div('nom', css_class='col-lg-6 col-md-6'),
                Div('prenom', css_class='col-lg-6 col-md-6'),
                css_class='row'
            ),
            Div(
                Div('date_naissance', css_class='col-lg-6 col-md-6'),
                Div('sexe', css_class='col-lg-6 col-md-6'),
                css_class='row'
            ),
            Div(
                Div('pays', css_class='col-lg-6 col-md-6'),
                Div('ville', css_class='col-lg-6 col-md-6'),
                css_class='row'
            ),
            Div(
                Div('adresse', css_class='col-lg-6 col-md-6'),
                Div('departement', css_class='col-lg-6 col-md-6'),
                css_class='row'
            ),
            Div(
                Div('fixe', css_class='col-lg-6 col-md-6'),
                Div('mobile', css_class='col-lg-6 col-md-6'),
                css_class='row'
            ),
            Div(
                Div('source', css_class='col-lg-6 col-md-6'),
                Div('motif', css_class='col-lg-6 col-md-6'),
                css_class='row'
            ),
            Div(
                Div('fonction', css_class='col-lg-3 col-md-3'),
                Div('organisme', css_class='col-lg-3 col-md-3'),
                Div('specialite', css_class='col-lg-6 col-md-6'),
                css_class='row'
            ),
            Div(
                Div('type_structure', css_class='col-lg-3 col-md-3'),
                Div('date_ouverture', css_class='col-lg-3 col-md-3'),
                Div('date_debut_exercice', css_class='col-lg-3 col-md-3'),
                Div('type_exercice', css_class='col-lg-3 col-md-3'),
                css_class='row'
            ),
            Div(
                Div('email', css_class='col-lg-6 col-md-6'),
                Div('codepostal', css_class='col-lg-2 col-md-3'),
                css_class='row'
            ),
            Div(
                Div('carte', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div('pageweb', css_class='col-lg-6 col-md-6'),
                Div('facebook', css_class='col-lg-6 col-md-6'),
                css_class='row'
            ),
            Div(
                Div('linkedin', css_class='col-lg-6 col-md-6'),
                Div('instagram', css_class='col-lg-6 col-md-6'),
                css_class='row'
            ),
            Div(
                Div('commentaire', css_class='col-lg-12'),
                css_class='row'
            ),
        )

    def save(self, commit=True):
        contact = super(ContactForm, self).save(commit)
        return contact


class SimpleContactForm(ContactForm):
    class Meta:
        model = Contact
        fields = ['nom', 'prenom', 'sexe', 'pays', 'ville', 'mobile', 'specialite', 'commentaire']
        widgets = {
            'specialite': CustomAutoCompleteWidgetSingle(
                url='speciality-autocomplete',
            ),
        }
        required = ['nom', 'prenom', 'sexe', 'pays', 'ville', 'mobile', 'specialite']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        enable_required_fields = True
        if self.instance:
            if hasattr(self.instance, "partenaire"):
                enable_required_fields = False
        if enable_required_fields:
            for field in self.Meta.required:
                self.fields[field].required = True
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.add_input(Submit('submit', _('Submit'), css_class='btn-etabib'))
        self.helper.form_method = 'POST'
        self.helper.layout = Layout(
            Div(
                Div('nom', css_class='col-md-4'),
                Div('prenom', css_class='col-md-4'),
                Div('sexe', css_class='col-md-4'),
                css_class='row'
            ),
            Div(
                Div('specialite', css_class='col-md-6'),
                Div('mobile', css_class='col-md-4'),
                css_class='row'
            ),
            Div(
                Div('pays', css_class='col-lg-6 col-md-6'),
                Div('ville', css_class='col-lg-6 col-md-6'),
                css_class='row'
            ),
            Div(
                Div('commentaire', css_class='col-lg-12'),
                css_class='row'
            ),
        )


class InterventionForm(forms.ModelForm):
    screen = forms.CharField(
        required=False,
        label=_("Capture d'écran"),
        widget=DropzoneInput(
            maxFilesize=10,
            acceptedFiles="image/*",
            paramName='image',
            placeholder=_("cliquer pour uploader une image"),
            maxFiles=1,
            upload_path='/screenshot-upload/'
        ),
    )

    def getScreen(self):
        return self.cleaned_data['screen']

    class Media:
        js = (VersionedMediaJS('js/dropzonee/dropzone.django.js', '2.2'), "js/dropzonee/jquery.cookie.js",)

    def __init__(self, *args, **kwargs):
        super(InterventionForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = False
        for field in self.Meta.required:
            self.fields[field].required = True

    class Meta:
        model = Intervention
        exclude = ['screenshots', 'detail_action']
        labels = {
            "duree_reelle": _("Durée d'intervention")
        }
        widgets = {
            'debut_execution': DateTimePickerInput(
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                    # "minDate": str(timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
                }
            ),
            'duree_reelle': TimeDurationWidget(show_days=False, show_seconds=False)
        }

        required = (
            'debut_execution',
            'duree_reelle'
        )


class ScreenShotUploadForm(forms.Form):
    image = forms.ImageField()

    def clean_image(self):
        content = self.cleaned_data['image']
        if content.size > 10 * 1024 * 1024:
            raise forms.ValidationError(_('Please keep filesize under %s. Current filesize %s') % (
                filesizeformat(10 * 1024 * 1024), filesizeformat(content.size)))
        return self.cleaned_data['image']

    def save(self):
        cp = Screenshot()
        cp.image = self.cleaned_data['image']
        cp.save()
        return cp


class OrderForm(forms.Form):
    contact = forms.ModelChoiceField(
        required=True,
        label=_('Contact'),
        queryset=Contact.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='contact-autocomplete',
            attrs={
                'data-placeholder': _('Séléctionnez un contact ...'),
                'class': "form-control",
                'data-theme': 'bootstrap'
            }
        ),
    )
    offre = forms.ModelChoiceField(
        required=True,
        label=_('Offre'),
        queryset=OffrePrepaye.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='offre-prepaye-autocomplete',
            attrs={
                'data-placeholder': _('Séléctionnez une Offre ...'),
                'class': "form-control",
                'data-theme': 'bootstrap'
            }
        ),
    )
    quantite = forms.IntegerField(label=_('Quantité'), required=True,
                                  validators=[MinValueValidator(1), MaxValueValidator(5)])
    reduction_categorie = forms.ChoiceField(label=_('Catégorie de Réduction'), choices=Facture.REDUCTION_CATEGORIE,
                                            required=False)
    reduction_type = forms.ChoiceField(label=_('Type de Réduction'), choices=Facture.REDUCTION_TYPE, required=False)
    reduction = forms.IntegerField(label=_('Réduction'), required=False, initial=0)
    negocie_ttc = forms.BooleanField(label="Négocié en TTC", initial=False, widget=forms.CheckboxInput(),
                                     required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.action = kwargs.pop('action', None)
        self.instance = kwargs.pop('instance', None)
        self.update = False
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_tag = False
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-3'
        self.helper.field_class = 'col-lg-9'
        self.helper.layout = Layout(
            Field("contact", css_class="mg-ub-10"),
            Field("offre", css_class="mg-ub-10"),
            Field("quantite", css_class="mg-ub-10"),
            Field("reduction_categorie", css_class="mg-ub-10"),
            Field("reduction_type", css_class="mg-ub-10"),
            Field("reduction", css_class="mg-ub-10"),
            Field("negocie_ttc", css_class="mg-ub-10"),
        )
        super(OrderForm, self).__init__(*args, **kwargs)
        if self.action:
            self.fields["contact"].initial = self.action.contact
            self.fields['contact'].required = False
            self.fields['contact'].widget.attrs['disabled'] = 'disabled'

        if self.instance and self.instance.id:
            self.fields["contact"].initial = self.instance.medecin.contact
            self.fields['contact'].required = False
            self.fields['contact'].widget.attrs['disabled'] = 'disabled'

            self.fields["offre"].initial = self.instance.offre_prepa
            if self.instance.fol_facture_set:
                self.fields["quantite"].initial = self.instance.fol_facture_set.count()
            else:
                self.fields["quantite"].initial = 0

            self.update = True

    def calculateTotal(self):
        quantite = self.cleaned_data['quantite']
        offre = self.cleaned_data['offre']
        total_ht = int(quantite) * offre.prix
        # calculate total
        return total_ht

    def clean(self):
        offre = self.cleaned_data['offre']
        reduction_type = self.cleaned_data['reduction_type']
        reduction = self.cleaned_data['reduction']
        negocie_ttc = self.cleaned_data['negocie_ttc']

        if self.action:
            contact = self.action.contact
            if not contact.specialite:
                raise forms.ValidationError(_("Veuillez ajouter la spécialité du contact %s") % contact)
            if not contact.carte_pessionnelle:
                raise forms.ValidationError(
                    _("Veuillez uploader une carte de professionnel pour le contact %s") % contact)
        self.including_etabib_workspace = False
        if is_including_etabib_workspace(offre):
            self.including_etabib_workspace = True
            quantite = self.cleaned_data['quantite']
            if getAvailableLicenses(quantite).count() != quantite:
                raise forms.ValidationError(_("Erreur 500"))

        if reduction_type == Facture.REDUCTION_TYPE[1][0]:
            if not (0 <= reduction <= 100):
                raise forms.ValidationError(_("La réduction doit être entre 0 et 100"))
        elif reduction_type == Facture.REDUCTION_TYPE[0][0] and reduction != 0:
            raise forms.ValidationError(_("Veuillez séléctionner un type de réduction."))

    def save(self, commit=True):
        if self.action:
            contact = self.action.contact
        else:
            contact = self.cleaned_data['contact']
        offre = self.cleaned_data['offre']
        quantite = self.cleaned_data['quantite']
        reduction_categorie = self.cleaned_data['reduction_categorie']
        reduction_type = self.cleaned_data['reduction_type']
        reduction = self.cleaned_data['reduction']
        negocie_ttc = self.cleaned_data['negocie_ttc']
        reduction_offre_status = offre.reduction_status(contact)

        if not self.update:
            facture = Facture()
            facture.commercial = self.user
            password = None
            if hasattr(contact, "medecin"):
                medecin = contact.medecin
            elif hasattr(contact, "professionnelsante"):
                medecin = Medecin()
                medecin.user = contact.professionnelsante.user
                medecin.contact = contact
                medecin.carte = contact.professionnelsante.carte
                medecin.user.groups.set([Group.objects.get(name=Role.DOCTOR.value)])

                contact.professionnelsante.user = None
                contact.professionnelsante.carte = None

                cp = CarteProfessionnelle()
                cp.image = contact.carte
                cp.checked = True
                cp.save()

                medecin.carte = cp

                medecin.save()
                contact.professionnelsante.delete()
            else:
                # create user
                user = User()

                group = Group.objects.get(name=Role.DOCTOR.value)

                user.first_name = contact.nom
                user.last_name = contact.prenom
                password = User.objects.make_random_password()
                contact.mdp_genere = password
                user.set_password(password)
                user.username = generate_username(slugify(user.first_name, allow_unicode=True),
                                                  slugify(user.last_name, allow_unicode=True))
                user.save()
                user.groups.add(group)

                mail = EmailAddress()
                mail.user = user
                mail.primary = True
                mail.verified = True
                if contact.email:
                    mail.email = contact.email
                else:
                    mail.email = generate_random_email()
                mail.save()

                contact.save()

                # Create doctor
                medecin = Medecin()
                medecin.user = user
                medecin.contact = contact
                # medecin carte
                cp = CarteProfessionnelle()
                cp.image = contact.carte
                cp.checked = True
                cp.save()

                medecin.carte = cp

                medecin.save()

            # if the offer has a reduction ignore all previous reductions
            if reduction_offre_status["has_reduction"]:
                reduction = (offre.prix - offre.prix_reduit) * quantite
                reduction_type = Facture.REDUCTION_TYPE[2][0]

            facture.medecin = medecin
            facture.reduction_type = reduction_type
            facture.reduction = reduction
            facture.reduction_categorie = reduction_categorie
            facture.total = self.calculateTotal()
            facture.negocie_ttc = negocie_ttc

            detail = DetailAction()
            detail.action = self.action
            detail.description = _("Commande pour une offre prépayée")
            detail.cree_par = self.user.operateur
            detail.save()

            facture.detail_action = detail

            if commit:
                facture.save()

            licences = None
            if self.including_etabib_workspace:
                # Get list of available licences
                licences = getAvailableLicenses(quantite)
            for i in range(quantite):
                fol = Facture_OffrePrep_Licence()
                fol.facture = facture
                fol.offre = offre
                if licences:
                    fol.licence = licences[i]
                if commit:
                    fol.save()

        else:
            facture = self.instance
            facture.reduction_type = reduction_type
            facture.reduction = reduction
            facture.reduction_categorie = reduction_categorie
            facture.total = self.calculateTotal()
            facture.negocie_ttc = negocie_ttc

            if self.instance.fol_facture_set:
                # delete old Facture_OffrePrep_Licence and recreate new ones
                self.instance.fol_facture_set.all().delete()

            licences = None
            if self.including_etabib_workspace:
                licences = getAvailableLicenses(quantite)
            for i in range(quantite):
                fol = Facture_OffrePrep_Licence()
                fol.facture = facture
                fol.offre = offre
                if licences:
                    fol.licence = licences[i]
                fol.save()

            if commit:
                facture.save()

        return facture


class CustomOrderForm(forms.Form):
    contact = forms.ModelChoiceField(
        required=True,
        label=_('Contact'),
        queryset=Contact.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='contact-autocomplete',
            attrs={
                'data-placeholder': _('Séléctionnez un Contact ...'),
                'class': "form-control",
                'data-theme': 'bootstrap'
            }
        ),
    )

    services = forms.ModelMultipleChoiceField(
        required=True,
        label=_('Services'),
        queryset=Service.objects.all(),
    )

    avantages = forms.ModelMultipleChoiceField(
        required=False,
        label=_('Services de fidélité'),
        queryset=ServiceFedilite.objects.all(),
    )

    quantite = forms.CharField(label=_('Quantité'), required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(CustomOrderForm, self).__init__(*args, **kwargs)

    def clean(self):
        contact = self.cleaned_data['contact']
        if contact and not contact.specialite:
            raise forms.ValidationError(_("Veuillez ajouter la spécialité du contact %s") % contact)
        if not contact.carte:
            raise forms.ValidationError(_("Veuillez uploader une carte de professionnel pour le contact %s") % contact)

        if 'quantite' in self.cleaned_data and 'services' in self.cleaned_data:
            quantite = self.cleaned_data['quantite']
            services = self.cleaned_data['services']
            need_license = 0
            if quantite:
                for tuple in self.getServicesFromQte(quantite, services):
                    if tuple["service"].creer_licence:
                        need_license += tuple["quantite"]
            else:
                raise forms.ValidationError(_("Erreur dans les données envoyées au serveur."))

    def getServicesFromQte(self, quantite, services):
        """
        return list of tuples {service,quantite}
        :param quantite:
        :param services:
        :return:
        """
        out = []
        if quantite and services:
            array = quantite.split(',')
            if len(array) % 2 == 0:
                it = iter(quantite.split(','))
                for service_id, qte in zip(it, it):
                    for service in services:
                        if service.pk == int(service_id):
                            out.append({
                                'service': service,
                                'quantite': int(qte)
                            })
        return out

    def calculateTotal(self, quantite, services):
        total = 0
        for tuple in self.getServicesFromQte(quantite, services):
            if tuple['service'] and tuple['quantite']:
                total += tuple['service'].tarif * tuple['quantite']
        return total

    def save(self, commit=True):
        quantite = self.cleaned_data['quantite']
        contact = self.cleaned_data['contact']
        services = self.cleaned_data['services']
        avantages = self.cleaned_data['avantages']

        offre = OffrePersonnalise()
        if commit:
            offre.save()
        offre.avantages.set(avantages)

        for tuple in self.getServicesFromQte(quantite, services):
            if tuple['service'].creer_licence:
                for i in range(tuple['quantite']):
                    os = OffrePersonnalise_Service()
                    os.service = tuple['service']
                    os.quantite = 1
                    os.licence = getAvailableLicenses(1)[0]
                    os.offre = offre
                    if commit:
                        os.save()
            elif tuple['service'].besoin_licence:
                os = OffrePersonnalise_Service()
                os.service = tuple['service']
                os.quantite = tuple['quantite']
                os.offre = offre
                if commit:
                    os.save()

        if hasattr(contact, "medecin"):
            medecin = contact.medecin
        else:
            # create user
            user = User()

            group = Group.objects.get(name=Role.DOCTOR.value)

            user.first_name = contact.nom
            user.last_name = contact.prenom
            password = User.objects.make_random_password()
            contact.mdp_genere = password
            user.set_password(password)
            user.username = generate_username(slugify(user.first_name, allow_unicode=True),
                                              slugify(user.last_name, allow_unicode=True))
            user.save()
            user.groups.add(group)

            mail = EmailAddress()
            mail.user = user
            mail.primary = True
            mail.verified = True
            if contact.email:
                mail.email = contact.email
            else:
                mail.email = generate_random_email()
            mail.save()

            contact.save()

            # Create doctor
            medecin = Medecin()
            medecin.user = user
            medecin.contact = contact
            # medecin carte
            cp = CarteProfessionnelle()
            cp.image = contact.carte
            cp.checked = True
            cp.save()

            medecin.carte = cp

            medecin.save()

        facture = Facture()
        facture.medecin = medecin
        facture.commercial = self.user
        facture.offre_perso = offre
        facture.total = self.calculateTotal(quantite, services)
        if commit:
            facture.save()

        return facture


class OrderPartnerForm(forms.Form):
    contact = forms.ModelChoiceField(
        required=True,
        label=_('Contact'),
        queryset=Contact.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='contact-autocomplete',
            attrs={
                'data-placeholder': _('Séléctionnez un contact ...'),
                'class': "form-control",
                'data-theme': 'bootstrap'
            }
        ),
    )
    offre = forms.ModelChoiceField(
        required=True,
        label=_('Offre'),
        queryset=OffrePartenaire.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='offre-partenaire-autocomplete',
            attrs={
                'data-placeholder': _('Séléctionnez une Offre ...'),
                'class': "form-control",
                'data-theme': 'bootstrap'
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.action = kwargs.pop('action', None)
        self.instance = kwargs.pop('instance', None)
        self.update = False
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        super(OrderPartnerForm, self).__init__(*args, **kwargs)
        if self.action:
            self.fields["contact"].initial = self.action.contact
            self.fields['contact'].required = False
            self.fields['contact'].widget.attrs['disabled'] = 'disabled'

    def clean(self):
        pass

    def save(self, commit=True):
        if self.action:
            contact = self.action.contact
        else:
            contact = self.cleaned_data['contact']
        offre = self.cleaned_data['offre']

        facture = Facture()
        facture.commercial = self.user
        partenaire = contact.partenaire
        partenaire.points = offre.points
        partenaire.save()
        facture.partenaire = partenaire
        facture.total = float(offre.prix.amount)

        detail = DetailAction()
        detail.action = self.action
        detail.description = _("Commande pour une offre partenaire")
        detail.cree_par = self.user.operateur
        detail.save()

        facture.detail_action = detail

        if commit:
            facture.save()

        fop = Facture_Offre_Partenaire()
        fop.offre = offre
        fop.facture = facture

        if commit:
            fop.save()

        return facture


class ServiceAssignForm(forms.Form):
    postes = forms.ModelMultipleChoiceField(
        required=True,
        label=_('Postes'),
        queryset=Poste.objects.all(),
    )

    os = forms.ModelMultipleChoiceField(
        required=True,
        label=_('Service'),
        queryset=OffrePersonnalise_Service.objects.all(),
    )


class ProblemForm(forms.ModelForm):
    screen = forms.CharField(
        required=False,
        label=_("Capture d'écran"),
        widget=DropzoneInput(
            maxFilesize=10,
            acceptedFiles="image/*",
            paramName='image',
            placeholder=_("cliquer pour uploader une image"),
            maxFiles=1,
            upload_path='/screenshot-upload/'
        ),
    )

    def getScreen(self):
        return self.cleaned_data['screen']

    class Media:
        js = (VersionedMediaJS('js/dropzonee/dropzone.django.js', '2.2'), "js/dropzonee/jquery.cookie.js",)

    class Meta:
        model = Probleme
        exclude = ['cree_par', 'screenshot']

    def __init__(self, *args, **kwargs):
        super(ProblemForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = False


class ProspectForm(forms.ModelForm):
    class Meta:
        model = Prospect
        exclude = ['cree_par', "urgent"]
        widgets = {'contact': forms.HiddenInput()}

    def clean(self):
        cleaned_data = super().clean()
        contact = cleaned_data.get("contact")
        if Prospect.objects.filter(contact=contact).exists():
            raise forms.ValidationError(
                _("%s est dèja dans la liste des prospects de %s") % (contact, contact.prospect.cree_par)
            )

    def __init__(self, *args, **kwargs):
        self.operateur = kwargs.pop("operateur", None)
        self.list_is_required = kwargs.pop("list_is_required", None)
        super(ProspectForm, self).__init__(*args, **kwargs)
        if self.operateur:
            self.fields['liste'].queryset = ListeProspect.objects.filter(cree_par=self.operateur)
            if self.list_is_required:
                self.fields['liste'].required = self.list_is_required


class TaskForm(forms.ModelForm):
    attribuee_a = forms.ModelChoiceField(
        label=_('Attribuée à'),
        queryset=Operateur.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='operateur-autocomplete',
            attrs={
                'data-placeholder': _('Séléctionnez un opérateur ...'),
                'class': "form-control",
                'data-theme': 'bootstrap'
            }
        ),
    )
    contact = forms.ModelChoiceField(
        required=False,
        label=_('Contact'),
        queryset=Contact.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='contact-autocomplete',
            attrs={
                'data-placeholder': _('Séléctionnez un contact ...'),
                'class': "form-control",
                'data-theme': 'bootstrap'
            }
        ),
    )

    class Meta:
        model = Tache
        exclude = ['cree_par', "termine"]
        required = [
            'message'
        ]
        widgets = {
            'message': forms.Textarea
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.Meta.required:
            self.fields[field].required = True


class CreatePisteForm(forms.Form):
    date_piste = forms.DateField(
        label=_("Choisir une date"),
        widget=DatePickerInput(
            format="%Y-%m-%d",
            options={
                "locale": "fr",
                "showClose": True,
                "showClear": True,
                "showTodayButton": True,
                "minDate": str(timezone.now().date() + datetime.timedelta(days=1))
            }
        ), )

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        # determine second_value here
        super(CreatePisteForm, self).__init__(*args, **kwargs)

    def save(self, commit=False):
        pass


class VirementForm(forms.ModelForm):
    contact = forms.ModelChoiceField(
        required=True,
        label=_('Contact'),
        queryset=Contact.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='contact-autocomplete',
            attrs={
                'data-placeholder': _('Séléctionnez un contact ...'),
                'class': "form-control",
                'data-theme': 'bootstrap'
            }
        ),
    )
    facture = forms.ModelChoiceField(
        required=True,
        label=_('Facture'),
        queryset=Facture.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='invoice-autocomplete',
            forward=['contact'],
            attrs={
                'data-placeholder': _('Séléctionnez une commande ...'),
                'class': "form-control",
                'data-theme': 'bootstrap'
            }
        ),
    )

    class Meta:
        model = Virement
        fields = ['contact', 'facture', 'montant', "methode_paiement", "image", "verifie"]


class ArchiveContactForm(ModelForm):
    class Meta:
        model = Contact
        fields = ["id"]


class InvoiceForm(forms.Form):
    first_last_name = forms.CharField(
        label=_('Client'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Nom Prénom /Nom Compagnie'),
        })
    )
    numero_commande = forms.CharField(
        required=False,
        label=_('Numéro de commande'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Numéro de commande',
        })
    )
    adresse = forms.CharField(
        label=_('Adresse'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Adresse',
        })
    )
    numero_registre_commerce = forms.CharField(
        required=False,
        label=_('NRC'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'NRC',
        })
    )
    numero_identification_fiscale = forms.CharField(
        required=False,
        label=_('NIF'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'NIF',
        })
    )
    numero_identification_domaine = forms.CharField(
        required=False,
        label=_('NIC'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'NIC',
        })
    )
    numeros_telephone = forms.CharField(
        required=False,
        label=_('Téléphone'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Téléphone',
        })
    )
    adresse_electronique = forms.CharField(
        required=False,
        label=_('Email client'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email client',
        })
    )
    numeros_fax = forms.CharField(
        required=False,
        label=_('Fax'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Fax',

        })
    )
    numero_tin = forms.CharField(
        required=False,
        label=_('TIN N°'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'TIN',
        })
    )
    numero_article = forms.CharField(
        required=False,
        label=_('Article N°'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Numéro article',
        })
    )
    statut = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'statut',
        })
    )
    mode_de_paiement = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mode de paiement',
        })
    )
    date_limite_reglement = forms.DateField(
        required=False,
        widget=NumberInput(attrs={'type': 'date'})
    )

    remises_et_rabais = forms.FloatField(
        required=False,
        label=_('REMISES ET RABAIS'),
        widget=forms.TextInput(attrs={
            'class': 'form-control input remisesrabais',
            'placeholder': 'REMISES ET RABAIS',
        })
    )
    frais_de_livraison = forms.FloatField(
        required=False,
        label=_('FRAIS DE LIVRAISON'),
        widget=forms.TextInput(attrs={
            'class': 'form-control input fraislivraison',
            'placeholder': 'FRAIS DE LIVRAISON',
        })
    )
    timbre = forms.FloatField(
        required=False,
        label=_('Timbre'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Timbre',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = False


class InvoiceItemForm(forms.Form):
    designation = forms.CharField(
        label=_('Désignation'),
        widget=forms.TextInput(attrs={
            'class': 'form-control input',
            'placeholder': 'Service/Product'
        })
    )
    quantity = forms.IntegerField(
        label='Qty',
        widget=forms.TextInput(attrs={
            'class': 'form-control input quantity',
            'placeholder': 'Quantity'
        })  # quantity should not be less than one
    )
    montant = forms.FloatField(
        label=_('Prix HT'),
        widget=forms.TextInput(attrs={
            'class': 'form-control input montant',
            'placeholder': 'Montant',
        })
    )
    tva = forms.FloatField(
        label=_('TVA'),
        widget=forms.TextInput(attrs={
            'class': 'form-control input tva',
            'placeholder': 'TVA',
        })
    )


class InvoiceFormCancel(forms.ModelForm):
    class Meta:
        model = FactureCompany
        fields = ["id"]


LineItemFormset = formset_factory(InvoiceItemForm, extra=1)


class ActionUpdateForm(forms.ModelForm):
    class Meta:
        model = Action
        fields = [
            'date_debut',
            'date_fin',
            'type']
        widgets = {
            'date_debut': DatePickerInput(
                format="%Y-%m-%d",
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                }
            ).start_of('event'),
            'date_fin': DatePickerInput(
                format="%Y-%m-%d",
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                }
            ).end_of('event')
        }


class ActionCreateForm(forms.ModelForm):
    attribuee_a = forms.ModelChoiceField(
        required=False,
        label=_('Attribuée à'),
        queryset=Operateur.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='operateur-autocomplete',
            forward=['type'],
            attrs={
                'class': "form-control",
                'data-theme': 'bootstrap'
            }
        ),
        help_text=_("Laissez vide pour l'attribuer au groupe")
    )
    contact = forms.ModelChoiceField(
        required=False,
        label=_('Contact'),
        queryset=Contact.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='contact-autocomplete',
            attrs={
                'class': "form-control",
            }
        ),
        to_field_name="pk"
    )

    class Meta:
        model = Action
        fields = [
            'type',
            'attribuee_a',
            'date_debut',
            'date_debut_time',
            'date_fin',
            'date_fin_time',
            'contact'
        ]
        widgets = {
            'date_debut': DatePickerInput(
                format="%Y-%m-%d",
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                    "minDate": str(timezone.now().date())
                }
            ).start_of('event'),
            'date_debut_time': TimePickerInput(
                options={
                    "locale": "fr",
                }
            ),
            'date_fin': DatePickerInput(
                format="%Y-%m-%d",
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                    "minDate": str(timezone.now().date())
                }
            ).end_of('event'),
            'date_fin_time': TimePickerInput(
                options={
                    "locale": "fr",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.hide_attr = kwargs.pop("hide_attr", None)
        self.hide_contact = kwargs.pop("hide_contact", None)
        self.type_action = kwargs.pop("type_action", None)
        self.contact = kwargs.pop("contact", None)
        self.type_choices = kwargs.pop("type_choices", None)
        super(ActionCreateForm, self).__init__(*args, **kwargs)
        if self.hide_attr:
            del self.fields['attribuee_a']
        if self.hide_contact:
            del self.fields['contact']
        if self.type_action:
            t = ()
            for tpl in Action.CHOICES:
                if tpl[0] == self.type_action:
                    t += (tpl,)
            self.fields["type"] = forms.ChoiceField(choices=t)
        elif self.type_choices:
            t = ()
            for tpl in Action.CHOICES:
                if tpl[0] in self.type_choices:
                    t += (tpl,)
            self.fields["type"] = forms.ChoiceField(choices=t)

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")
        type = cleaned_data.get("type")
        attribuee_a = cleaned_data.get("attribuee_a")
        if is_formation(type):
            if not attribuee_a:
                raise forms.ValidationError(
                    _("Pour le type demande de formation, le champ 'Attribuée à' est obligatoire"))

        if self.contact:
            ats = Action.objects.filter(Q(contact=self.contact, date_debut__range=[date_debut, date_fin])
                                        | Q(contact=self.contact, date_fin__range=[date_debut, date_fin])
                                        | Q(contact=self.contact, date_debut__lte=date_debut, date_fin__gte=date_fin))
            if ats.filter(type=self.type_action).exists():
                raise forms.ValidationError(
                    _("Il existe une demande de la même type avec la même intervalle de date"))


class ProlongerPisteForm(forms.ModelForm):
    class Meta:
        model = Action
        fields = [
            'date_fin',
        ]
        widgets = {
            'date_rencontre': DatePickerInput(
                format="%Y-%m-%d",
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                    "minDate": str(timezone.now().date() + datetime.timedelta(days=1))
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        # determine second_value here
        super(ProlongerPisteForm, self).__init__(*args, **kwargs)
        if self.instance:
            d = self.instance.date_fin if self.instance.date_fin >= timezone.now().date() else timezone.now().date()
            self.fields['date_fin'].widget = DatePickerInput(
                format="%Y-%m-%d",
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                    "minDate": str(d)
                })
            self.fields['date_fin'].initial = d


class DetailActionForm(forms.ModelForm):
    audio = forms.CharField(
        required=False,
        label=_("Fichier Audio"),
        widget=AudioFileWidget(url='detail-action-audio-file-upload', choices=DetailActionAudioFile.objects.all())
    )
    file = forms.CharField(
        label=_("Pièce jointe"),
        widget=DropzoneInput(
            maxFilesize=10,
            acceptedFiles="",
            paramName='file',
            placeholder=_("cliquer pour uploader un fichier"),
            maxFiles=1,
            upload_path='/detail-action-file-upload/'
        ),
        required=False
    )

    class Meta:
        model = DetailAction
        fields = [
            'type',
            'description',
            'audio',
            'file',
        ]
        required = [
            'type',
        ]

    class Media:
        js = (VersionedMediaJS('js/dropzonee/dropzone.django.js', '2.4'), "js/dropzonee/jquery.cookie.js",)

    def clean_audio(self):
        audio = self.cleaned_data['audio']
        if not audio:
            self.cleaned_data['audio'] = None
        else:
            try:
                da = DetailActionAudioFile.objects.get(pk=self.cleaned_data['audio'])
                self.cleaned_data['audio'] = da
            except DetailActionAudioFile.DoesNotExist:
                self.cleaned_data['audio'] = None
        return self.cleaned_data['audio']

    def clean(self):
        cleaned_data = super().clean()
        audio = cleaned_data.get("audio")
        description = cleaned_data.get("description")
        if not audio and not description:
            raise forms.ValidationError(_("L'un des champs: Description ou Fichier Audio est requis"))

    def __init__(self, *args, **kwargs):
        self.type_choices = kwargs.pop("type_choices", None)
        self.is_delegue = kwargs.pop("is_delegue", None)
        super(DetailActionForm, self).__init__(*args, **kwargs)
        if self.is_delegue:
            self.fields.pop('audio')
            self.fields.pop('file')
        for field in self.Meta.required:
            self.fields[field].required = True
        if self.type_choices:
            self.fields["type"] = forms.ChoiceField(choices=self.type_choices)

        self.helper = FormHelper()
        self.helper.include_media = False

    def getFile(self):
        if not self.is_delegue:
            return self.cleaned_data['file']
        return None


class DetailActionFileForm(forms.Form):
    file = forms.FileField()

    def clean_file(self):
        # TODO: validate the size of the file and the type
        return self.cleaned_data['file']

    def save(self):
        cp = DetailActionFile()
        cp.file = self.cleaned_data['file']
        cp.save()
        return cp


class DetailActionAudioFileForm(forms.Form):
    audio_file = forms.FileField()

    def clean_audio_file(self):
        # TODO: validate the size of the file and the type
        return self.cleaned_data['audio_file']

    def save(self):
        cp = DetailActionAudioFile()
        cp.file = self.cleaned_data['audio_file']
        cp.save()
        return cp


class InactivateActionForm(forms.ModelForm):
    class Meta:
        model = Action
        fields = ['active']
        widgets = {'active': forms.HiddenInput()}


class PinBoardCreateForm(forms.ModelForm):
    class Meta:
        model = PinBoard
        exclude = ['cree_par', ]


class ProchaineRencontreForm(forms.ModelForm):
    type = forms.ChoiceField(choices=DetailAction.TYPE_CHOICES_CMR)

    class Meta:
        model = ProchaineRencontre
        exclude = ['detail_action', ]
        fields = (
            'type',
            'date_rencontre',
        )
        widgets = {
            'date_rencontre': DatePickerInput(
                format="%Y-%m-%d",
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                    "minDate": str(timezone.now().date() + datetime.timedelta(days=1))
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.type_choices = kwargs.pop("type_choices", None)
        super(ProchaineRencontreForm, self).__init__(*args, **kwargs)
        if self.type_choices:
            self.fields["type"] = forms.ChoiceField(choices=self.type_choices)
            if self.initial:
                self.fields["type"].initial = self.initial['type']


class ClotureActionForm(forms.ModelForm):
    decision = forms.ChoiceField(label=_("Décision à faire"), choices=DetailAction.DECISION_CHOICES)
    decision_nb_jour = forms.IntegerField(label="",
                                          widget=forms.NumberInput(attrs={'placeholder': 'Relance dans X jour(s)'}))

    class Meta:
        model = ClotureAction
        exclude = ['detail_action']
        fields = (
            'categorisations',
            'decision',
            'decision_nb_jour',
        )

    def __init__(self, *args, **kwargs):
        self.action = kwargs.pop("action", None)
        self.is_manager = kwargs.pop("is_manager", False)
        super(ClotureActionForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get("decision")
        if self.action:
            if not self.is_manager and self.action.date_fin > timezone.now().date():
                raise forms.ValidationError(
                    _("Vous ne pouvez pas clôturer la piste."))

            dset = self.action.detail_set.filter(prochainerencontre__isnull=False)
            for d in dset:
                if d.prochainerencontre.date_rencontre > timezone.now().date():
                    raise forms.ValidationError(
                        _("Vous ne pouvez pas clôturer la piste,"
                          " car vous avez une action planifiée le %s") % d.prochainerencontre.date_rencontre)

    def treatDecision(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get("decision")
        decision_nb_jour = cleaned_data.get("decision_nb_jour")
        if decision == DetailAction.DECISION_CHOICES[0][0]:  # relancer dans
            new_action = Action()
            new_action.cree_par = self.action.cree_par
            new_action.type = self.action.type
            new_action.date_debut = timezone.now() + datetime.timedelta(days=decision_nb_jour)
            new_action.date_fin = new_action.date_debut + datetime.timedelta(days=15)
            new_action.contact = self.action.contact
            new_action.attribuee_a = self.action.attribuee_a
            new_action.save()
        elif decision == DetailAction.DECISION_CHOICES[1][0]:  # suivi ponctuel
            new_action = Action()
            new_action.cree_par = self.action.cree_par
            new_action.type = Action.CHOICES[1][0]
            new_action.date_debut = timezone.now() + datetime.timedelta(days=decision_nb_jour)
            new_action.date_fin = new_action.date_debut + datetime.timedelta(days=1)
            new_action.contact = self.action.contact
            new_action.attribuee_a = Group.objects.get(name=Role.COMMUNICATION.value)
            new_action.save()

            # after clôturer la piste supprimer le contact de la liste des prospects
            Prospect.objects.filter(contact=self.action.contact).delete()

            # add the contact to ListeSuivi
            if not Suivi.objects.filter(contact=self.action.contact).exists():
                lsuivi = Suivi()
                lsuivi.contact = self.action.contact
                lsuivi.cree_par = self.action.cree_par
                lsuivi.save()

            detail = DetailAction()
            detail.action = new_action
            detail.type = "L"
            detail.cree_par = self.action.cree_par
            detail.save()

            rencontre = ProchaineRencontre()
            rencontre.detail_action = detail
            rencontre.date_rencontre = new_action.date_debut
            rencontre.save()


class TreatProchaineRencontreForm(forms.ModelForm):
    audio = forms.CharField(
        required=False,
        label=_("Fichier Audio"),
        widget=AudioFileWidget(url='detail-action-audio-file-upload', choices=DetailActionAudioFile.objects.all())
    )

    class Meta:
        model = DetailAction
        fields = [
            'description',
            'audio',
        ]

    def clean_audio(self):
        audio = self.cleaned_data['audio']
        if not audio:
            self.cleaned_data['audio'] = None
        else:
            try:
                da = DetailActionAudioFile.objects.get(pk=self.cleaned_data['audio'])
                self.cleaned_data['audio'] = da
            except DetailActionAudioFile.DoesNotExist:
                self.cleaned_data['audio'] = None
        return self.cleaned_data['audio']

    def clean(self):
        cleaned_data = super().clean()
        audio = cleaned_data.get("audio")
        description = cleaned_data.get("description")
        if not audio and not description:
            raise forms.ValidationError(_("L'un des champs: Description ou Fichier Audio est requis"))

    def __init__(self, *args, **kwargs):
        super(TreatProchaineRencontreForm, self).__init__(*args, **kwargs)


class CommandeUploadForm(forms.Form):
    file = forms.ImageField()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(CommandeUploadForm, self).__init__(*args, **kwargs)

    def save(self):
        ci = CommandeImage()
        ci.image = self.cleaned_data['file']
        return ci


class DelegueStep1Form(forms.Form):
    email = forms.CharField(
        required=True,
        label=_('Adresse mail'),
        widget=forms.TextInput(attrs={
            'placeholder': 'Adresse mail',
        })
    )
    nom = forms.CharField(
        required=True,
        label=_('Nom'),
        widget=forms.TextInput(attrs={
            'placeholder': 'Nom',
        })
    )
    prenom = forms.CharField(
        required=True,
        label=_('Prénom'),
        widget=forms.TextInput(attrs={
            'placeholder': 'Prénom',
        })
    )
    telephone = forms.CharField(
        required=True,
        label=_('Téléphone'),
        widget=forms.TextInput(attrs={
            'placeholder': 'Numéro téléphone',
        })
    )

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = "deleguestep1form"
        self.helper.form_method = 'POST'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-3'
        self.helper.field_class = 'col-lg-9'
        self.helper.layout = Layout(
            "email",
            "nom",
            "prenom",
            "telephone",
        )
        super(DelegueStep1Form, self).__init__(*args, **kwargs)


class DelegueStep2Form(forms.Form):
    OFFER_CHOICES = (
        ('', '----'),
        ("0", _("Abonement Trimestriel")),
        ("1", _("Abonement Annuel")),
        ("2", _("Abonement 18 Mois")),
    )
    offre = forms.ChoiceField(
        required=True,
        label=_('Offre'),
        choices=OFFER_CHOICES,
        widget=forms.Select(attrs={
            'placeholder': 'Offre',
        })
    )
    quantite = forms.IntegerField(
        required=True,
        initial=1,
        label=_('Quantité'),
        widget=forms.NumberInput(attrs={
            'placeholder': 'Quantité',
        })
    )

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_id = "deleguestep2form"
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-3'
        self.helper.field_class = 'col-lg-9'
        self.helper.layout = Layout(
            "offre",
            "quantite",
        )
        super(DelegueStep2Form, self).__init__(*args, **kwargs)


class DelegueStep3Form(forms.Form):
    CHOICES = (
        ('', '----'),
        ("0", _("Espèce")),
        ("1", _("Chèque")),
        ("2", _("TPE")),
    )
    paiement = forms.ChoiceField(
        required=True,
        label=_('Méthode de paiement'),
        choices=CHOICES,
        widget=forms.Select(attrs={
            'placeholder': 'Méthode de paiement',
        })
    )
    versement_initial = forms.IntegerField(
        required=True,
        label=_('Versement initial'),
        widget=forms.NumberInput(attrs={
            'placeholder': 'Versement initial',
        })
    )

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = "deleguestep3form"
        self.helper.form_method = 'POST'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-3'
        self.helper.field_class = 'col-lg-9'
        self.helper.layout = Layout(
            "paiement",
            "versement_initial"
        )
        super(DelegueStep3Form, self).__init__(*args, **kwargs)


class ContactFilterForm(forms.Form):
    distance = forms.IntegerField(
        initial=10,
        widget=NumberInput(attrs={'placeholder': _('Tapez une distance en km')}),
        help_text=_("en Kilomètre")
    )
    commune = forms.ModelChoiceField(
        queryset=Ville.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='ville-autocomplete',
            forward=(forward.Const(1, 'pays'),),
            attrs={
                'data-placeholder': _('Choisir une commune ...'),
                'data-allow-clear': "true"
            }
        )
    )
    specialite = forms.ModelChoiceField(
        queryset=Specialite.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='speciality-autocomplete',
            attrs={
                'data-placeholder': _('Choisir une spécialité ...'),
                'data-allow-clear': "true"
            }
        )
    )

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        # self.helper.form_class = 'form-inline'
        # self.helper.field_template = 'bootstrap3/layout/inline_field.html'
        self.helper.layout = Layout(
            Field("specialite", wrapper_class="col-lg-5 col-md-5 col-sm-5"),
            Field("commune", wrapper_class="col-lg-5 col-md-5 col-sm-5"),
            Field("distance", wrapper_class="col-lg-2 col-md-2 col-sm-2"),
        )
        super(ContactFilterForm, self).__init__(*args, **kwargs)


class PlanStep1Form(forms.Form):
    specialite_q = forms.ModelChoiceField(
        label="",
        required=False,
        queryset=Specialite.objects.all(),
        help_text=_("vide = toutes les spécialités"),
        widget=autocomplete.ModelSelect2(
            url='speciality-autocomplete',
            attrs={
                'data-placeholder': _('Choisir une spécialité ...'),
                'data-allow-clear': "true"
            }
        )
    )
    max_prospect = forms.IntegerField(
        required=True,
        max_value=15,
        min_value=10,
        initial=10,
        help_text=_("Max prospects dans chanque liste min=10, max=15"),
        label="",
        widget=forms.NumberInput(attrs={
            'placeholder': _('NB max de prospect à inclure'),
        })
    )
    inclure_visiteur = forms.BooleanField(
        required=False,
        label=_("Inclure les visiteurs spontanés du site"),
    )
    inclure_profiles_unknown = forms.BooleanField(
        required=False,
        label=_("Inclure les profils de spécialité incnnu"),
    )

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = "planstep1form"
        self.helper.form_method = 'POST'
        self.helper.layout = Layout(
            Row(
                Div("specialite_q", css_class="col-md-6"),
                Div("max_prospect", css_class="col-md-6"),
            ),
            "inclure_visiteur",
            "inclure_profiles_unknown",

        )
        super(PlanStep1Form, self).__init__(*args, **kwargs)


class PlanStep2Form(forms.Form):
    commune_depart = forms.ModelChoiceField(
        required=True,
        queryset=Ville.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='ville-autocomplete',
            attrs={
                'data-placeholder': _('Commune point de départ'),
                'data-allow-clear': "true"
            }
        )
    )
    rayon = forms.IntegerField(
        required=True,
        help_text=_('Rayon (km)'),
        widget=forms.NumberInput(attrs={
            'placeholder': _('Rayon (km)'),
        })
    )

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = "planstep2form"
        self.helper.form_show_labels = False
        self.helper.form_method = 'POST'
        self.helper.layout = Layout(
            Row(
                Div("commune_depart", css_class="col-md-6"),
                Div("rayon", css_class="col-md-6"),
            ),
        )
        super(PlanStep2Form, self).__init__(*args, **kwargs)