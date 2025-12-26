# -*- coding: utf-8 -*-
import datetime

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from cities_light.models import Country, City
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field, HTML, Row, Column, Fieldset, Div
from dal import autocomplete, forward
from django import forms
from django.db import transaction
from django.forms import DateInput
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import filesizeformat
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from djmoney.forms import MoneyField
from location_field.forms.plain import PlainLocationField
from taggit.models import Tag

from ads.forms.partner_forms import CustomMoneyWidget
from basket.cart import Cart
from core.enums import WebsocketCommand
from core.forms.forms import ProfessionalIdentityForm
from core.models import Specialite, CarteProfessionnelle, Medecin, Contact, \
    Commentaire, Module, Note, Installation, ModuleStatus, Poste, OffrePrepaye, Qualification, Certificat, \
    AnnonceFeedBack, Grade, Bank
from core.utils import createCommand
from coupons.models import Coupon
from teleconsultation.models import Tdemand


class DoctorIdentityForm(ProfessionalIdentityForm):

    def __init__(self, *args, **kwargs):
        self.medecin = kwargs.pop('medecin', None)
        super(DoctorIdentityForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.add_input(Submit('submit', _("Envoyer"), css_class='btn btn-etabib'))
        self.helper.form_method = 'POST'

    def save(self):
        nom = self.cleaned_data['nom']
        prenom = self.cleaned_data['prenom']
        email = self.cleaned_data['email']
        mobile = self.cleaned_data['mobile']
        fonction = self.cleaned_data['fonction']
        organisme = self.cleaned_data['organisme']
        with transaction.atomic():
            self.medecin.contact.nom = nom
            self.medecin.contact.prenom = prenom
            self.medecin.contact.email = email
            self.medecin.contact.mobile = mobile
            self.medecin.contact.fonction = fonction
            self.medecin.contact.organisme = organisme
            self.medecin.user.first_name = nom
            self.medecin.user.last_name = prenom
            try:
                carte = CarteProfessionnelle.objects.get(pk=self.cleaned_data['card'])
            except CarteProfessionnelle.DoesNotExist:
                carte = None
            self.medecin.carte = carte

            self.medecin.user.save()
            self.medecin.contact.save()
            self.medecin.save()
        return self.medecin


class ProfessionalCardUploadForm(forms.Form):
    image = forms.ImageField(label=_("Carte professionnelle"))

    def clean_image(self):
        content = self.cleaned_data['image']
        if content.size > 10 * 1024 * 1024:
            raise forms.ValidationError(_('Please keep filesize under %s. Current filesize %s') % (
                filesizeformat(10 * 1024 * 1024), filesizeformat(content.size)))
        return self.cleaned_data['image']

    def save(self):
        cp = CarteProfessionnelle()
        cp.image = self.cleaned_data['image']
        cp.save()
        return cp


class AppCommentForm(forms.Form):
    comment = forms.CharField(widget=forms.Textarea)
    user_id = forms.IntegerField()
    app_id = forms.IntegerField()

    def save(self):
        c = Commentaire()
        c.texte = self.cleaned_data['comment']
        c.medecin = get_object_or_404(Medecin, user__id=self.cleaned_data['user_id'])
        c.module = get_object_or_404(Module, id=self.cleaned_data['app_id'])
        c.save()
        return c


class AppRatingForm(forms.Form):
    rating = forms.FloatField()
    user_id = forms.IntegerField()
    app_id = forms.IntegerField()

    def save(self):
        medecin = get_object_or_404(Medecin, user__id=self.cleaned_data['user_id'])
        module = get_object_or_404(Module, id=self.cleaned_data['app_id'])
        note = None
        try:
            note = Note.objects.get(medecin=medecin, module=module)
        except Note.DoesNotExist:
            note = Note()
            note.medecin = medecin
            note.module = module

        note.valeur = self.cleaned_data['rating']
        note.save()
        return note


class AppInstallationForm(forms.Form):
    poste_id = forms.IntegerField()
    app_id = forms.IntegerField()

    def __init__(self, *args, **kwargs):
        self.session = kwargs.pop('session', None)
        self.user = kwargs.pop('user', None)
        super(AppInstallationForm, self).__init__(*args, **kwargs)

    def clean(self):
        poste = get_object_or_404(Poste, id=self.cleaned_data['poste_id'])
        module = get_object_or_404(Module, id=self.cleaned_data['app_id'])
        status = module.etat(poste)

        # check user's points
        if status == ModuleStatus.NOT_INSTALLED:  # install
            pass
            # if not poste.has_enough_points(module):
            # raise forms.ValidationError(_("Votre crédit est insuffisant pour effectuer cette installation"))

    def save(self):
        poste = get_object_or_404(Poste, id=self.cleaned_data['poste_id'])
        module = get_object_or_404(Module, id=self.cleaned_data['app_id'])
        status = module.etat(poste)
        if status == ModuleStatus.NOT_INSTALLED:  # add to cart or remove
            from basket.templatetags.carton_tags import wasAddedToCart
            if wasAddedToCart(module, self.session, poste):
                # remove it from cart
                cart = Cart(self.session)
                cart.remove(module, poste)
            else:
                # add it to cart
                cart = Cart(self.session)
                cart.add(module, poste, price=module.consomation)

            # send notification through channels
            if cart != None:
                channel_layer = get_channel_layer()
                room_group_name = 'chat_%s' % self.user.pk
                async_to_sync(channel_layer.group_send)(
                    room_group_name,
                    {
                        'type': 'notification_message',
                        'data': {
                            'command': WebsocketCommand.FETCH_CART_COUNTS.value,
                            'count': cart.unique_count
                        }
                    }
                )

        elif status == ModuleStatus.TO_INSTALL:  # Cancel the installation
            installtion = get_object_or_404(Installation, poste=poste, version__module=module)
            installtion.delete()
        elif status == ModuleStatus.TO_UNINSTALL:  # Cancel the uninstallation
            installtion = get_object_or_404(Installation, poste=poste, version__module=module)
            installtion.a_desinstaller = False
            installtion.save()
        elif status == ModuleStatus.IS_INSTALLED:  # Uninstall
            installtion = get_object_or_404(Installation, poste=poste, version__module=module)
            installtion.a_desinstaller = True
            installtion.save()
        elif status == ModuleStatus.NO_VERSION:  # No Action
            pass
        return module.etat(poste)


class SearchForm(forms.Form):
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': _('Rechercher une application')}))
    tag = forms.ModelChoiceField(
        required=False,
        label=_('Tag'),
        queryset=Tag.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(
            url='tag-autocomplete',
        ),
    )


class ProfileForm(forms.Form):
    facebook = forms.URLField(label=_('Facebook URL'), required=False,
                              widget=forms.TextInput(attrs={'placeholder': _('Facebook URL')}))
    twitter = forms.URLField(label=_('Twitter URL'), required=False,
                             widget=forms.TextInput(attrs={'placeholder': _('Twitter URL')}))
    pageweb = forms.URLField(label=_('Site Web URL'), required=False,
                             widget=forms.TextInput(attrs={'placeholder': _('Site Web URL')}))
    infos = forms.CharField(label=_('infos'), max_length=120, required=False, widget=forms.Textarea(
        attrs={'placeholder': _('Infos')}))
    specialite = forms.ModelChoiceField(
        label=_('Spécialité'),
        queryset=Specialite.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='speciality-autocomplete',
            attrs={
                'data-placeholder': _('Choisir une spécialité ...'),
                'data-html': True,
            }
        ),
    )
    specialite_certificat_file = forms.FileField(
        required=False,
        label=" ", help_text=_("Certificat ou un document <= 2MB"),
        widget=forms.FileInput(
            attrs={
                'data-max-file-size': "2MB",
            }
        )
    )
    specialite_certificat_file_id = forms.CharField(
        widget=forms.HiddenInput,
        required=False,
    )
    qualifications = forms.ModelMultipleChoiceField(
        label=_('Qualifications'),
        queryset=Qualification.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(
            url='qualification-autocomplete',
            attrs={
                'data-placeholder': _('Choisir une qualification ...'),
            }
        ),
        required=False
    )
    agrement = forms.FileField(
        required=False,
        label="Autorisation de travail", help_text=_("Agrément ou certificat de travail <= 2MB"),
        widget=forms.FileInput(
            attrs={
                'data-max-file-size': "2MB",
            }
        )
    )
    agrement_id = forms.CharField(
        widget=forms.HiddenInput,
        required=False,
    )
    qualifications_certificat_file = forms.FileField(
        required=False,
        label=" ", help_text=_("Certificat ou un document <= 2MB"),
        widget=forms.FileInput(
            attrs={
                'multiple': 'multiple',
                'data-max-file-size': "2MB",
            })
    )
    qualifications_certificat_file_id = forms.CharField(
        widget=forms.HiddenInput,
        required=False,
    )
    rang = forms.ModelChoiceField(
        required=False,
        label=_('Grade'),
        queryset=Grade.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='grade-autocomplete',
            attrs={
                'class': "form-control",
                'data-theme': 'bootstrap'
            }
        ),
    )
    experience = forms.IntegerField(label=_("Années d'expériences"), required=False, initial=0)
    country = forms.ModelChoiceField(
        label=_('Pays'),
        queryset=Country.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='country-autocomplete',
            attrs={
                'data-placeholder': _('Choisir un pays ...'),
                'class': "form-control",
                'data-theme': 'bootstrap'
            }
        ),
    )
    city = forms.ModelChoiceField(
        label=_('Ville'),
        queryset=City.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='city-autocomplete',
            forward=['country'],
            attrs={
                'data-placeholder': _('Choisir une ville ...'),
                'class': "form-control",
                'data-theme': 'bootstrap'
            }
        ),
    )
    tarif_consultation = MoneyField(label=_("Tarif d'une consultation"), default_currency='DZD')
    ccp = forms.CharField(label=_('Numéro CCP'), required=False, max_length=10)
    cle = forms.CharField(label=_('Clé'), required=False, max_length=2)
    bank = forms.ModelChoiceField(
        label=_('Banque'),
        required=False,
        queryset=Bank.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='bank-autocomplete',
            attrs={
                'class': "form-control",
                'data-theme': 'bootstrap'
            }
        ),
    )
    bank_agence = forms.CharField(required=False, label=_("Agence"))
    bank_compte = forms.CharField(required=False, label=_("Numéro du Compte"))
    bank_rib = forms.CharField(required=False, label=_("Clé RIB"))
    gps = PlainLocationField(based_fields=['city'], zoom=5, required=False)

    def __init__(self, *args, **kwargs):
        text = _("Les reçus de votre téléconsultation seront transférés vers:")
        self.medecin = kwargs.pop('medecin', None)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        # self.helper.form_class = 'form-horizontal'
        # self.helper.label_class = 'col-lg-3'
        # self.helper.field_class = 'col-lg-9'
        self.helper.layout = Layout(
            'specialite',
            Field('specialite_certificat_file', css_class="controls specfile"),
            'specialite_certificat_file_id',
            'qualifications',
            Field('qualifications_certificat_file', css_class="controls qualfile"),
            'qualifications_certificat_file_id',
            Field('agrement', css_class="controls agrmfile"),
            'agrement_id',
            Row(
                Column('rang', css_class='col-md-6'),
                Column('experience', css_class='col-md-6'),
                css_class='row'
            ),
            Row(
                Column('country', css_class='col-md-6'),
                Column('city', css_class='col-md-6'),
                css_class='row'
            ),
            'tarif_consultation',
            HTML("<strong>" + str(text) + "</strong>"),
            Fieldset(
                "Compte CCP",
                Row(
                    Column('ccp', css_class='col-md-6'),
                    Column('cle', css_class='col-md-6'),
                    css_class='row'
                )
            ),
            Fieldset(
                "Compte bancaire",
                Row(
                    Column('bank', css_class='col-lg-4 col-md-6'),
                    Column('bank_agence', css_class='col-lg-2 col-md-6'),
                    Column('bank_compte', css_class='col-lg-4 col-md-6'),
                    Column('bank_rib', css_class='col-lg-2 col-md-6'),
                    css_class='row'
                ),
            ),
            'infos',
            'gps',
            'facebook',
            'twitter',
            'pageweb',
        )
        self.helper.add_input(Submit('submit', _("Mettre à jour"), css_class='btn btn-etabib'))
        super(ProfileForm, self).__init__(*args, **kwargs)
        amount, currency = self.fields['tarif_consultation'].fields
        amount.widget.attrs['class'] = "form-control"
        currency.widget.attrs['class'] = "form-control"
        self.fields['tarif_consultation'].widget = CustomMoneyWidget(
            amount_widget=amount.widget, currency_widget=currency.widget
        )

    def clean_bank_agence(self):
        bank_agence = self.cleaned_data['bank_agence']
        if (bank_agence):
            if len(str(bank_agence)) != 5:
                raise forms.ValidationError(u'Verifier votre numéro agence bancaire')
            return bank_agence
        return None

    def clean_bank_compte(self):
        bank_compte = self.cleaned_data['bank_compte']
        if (bank_compte):
            if len(str(bank_compte)) != 10:
                raise forms.ValidationError(u'Verifier votre numéro compte bancaire')
            return bank_compte
        return None

    def clean_bank_rib(self):
        bank_rib = self.cleaned_data['bank_rib']
        if (bank_rib):
            if len(str(bank_rib)) != 2:
                raise forms.ValidationError(u'Verifier votre numéro rib bancaire ')
            return bank_rib
        return bank_rib

    def clean(self):
        cleaned_data = super().clean()
        ccp = cleaned_data.get('ccp')
        cle = cleaned_data.get('cle')

        bank = cleaned_data.get('bank')
        bank_agence = cleaned_data.get('bank_agence')
        bank_compte = cleaned_data.get('bank_compte')
        bank_rib = cleaned_data.get('bank_rib')

        if not bank and not bank_agence and not bank_compte and not bank_rib:
            pass
        elif bank and bank_agence and bank_compte and bank_rib:
            pass
        else:
            raise forms.ValidationError(u'Verifier les informations de compte bencaire')

    def save(self):
        facebook = self.cleaned_data['facebook']
        twitter = self.cleaned_data['twitter']
        pageweb = self.cleaned_data['pageweb']
        infos = self.cleaned_data['infos']
        country = self.cleaned_data['country']
        rang = self.cleaned_data['rang']
        experience = self.cleaned_data['experience']
        city = self.cleaned_data['city']
        specialite = self.cleaned_data['specialite']
        tarif_consultation = self.cleaned_data['tarif_consultation']
        ccp = self.cleaned_data['ccp']
        cle = self.cleaned_data['cle']
        bank = self.cleaned_data['bank']
        bank_agence = self.cleaned_data['bank_agence']
        bank_compte = self.cleaned_data['bank_compte']
        bank_rib = self.cleaned_data['bank_rib']
        gps = self.cleaned_data['gps']

        self.medecin.contact.facebook = facebook
        self.medecin.contact.twitter = twitter
        self.medecin.contact.pageweb = pageweb
        self.medecin.contact.pays = country
        self.medecin.contact.experience = experience
        self.medecin.contact.rang = rang
        self.medecin.contact.ville = city
        self.medecin.contact.specialite = specialite
        self.medecin.contact.qualifications.set(self.cleaned_data['qualifications'])
        self.medecin.infos = infos
        self.medecin.tarif_consultation = tarif_consultation
        self.medecin.ccp = ccp
        self.medecin.cle = cle
        self.medecin.contact.gps = gps
        self.cleaned_data['bank'] = bank
        self.cleaned_data['bank_agence'] = bank_agence
        self.cleaned_data['bank_compte'] = bank_compte
        self.cleaned_data['bank_rib'] = bank_rib

        specialite_certificat_file_id = self.cleaned_data['specialite_certificat_file_id']
        self.medecin.contact.specialite_certificat = None
        if specialite_certificat_file_id:
            certificat = Certificat.objects.get(pk=specialite_certificat_file_id)
            self.medecin.contact.specialite_certificat = certificat

        agrement_id = self.cleaned_data['agrement_id']
        self.medecin.contact.agrement = None
        if agrement_id:
            certificat = Certificat.objects.get(pk=agrement_id)
            self.medecin.contact.agrement = certificat

        self.medecin.contact.qualifications_certificats.clear()
        qualifications_certificat_file_id = self.cleaned_data['qualifications_certificat_file_id']
        if qualifications_certificat_file_id:
            arr = qualifications_certificat_file_id.split(",")
            for item in arr:
                certificat = Certificat.objects.get(pk=item)
                self.medecin.contact.qualifications_certificats.add(certificat)

        self.medecin.contact.save()
        self.medecin.save()


class BusyForm(forms.ModelForm):
    BUSY_CHOICES = [
        ("1", _("5 minutes")),
        ("2", _("10 minutes")),
        ("3", _("30 minutes")),
        ("4", _("1 heure")),
    ]
    busy_time = forms.ChoiceField(label="", choices=BUSY_CHOICES, widget=forms.RadioSelect)

    class Meta:
        model = Tdemand
        fields = ["busy_time"]

    def getChosenTime(self):
        choice = self.cleaned_data['busy_time']
        time = None
        if choice == self.BUSY_CHOICES[0][0]:
            time = timezone.now() + datetime.timedelta(minutes=5)
        elif choice == self.BUSY_CHOICES[1][0]:
            time = timezone.now() + datetime.timedelta(minutes=10)
        elif choice == self.BUSY_CHOICES[2][0]:
            time = timezone.now() + datetime.timedelta(minutes=30)
        elif choice == self.BUSY_CHOICES[3][0]:
            time = timezone.now() + datetime.timedelta(minutes=60)
        print(time)
        return time


class CertifUploadForm(forms.Form):
    file = forms.FileField()
    t = forms.CharField(required=False)

    def clean_t(self):
        t = self.cleaned_data['t']
        if (t in "1" and self.user.medecin.contact.specialite_certificat) or (
                t in "3" and self.user.medecin.contact.agrement
        ):
            raise forms.ValidationError(_('Delete the old file before updating another one.'))
        return self.cleaned_data['t']


    def clean_file(self):
        content = self.cleaned_data['file']
        if content.size > 2 * 1024 * 1024:
            raise forms.ValidationError(_('Please keep filesize under %s. Current filesize %s') % (
                filesizeformat(2 * 1024 * 1024), filesizeformat(content.size)))
        return self.cleaned_data['file']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(CertifUploadForm, self).__init__(*args, **kwargs)


    def save(self):
        cp = Certificat()
        cp.file = self.cleaned_data['file']
        cp.save()
        return cp


class AnnonceFeedBackForm(forms.ModelForm):
    FEEDBACKS = [
        ("It's not relevant to me", _("It's not relevant to me")),
        ("I keep seeing this", _("I keep seeing this"))
    ]
    feedbacks = forms.ChoiceField(label="", choices=FEEDBACKS, widget=forms.RadioSelect)

    class Meta:
        model = AnnonceFeedBack
        fields = ["feedbacks"]

    def save(self, commit=True):
        afb = super(AnnonceFeedBackForm, self).save(commit)
        feedback = self.cleaned_data['feedbacks']
        afb.feedback = feedback
        return afb


class OfferSponsorisedOrderForm(forms.Form):
    coupon = forms.CharField(label=_("Coupon"))

    def clean_coupon(self):
        code = self.cleaned_data['coupon']
        try:
            self.coupon = Coupon.objects.get(code=code, target="1",
                                             type="sponsorship")  # target see COUPON_TARGETS settings
            if self.coupon.is_redeemed or self.coupon.expired():
                raise forms.ValidationError(_("Coupon invalide!"))
        except Coupon.DoesNotExist:
            raise forms.ValidationError(_("Coupon invalide!"))
        return code

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        super(OfferSponsorisedOrderForm, self).__init__(*args, **kwargs)

    def save(self, commit=True, user=None):
        # if coupon has a type "sponsorship" we stock the id of the offer in its value
        offre = OffrePrepaye.objects.get(id=self.coupon.value)
        return createCommand(offre, user.medecin, self.coupon)


class DemoRequestForm(forms.ModelForm):
    commentaire = forms.CharField(
        label=_("Pour quelle finalité souhaitez-vous tester notre solution ?"),
        widget=forms.Textarea(attrs={'rows': 4}),
    )

    class Meta:
        model = Contact
        fields = ["nom", "prenom", "date_naissance", "sexe", "pays", "ville", "mobile", "specialite", "rang"]
        widgets = {
            "specialite": autocomplete.ModelSelect2(
                url='speciality-autocomplete',
                attrs={
                    'data-placeholder': _('Choisir une spécialité ...'),
                    'data-html': True,
                    'data-theme': 'bootstrap'
                }
            ),
            'pays': autocomplete.ModelSelect2(
                url='country-autocomplete',
                attrs={
                    'data-placeholder': _('Choisir un pays ...'),
                    'class': "form-control",
                    'data-theme': 'bootstrap'
                }
            ),
            'ville': autocomplete.ModelSelect2(
                url='city-autocomplete',
                forward=(forward.Field('pays', 'country'),),
                attrs={
                    'data-placeholder': _('Choisir une ville ...'),
                    'class': "form-control",
                    'data-theme': 'bootstrap'
                }
            ),
            'rang': autocomplete.ModelSelect2(
                url='grade-autocomplete',
                attrs={
                    'class': "form-control",
                    'data-placeholder': _('Choisir un grade ...'),
                    'data-theme': 'bootstrap'
                }
            ),
            'date_naissance': DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(DemoRequestForm, self).__init__(*args, **kwargs)
        for field in self.Meta.fields:
            self.fields[field].required = True
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        text = _(
            "Pour pouvoir tester la plateforme et le logiciel eTabib Workspace, Veuillez Remplir Correctement Cette Demande. "
            "Vous receverez un e-mail de confirmation avec des explications sur la procédure. NB: La demande sera rejeté en cas d'informations erronées")
        self.helper.layout = Layout(
            Div(
                HTML(text),
                css_class="alert alert-info"
            ),
            Row(
                Column('nom', css_class='col-md-4'),
                Column('prenom', css_class='col-md-4'),
                Column('sexe', css_class='col-md-4'),
                css_class='row'
            ),
            Row(
                Column('date_naissance', css_class='col-md-6'),
                Column('mobile', css_class='col-md-6'),
                css_class='row'
            ),
            Row(
                Column('pays', css_class='col-md-6'),
                Column('ville', css_class='col-md-6'),
                css_class='row'
            ),
            Row(
                Column('specialite', css_class='col-md-6'),
                Column('rang', css_class='col-md-6'),
                css_class='row'
            ),
            "commentaire"
        )

    def save(self, commit=True):
        contact = super(DemoRequestForm, self).save(commit)
        return contact


class FirstLoginForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['nom', 'prenom', 'adresse', 'pays', 'ville',]

        widgets = {
            'nom': forms.TextInput(attrs={'class': "form-control", }),
            'prenom': forms.TextInput(attrs={'class': "form-control", }),
            'pays': autocomplete.ModelSelect2(
                url='country-autocomplete',
                attrs={
                    'data-placeholder': _('Choisir un pays ...'),
                    'class': "form-control",
                    'data-theme': 'bootstrap'
                }
            ),
            'ville': autocomplete.ModelSelect2(
                url='city-autocomplete',
                forward=(forward.Field('pays', 'country'),),
                attrs={
                    'data-placeholder': _('Choisir une ville ...'),
                    'class': "form-control",
                    'data-theme': 'bootstrap'
                }
            ),
            'adresse': forms.Textarea(attrs={'rows': 1, 'style': 'height:auto', 'class': "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.contact = kwargs.pop('contact', None)
        super(FirstLoginForm, self).__init__(*args, **kwargs)
        self.fields['nom'].required = True
        self.fields['prenom'].required = True
        self.fields['pays'].required = True
        self.fields['ville'].required = True
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_id = 'form_p1'
        self.helper.layout = Layout(
        Div(
            Fieldset(_("معلومات عامة"),
                     HTML("<p class='help-block'>%s</p>" % _("Ces informations seront partagées avec le grand public dans l'annuaire")),
                     Row(
                         Div('nom', css_class='col-lg-6'),
                         Div('pays', css_class='col-lg-6'),
                     ),
                     Row(
                         Div('prenom', css_class='col-lg-6'),
                         Div('ville', css_class='col-lg-6'),
                     ),
                     'adresse'
                     )
            )
        )

    def save(self, commit=False):
        self.contact.nom = self.cleaned_data['nom']
        self.contact.prenom = self.cleaned_data['prenom']
        self.contact.adresse = self.cleaned_data['adresse']
        self.contact.pays = self.cleaned_data['pays']
        self.contact.ville = self.cleaned_data['ville']
        self.contact.save()
        return self.contact


class FirstLoginP1Form(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['specialite', 'qualifications',]
        widgets = {
            'specialite': autocomplete.ModelSelect2(
                url='speciality-autocomplete',
                attrs={
                    'data-placeholder': _('Choisir une spécialité ...'),
                    'data-html': True,
                    'data-theme': 'bootstrap',
                    'class': "form-control"
                },
            ),
            'qualifications': autocomplete.ModelSelect2Multiple(
                    url='qualification-autocomplete',
                    attrs={
                        'data-placeholder': _('Choisir une qualification ...'),
                        'class': "form-control"
                    }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.contact = kwargs.pop('contact', None)
        super(FirstLoginP1Form, self).__init__(*args, **kwargs)
        self.fields['specialite'].required = True
        self.helper = FormHelper()
        self.helper.form_id = 'form_p2'
        self.helper.form_method = 'POST'
        self.helper.layout = Layout(
            Div(
                Fieldset(_("معلومات عامة"),
                         HTML("<p class='help-block'>%s</p>" % _(
                             "Ces informations seront partagées dans l'annuaire avec le grand public")),
                         'qualifications', 'specialite',
                         ),
            )
        )

    def save(self, commit=False):
        self.contact.specialite = self.cleaned_data['specialite']
        self.contact.qualifications.set(self.cleaned_data['qualifications'])
        self.contact.save()
        return self.contact


class FirstLoginP2Form(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['facebook', 'fixe', 'mobile', 'mobile_1', 'mobile_2', ]

        widgets = {
            'mobile': forms.TextInput(attrs={'class': "form-control", }),
            'mobile_1': forms.TextInput(attrs={'class': "form-control", }),
            'mobile_2': forms.TextInput(attrs={'class': "form-control", }),
            'fixe': forms.TextInput(attrs={'class': "form-control", }),
            'facebook': forms.TextInput(attrs={'class': "form-control", }),
        }

    def __init__(self, *args, **kwargs):
        self.contact = kwargs.pop('contact', None)
        super(FirstLoginP2Form, self).__init__(*args, **kwargs)
        self.fields['mobile_1'].required = True
        self.fields['mobile'].required = True
        self.helper = FormHelper()
        self.helper.form_id = 'form_p3'
        self.helper.form_method = 'POST'
        self.helper.layout = Layout(
            Div(
                Fieldset(_("معلومات عامة"),
                         HTML("<p class='help-block'>%s</p>" % _(
                             "Ces informations seront partagées dans l'annuaire avec le grand public")),
                         Row(Div('mobile_1', css_class='col-lg-6'), Div('mobile_2', css_class='col-lg-6')),
                         Row(Div('fixe', css_class='col-lg-6'), Div('facebook', css_class='col-lg-6')),
                     ),
                HTML('<br>'),
                Fieldset(_("معلومات خاصة"),
                         HTML("<p class='help-block'>%s</p>" % _(
                             "Ces informations seront utiliseés pour la relation clientèle eTabib et ne seront pas publiques")),
                            'mobile'),
            )
        )

    def save(self, commit=False):
        self.contact.fixe = self.cleaned_data['fixe']
        self.contact.mobile = self.cleaned_data['mobile']
        self.contact.mobile_1 = self.cleaned_data['mobile_1']
        self.contact.mobile_2 = self.cleaned_data['mobile_2']
        self.contact.facebook = self.cleaned_data['facebook']
        self.contact.save()
        return self.contact

