# -*- coding: utf-8 -*-
import json

from bootstrap_datepicker_plus import DateTimePickerInput
from cities_light.models import Country, City
from crispy_forms.bootstrap import AppendedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Field, HTML, Submit, Row, Column, Fieldset
from dal import autocomplete, forward
from django import forms
from django.core.files.images import get_image_dimensions
from django.forms import ModelForm, DateInput
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import filesizeformat
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from djmoney.forms import MoneyWidget

from core.forms.forms import VersionedMediaJS
from core.models import Partenaire, Contact, Produit, ArticleImage, ArticleDocument, Medic, AutreProduit, AnnonceFeed, \
    AnnonceDisplay, AnnonceImage, CampagneImpression, AnnonceVideo, Video, Catalogue, Stand, PartenaireMarque
from core.widgets import CustomAutoCompleteWidgetSingle
from dropzone.forms import DropzoneInput
from etabibWebsite import settings
from etabibWebsite.settings import ADS_IMAGE_SIZE_CHOICES


class PartnerRegistrationForm(forms.Form):
    family_name = forms.CharField(label=_('Nom'), max_length=255)
    last_name = forms.CharField(label=_('Prénom'), max_length=255)
    company = forms.CharField(label=_('Société'), max_length=255)
    address = forms.CharField(label=_('Adresse'), max_length=255)
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
    mobile = forms.CharField(label=_('Téléphone mobile'), max_length=255)
    phone = forms.CharField(label=_('Téléphone fixe'), max_length=255, required=False)
    nrc = forms.CharField(label=_('Numéro du register de commerce'), max_length=255)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        if self.user:
            try:
                kwargs.update(initial={
                    'family_name': self.user.first_name,
                    'last_name': self.user.last_name
                })
            except:
                pass
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.layout = Layout(
            Div(
                Div('family_name', css_class='col-lg-6'),
                Div('last_name', css_class='col-lg-6'),
                css_class='row'
            ),
            Div(
                Div('country', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div('city', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div('address', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div('company', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div('nrc', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div('mobile', css_class='col-lg-6'),
                Div('phone', css_class='col-lg-6'),
                css_class='row'
            ),
        )
        self.helper.add_input(Submit('submit', _("S'inscrire"), css_class='btn btn-etabib btn-block'))
        self.helper.form_method = 'POST'
        super(PartnerRegistrationForm, self).__init__(*args, **kwargs)

    def save(self):
        if hasattr(self.user, 'partenaire'):
            partenaire = self.user.partenaire
            contact = partenaire.contact
        else:
            partenaire = Partenaire()
            contact = Contact()
        partenaire.user = self.user
        partenaire.user.first_name = self.cleaned_data['family_name']
        partenaire.user.last_name = self.cleaned_data['last_name']
        partenaire.nrc = self.cleaned_data['nrc']
        partenaire.raisonsocial = self.cleaned_data['company']
        contact.nom = self.cleaned_data['family_name']
        contact.prenom = self.cleaned_data['last_name']
        contact.adresse = self.cleaned_data['address']
        contact.pays = self.cleaned_data['country']
        contact.ville = self.cleaned_data['city']
        contact.mobile = self.cleaned_data['mobile']
        contact.fixe = self.cleaned_data['phone']

        contact.save()

        partenaire.user.save()
        partenaire.contact = contact;

        partenaire.save()
        return partenaire


class ArticleImageUploadForm(forms.Form):
    image = forms.ImageField()

    def clean_image(self):
        content = self.cleaned_data['image']
        if content.size > 10 * 1024 * 1024:
            raise forms.ValidationError(_('Please keep filesize under %s. Current filesize %s') % (
                filesizeformat(10 * 1024 * 1024), filesizeformat(content.size)))
        return self.cleaned_data['image']

    def save(self):
        pi = ArticleImage()
        pi.image = self.cleaned_data['image']
        pi.save()
        return pi


class ArticleDocumentUploadForm(forms.Form):
    file = forms.FileField()

    def clean_file(self):
        content = self.cleaned_data['file']
        if content.size > 20 * 1024 * 1024:
            raise forms.ValidationError(_('Please keep filesize under %s. Current filesize %s') % (
                filesizeformat(20 * 1024 * 1024), filesizeformat(content.size)))
        return self.cleaned_data['file']

    def save(self):
        pi = ArticleDocument()
        pi.document = self.cleaned_data['file']
        pi.save()
        return pi


class AdsImageUploadForm(forms.Form):
    image = forms.ImageField()

    def clean_image(self):
        content = self.cleaned_data['image']
        if content.size > 20 * 1024 * 1024:
            raise forms.ValidationError(_('Please keep filesize under %s. Current filesize %s') % (
                filesizeformat(20 * 1024 * 1024), filesizeformat(content.size)))
        return self.cleaned_data['image']

    def save(self):
        pi = AnnonceImage()
        pi.image = self.cleaned_data['image']
        pi.save()
        return pi


class AdsVideoUploadForm(forms.Form):
    video = forms.FileField()

    def clean_video(self):
        content = self.cleaned_data['video']
        if content.size > settings.ADS_MAX_VIDEO_SIZE * 1024 * 1024:
            raise forms.ValidationError(_('Please keep filesize under %s. Current filesize %s') % (
                filesizeformat(settings.ADS_MAX_VIDEO_SIZE * 1024 * 1024), filesizeformat(content.size)))
        return self.cleaned_data['video']

    def save(self):
        v = Video()
        v.fichier = self.cleaned_data['video']
        v.save()
        return v


class ProductForm(ModelForm):
    images = forms.CharField(required=False)
    images_as_json = forms.CharField(widget=forms.Textarea, required=False)
    file1 = forms.CharField(required=False)
    file1_as_json = forms.CharField(widget=forms.Textarea, required=False)
    file2 = forms.CharField(required=False)
    file2_as_json = forms.CharField(widget=forms.Textarea, required=False)

    class Media:
        js = (VersionedMediaJS('js/dropzone/dropzone-active.js','1.2'),)

    def clean(self):
        # TODO: validate maxFiles (=4)
        cleaned_data = super().clean()
        imgs = cleaned_data.get('images')
        if not imgs:
            raise forms.ValidationError(_("Veuillez ajouter une ou plusieurs images pour ce produit."))

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        amount, currency = self.fields['prix'].fields
        amount.widget.attrs['class'] = "form-control"
        currency.widget.attrs['class'] = "form-control"
        self.fields['prix'].widget = CustomMoneyWidget(
            amount_widget=amount.widget, currency_widget=currency.widget
        )
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.layout = Layout(
            Div(
                Div('libelle', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div('n_enregistrement', css_class='col-lg-6'),
                Div('categorie', css_class='col-lg-6'),
                css_class='row'
            ),
            Div(
                Div('marque', css_class='col-lg-6'),
                Div('origine', css_class='col-lg-6'),
                css_class='row'
            ),
            Div(
                Div('prix', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div(
                    AppendedText('promotion', '%')
                    , css_class='col-lg-6'
                ),
                Div('fin_promotion', css_class='col-lg-6'),
                css_class='row'
            ),
            Div(
                Div('description', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div(
                    Div(
                        HTML(
                            '<div class ="dz-default dz-message" > '
                            '<span> Déposer un  document pour l\'autorisation'
                            '</span> </div>'
                        ),
                        css_id="product_document_aut",
                        css_class="needsclick download-custom dropzone dropzone-custom",
                    ),
                    css_class="col-lg-6"
                ),
                Div(
                    Div(
                        HTML(
                            '<div class ="dz-default dz-message" > '
                            '<span> Déposer un Document pour l\'homologation.'
                            '</span> </div>'
                        ),
                        css_id="product_document_hom",
                        css_class="needsclick download-custom dropzone dropzone-custom",
                    ),
                    css_class="col-lg-6"
                ),
                css_class='row'
            ),
            HTML(
                '<br>'
            ),
            Field('images', type="hidden"),
            Field('images_as_json', type="hidden"),
            Field('file1', type="hidden"),
            Field('file1_as_json', type="hidden"),
            Field('file2', type="hidden"),
            Field('file2_as_json', type="hidden"),
            Div(
                HTML(
                    '<div class ="dz-default dz-message" > '
                    '<span> <strong> ' + str(_("Images du produit.</strong > ")) +
                    '<br> - ' + str(_("Nombre maximum d'images = 4 Images")) +
                    '<br> - ' + str(_("Taille maximale d'une image = 2Mb")) +
                    '<br> - ' + str(_("Résolution = 1000x1000")) +
                    '</span> </div>'
                ),
                css_id="product_images",
                css_class="needsclick download-custom dropzone dropzone-custom",
            ),
        )

    class Meta:
        model = Produit
        exclude = ['partenaire']
        widgets = {
            'fin_promotion': DateTimePickerInput(
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                    "minDate": str(timezone.now())
                }
            ),
            'categorie': CustomAutoCompleteWidgetSingle(
                url='categorie-produit-autocomplet',
                attrs={
                    'data-html': True,
                    'class': "form-control",
                }
            )

        }

    def getImages(self):
        return self.cleaned_data['images'].split(',')

    def getFile(self, i):
        if i == 1:
            return self.cleaned_data['file1']
        if i == 2:
            return self.cleaned_data['file2']


class CustomMoneyWidget(MoneyWidget):
    template_name = "django/forms/widgets/money.html"


class DrugForm(ModelForm):
    images = forms.CharField(required=False)
    images_as_json = forms.CharField(widget=forms.Textarea, required=False)
    file1 = forms.CharField(required=False)
    file1_as_json = forms.CharField(widget=forms.Textarea, required=False)
    file2 = forms.CharField(required=False)
    file2_as_json = forms.CharField(widget=forms.Textarea, required=False)

    def clean(self):
        # TODO: validate maxFiles (=4)
        cleaned_data = super().clean()
        imgs = cleaned_data.get('images')
        if not imgs:
            raise forms.ValidationError(_("Veuillez ajouter une ou plusieurs images pour ce medicamant."))

    class Media:
        js = (VersionedMediaJS('js/dropzone/dropzone-active.js','1.2'),)

    class Meta:
        model = Medic
        exclude = ['partenaire']
        widgets = {
            'dci': autocomplete.ModelSelect2(
                url='dci-autocomplete',
                attrs={
                    'data-html': True,
                    'class': "form-control",
                }
            ),
            'interactions': autocomplete.ModelSelect2Multiple(
                url='dci-autocomplete',
                attrs={
                    'data-html': True,
                    'class': "form-control",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super(DrugForm, self).__init__(*args, **kwargs)
        amount, currency = self.fields['prix'].fields
        amount.widget.attrs['class'] = "form-control"
        currency.widget.attrs['class'] = "form-control"
        self.fields['prix'].widget = CustomMoneyWidget(
            amount_widget=amount.widget, currency_widget=currency.widget
        )
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.layout = Layout(
            Div(
                Div('libelle', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div(
                    'n_enregistrement',
                    css_class="col-lg-6"
                ),
                Div(
                    'type',
                    css_class="col-lg-6"
                ),
                css_class="row"
            ),
            Div(
                Div('dci', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div(
                    'fabriquant',
                    css_class="col-lg-6"
                ),
                Div(
                    'exploitant',
                    css_class="col-lg-6"
                ),
                css_class="row"
            ),
            Div(
                Div(
                    'prix',
                    css_class="col-lg-8"
                ),
                Div(
                    'remboursement',
                    css_class="col-lg-4"
                ),
                css_class="row"
            ),
            Div(
                Div('indications', css_class='col-lg-12'),
                css_class="row"
            ),
            Div(
                Div('interactions', css_class='col-lg-12'),
                css_class="row"
            ),
            Div(
                Div('ref_etude', css_class='col-lg-12'),
                css_class="row"
            ),
            Field('images', type="hidden"),
            Field('images_as_json', type="hidden"),
            Field('file1', type="hidden"),
            Field('file1_as_json', type="hidden"),
            Field('file2', type="hidden"),
            Field('file2_as_json', type="hidden"),
            Div(
                Div(
                    Div(
                        HTML(
                            '<div class ="dz-default dz-message" > '
                            '<span> RCP'
                            '</span> </div>'
                        ),
                        css_id="medic_rcp",
                        css_class="needsclick download-custom dropzone dropzone-custom",
                    ),
                    css_class="col-lg-6"
                ),
                Div(
                    Div(
                        HTML(
                            '<div class ="dz-default dz-message" > '
                            '<span> Document attestant l\'autorisation AMM'
                            '</span> </div>'
                        ),
                        css_id="medic_document_aut",
                        css_class="needsclick download-custom dropzone dropzone-custom",
                    ),
                    css_class="col-lg-6"
                ),
                css_class='row'
            ),
            HTML(
                '<br>'
            ),
            Div(
                HTML(
                    '<div class ="dz-default dz-message" > '
                    '<span> <strong> ' + str(_("Images du produit.</strong > ")) +
                    '<br> - ' + str(_("Nombre maximum d'images = 4 Images")) +
                    '<br> - ' + str(_("Taille maximale d'une image = 2Mb")) +
                    '<br> - ' + str(_("Résolution = 1000x1000")) +
                    '</span> </div>'
                ),
                css_id="medic_images",
                css_class="needsclick download-custom dropzone dropzone-custom",
            ),
        )

    def getImages(self):
        return self.cleaned_data['images'].split(',')

    def getFile(self, i):
        if i == 1:
            return self.cleaned_data['file1']
        if i == 2:
            return self.cleaned_data['file2']


class OtherProductForm(ModelForm):
    images = forms.CharField(required=False)
    images_as_json = forms.CharField(widget=forms.Textarea, required=False)

    def clean(self):
        # TODO: validate maxFiles (=4)
        cleaned_data = super().clean()
        imgs = cleaned_data.get('images')
        if not imgs:
            raise forms.ValidationError(_("Veuillez ajouter une ou plusieurs images pour ce produit."))

    class Media:
        js = (VersionedMediaJS('js/dropzone/dropzone-active.js','1.2'),)

    class Meta:
        model = AutreProduit
        exclude = ['partenaire']

    def __init__(self, *args, **kwargs):
        super(OtherProductForm, self).__init__(*args, **kwargs)
        amount, currency = self.fields['prix'].fields
        amount.widget.attrs['class'] = "form-control"
        currency.widget.attrs['class'] = "form-control"
        self.fields['prix'].widget = CustomMoneyWidget(
            amount_widget=amount.widget, currency_widget=currency.widget
        )
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.layout = Layout(
            Div(
                Div('libelle', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div(
                    'reference',
                    css_class="col-lg-6"
                ),
                Div(
                    'categorie',
                    css_class="col-lg-6"
                ),
                css_class="row"
            ),
            Div(
                Div(
                    'marque',
                    css_class="col-lg-6"
                ),
                Div(
                    'origine',
                    css_class="col-lg-6"
                ),
                css_class="row"
            ),
            Div(
                Div('prix', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div('description', css_class='col-lg-12'),
                css_class='row'
            ),
            Field('images', type="hidden"),
            Field('images_as_json', type="hidden"),
            Div(
                HTML(
                    '<div class ="dz-default dz-message" > '
                    '<span> <strong> ' + str(_("Images du produit.</strong > ")) +
                    '<br> - ' + str(_("Nombre maximum d'images = 4 Images")) +
                    '<br> - ' + str(_("Taille maximale d'une image = 2Mb")) +
                    '<br> - ' + str(_("Résolution = 1000x1000")) +
                    '</span> </div>'
                ),
                css_id="other_product_images",
                css_class="needsclick download-custom dropzone dropzone-custom",
            ),
        )

    def getImages(self):
        return self.cleaned_data['images'].split(',')


class AnnonceFeedForm(ModelForm):
    titre = forms.CharField(max_length=30, help_text="titre de l'annonce <= 30 charactères")
    corps = forms.CharField(widget=forms.Textarea, max_length=90, help_text="corps de l'annonce <= 90 charactères")

    class Meta:
        model = AnnonceFeed
        fields = ('libelle', 'titre', 'corps', 'article', 'external_link')
        labels = {
            'article': _('Produit')
        }
        widgets = {
            'article': autocomplete.ModelSelect2(
                url='article-autocomplete',
                attrs={
                    'data-html': True,
                    'class': "form-control",
                    'data-theme': 'bootstrap'
                }
            ),
        }


class AnnonceDisplayForm(ModelForm):
    image_728x360 = forms.CharField(
        required=False,
        label=_("Annonce interstitielle store code SI1"),
        widget=DropzoneInput(
            maxFilesize=1,
            acceptedFiles="image/*",
            paramName='image',
            placeholder=_("cliquer pour uploader une image"),
            maxFiles=1,
            width=settings.ADS_728x360_WIDTH,
            height=settings.ADS_728x360_HEIGHT,
            upload_path='/annonce-image-upload/'
        ),
        help_text=_("Résolution = %sx%s pixels, Poids: 1Mo") %
                  (settings.ADS_728x360_WIDTH, settings.ADS_728x360_HEIGHT)
    )
    image_200x360 = forms.CharField(
        required=False,
        label=_("Annonce interstitielle store code SI2"),
        widget=DropzoneInput(
            maxFilesize=1,
            acceptedFiles="image/*",
            paramName='image',
            placeholder=_("cliquer pour uploader une image"),
            maxFiles=1,
            width=settings.ADS_200x360_WIDTH,
            height=settings.ADS_200x360_HEIGHT,
            upload_path='/annonce-image-upload/'
        ),
        help_text=_("Résolution = %sx%s pixels, Poids: 1Mo") %
                  (settings.ADS_200x360_WIDTH, settings.ADS_200x360_HEIGHT)
    )

    image_500x360 = forms.CharField(
        required=False,
        label=_("Annonce interstitielle store code SI3"),
        widget=DropzoneInput(
            maxFilesize=1,
            acceptedFiles="image/*",
            paramName='image',
            placeholder=_("cliquer pour uploader une image"),
            maxFiles=1,
            width=settings.ADS_500x360_WIDTH,
            height=settings.ADS_500x360_HEIGHT,
            upload_path='/annonce-image-upload/'
        ),
        help_text=_("Résolution = %sx%s pixels, Poids: 1Mo") %
                  (settings.ADS_500x360_WIDTH, settings.ADS_500x360_HEIGHT)
    )

    image_450x416 = forms.CharField(
        required=False,
        label=_("Annonce workspace code EG"),
        widget=DropzoneInput(
            maxFilesize=1,
            acceptedFiles="image/*",
            paramName='image',
            placeholder=_("cliquer pour uploader une image"),
            maxFiles=1,
            width=settings.ADS_450x416_WIDTH,
            height=settings.ADS_450x416_HEIGHT,
            upload_path='/annonce-image-upload/'
        ),
        help_text=_("Résolution = %sx%s pixels, Poids: 1Mo") %
                  (settings.ADS_450x416_WIDTH, settings.ADS_450x416_HEIGHT)
    )

    image_1600x840 = forms.CharField(
        required=False,
        label=_("Annonce expo code EX"),
        widget=DropzoneInput(
            maxFilesize=1,
            acceptedFiles="image/*",
            paramName='image',
            placeholder=_("cliquer pour uploader une image"),
            maxFiles=1,
            width=settings.ADS_1600x840_WIDTH,
            height=settings.ADS_1600x840_HEIGHT,
            upload_path='/annonce-image-upload/'
        ),
        help_text=_("Résolution = %sx%s pixels, Poids: 1Mo") %
                  (settings.ADS_1600x840_WIDTH, settings.ADS_1600x840_HEIGHT)
    )

    image_728x360_as_json = forms.CharField(widget=forms.Textarea, required=False)
    image_200x360_as_json = forms.CharField(widget=forms.Textarea, required=False)
    image_450x416_as_json = forms.CharField(widget=forms.Textarea, required=False)
    image_500x360_as_json = forms.CharField(widget=forms.Textarea, required=False)
    image_1600x840_as_json = forms.CharField(widget=forms.Textarea, required=False)

    def clean_image_500x360(self):
        image_500x360 = self.cleaned_data['image_500x360']
        if image_500x360:
            try:
                annonceImage = AnnonceImage.objects.get(pk=image_500x360)
                width, height = get_image_dimensions(annonceImage.image)
                if width != settings.ADS_500x360_WIDTH or height != settings.ADS_500x360_HEIGHT:
                    raise forms.ValidationError(_("Dimension d'image invalide"))
                else:
                    annonceImage.type = ADS_IMAGE_SIZE_CHOICES[3][0]
                    annonceImage.save()
            except AnnonceImage.DoesNotExist:
                raise forms.ValidationError(_("Ce champ est obligatoire"))
        return self.cleaned_data['image_500x360']

    def clean_image_450x416(self):
        image_450x416 = self.cleaned_data['image_450x416']
        if image_450x416:
            try:
                annonceImage = AnnonceImage.objects.get(pk=image_450x416)
                width, height = get_image_dimensions(annonceImage.image)
                if width != settings.ADS_450x416_WIDTH or height != settings.ADS_450x416_HEIGHT:
                    raise forms.ValidationError(_("Dimension d'image invalide"))
                else:
                    annonceImage.type = ADS_IMAGE_SIZE_CHOICES[1][0]
                    annonceImage.save()
            except AnnonceImage.DoesNotExist:
                raise forms.ValidationError(_("Ce champ est obligatoire"))
        return self.cleaned_data['image_450x416']

    def clean_image_200x360(self):
        image_200x360 = self.cleaned_data['image_200x360']
        if image_200x360:
            try:
                annonceImage = AnnonceImage.objects.get(pk=image_200x360)
                width, height = get_image_dimensions(annonceImage.image)
                if width != settings.ADS_200x360_WIDTH or height != settings.ADS_200x360_HEIGHT:
                    raise forms.ValidationError(_("Dimension d'image invalide"))
                else:
                    annonceImage.type = ADS_IMAGE_SIZE_CHOICES[2][0]
                    annonceImage.save()
            except AnnonceImage.DoesNotExist:
                raise forms.ValidationError(_("Ce champ est obligatoire"))
        return self.cleaned_data['image_200x360']

    def clean_image_728x360(self):
        image_728x360 = self.cleaned_data['image_728x360']
        if image_728x360:
            try:
                annonceImage = AnnonceImage.objects.get(pk=image_728x360)
                width, height = get_image_dimensions(annonceImage.image)
                if width != settings.ADS_728x360_WIDTH or height != settings.ADS_728x360_HEIGHT:
                    raise forms.ValidationError(_("Dimension d'image invalide"))
                else:
                    annonceImage.type = ADS_IMAGE_SIZE_CHOICES[4][0]
                    annonceImage.save()
            except AnnonceImage.DoesNotExist:
                raise forms.ValidationError(_("Ce champ est obligatoire"))
        return self.cleaned_data['image_728x360']

    def clean_image_1600x840(self):
        image_1600x840 = self.cleaned_data['image_1600x840']
        if image_1600x840:
            try:
                annonceImage = AnnonceImage.objects.get(pk=image_1600x840)
                width, height = get_image_dimensions(annonceImage.image)
                if width != settings.ADS_1600x840_WIDTH or height != settings.ADS_1600x840_HEIGHT:
                    raise forms.ValidationError(_("Dimension d'image invalide"))
                else:
                    annonceImage.type = ADS_IMAGE_SIZE_CHOICES[5][0]
                    annonceImage.save()
            except AnnonceImage.DoesNotExist:
                raise forms.ValidationError(_("Ce champ est obligatoire"))
        return self.cleaned_data['image_1600x840']

    def clean(self):
        cleaned_data = super().clean()
        image_728x360 = cleaned_data.get('image_728x360')
        image_200x360 = cleaned_data.get('image_200x360')
        image_450x416 = cleaned_data.get('image_450x416')
        image_500x360 = cleaned_data.get('image_500x360')
        image_1600x840 = cleaned_data.get('image_1600x840')
        if not image_728x360 and not image_200x360 and not image_450x416 and not image_500x360 and not image_1600x840:
            raise forms.ValidationError(_("Veuillez ajouter au moins une image pour cette annonce."))

    class Media:
        js = (VersionedMediaJS('js/dropzonee/dropzone.django.js', '2.2'),)

    class Meta:
        model = AnnonceDisplay
        fields = ('libelle', 'article', 'external_link')
        labels = {
            'libelle': _("Nom du groupe d'annonce"),
            'article': _('Produit')
        }
        widgets = {
            'article': autocomplete.ModelSelect2(
                url='article-autocomplete',
                attrs={
                    'data-html': True,
                    'class': "form-control",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super(AnnonceDisplayForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.layout = Layout(
            Div(
                Div('libelle', css_class='col-lg-12'),
                css_class='row'
            ),
            # https://sproutsocial.com/insights/facebook-ad-sizes/
            Div(
                Div('image_728x360', css_class='col-lg-12'),
                css_class='row'
            ), Field('image_728x360_as_json', type="hidden")
            , Div(
                Div('image_200x360', css_class='col-lg-12'),
                css_class='row'
            ), Field('image_200x360_as_json', type="hidden"),
            Div(
                Div('image_500x360', css_class='col-lg-12'),
                css_class='row'
            ), Field('image_500x360_as_json', type="hidden"),
            Div(
                Div('image_450x416', css_class='col-lg-12'),
                css_class='row'
            ), Field('image_450x416_as_json', type="hidden"),
            Div(
                Div('image_1600x840', css_class='col-lg-12'),
                css_class='row'
            ), Field('image_1600x840_as_json', type="hidden"),
            Div(
                Div('article', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div('external_link', css_class='col-lg-12'),
                css_class='row'
            )
        )

    def getImage_450x416(self):
        return self.cleaned_data['image_450x416']

    def getImage_200x360(self):
        return self.cleaned_data['image_200x360']

    def getImage_728x360(self):
        return self.cleaned_data['image_728x360']

    def getImage_500x360(self):
        return self.cleaned_data['image_500x360']

    def getImage_1600x840(self):
        return self.cleaned_data['image_1600x840']


class CatalogueForm(ModelForm):
    class Meta:
        model = Catalogue
        exclude = ["cree_par", "date_creation"]


class AnnonceVideoForm(ModelForm):
    _video = forms.CharField(
        required=True,
        label=_("Video"),
        widget=DropzoneInput(
            maxFilesize=settings.ADS_MAX_VIDEO_SIZE,
            acceptedFiles="video/*",
            maxDuration=settings.ADS_MAX_VIDEO_DURATION,  # in seconds
            paramName='video',
            placeholder=_("cliquer pour uploader une video"),
            maxFiles=1,
            upload_path='/annonce-video-upload/'
        ),
        help_text=_("La vidéo sera Soumise à validation avant d'être publiée, décourez les règles relatives au contenu."
                    "<a href='#'>Ici</a><br>"
                    "La durée de la vidéo doit être <= %s secondes") % settings.ADS_MAX_VIDEO_DURATION
    )

    class Meta:
        model = AnnonceVideo
        fields = ('libelle', '_video')

    class Media:
        js = (VersionedMediaJS('js/dropzonee/dropzone.django.js', '2.2'), "js/dropzonee/jquery.cookie.js",)

    def __init__(self, *args, **kwargs):
        super(AnnonceVideoForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.layout = Layout(
            # audio element used to calculate duration of the video before uploading it to the server
            'libelle', '_video', HTML("<audio id='audio'></audio")
        )

    def clean(self):
        cleaned_data = super().clean()
        _video = cleaned_data.get('_video')
        video = get_object_or_404(Video, id=_video)
        # TODO: find another way to validate video duration in GOOGLE DRIVE
        # v = VideoFileClip(video.path)
        # if v.duration > settings.ADS_MAX_VIDEO_DURATION:
        #     raise forms.ValidationError(
        #         _("La durée de la vidéo doit être <= %s secondes") % settings.ADS_MAX_VIDEO_DURATION)


class CampagneImpForm(ModelForm):
    class Meta:
        model = CampagneImpression
        exclude = ['partenaire', 'reseaux', 'budget_max']
        widgets = {
            'zones': autocomplete.ModelSelect2Multiple(
                url='region-autocomplete',
                attrs={
                    'class': "form-control",
                },
                forward=(forward.Const(62, 'country'),)
            ),
            'cibles': autocomplete.ModelSelect2Multiple(
                url='speciality-autocomplete',
                attrs={
                    'class': "form-control",
                }
            )
            , 'annonces': autocomplete.ModelSelect2Multiple(
                url='annonce-autocomplete',
                attrs={
                    'data-html': True,
                    'class': "form-control",
                }
            ),
            'date_debut': DateTimePickerInput(
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                    "minDate": str(timezone.now())
                }
            ),
            'date_fin': DateTimePickerInput(
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                    "minDate": str(timezone.now())
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super(CampagneImpForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.layout = Layout(
            HTML(
                "<p>Votre campagne réunira tous les services que vous désirez utiliser pour atteindre les objectifs de la communication médicale que vous voulez entreprendre.<br>"
                "1- Choisissez les services que vous voulez utiliser<br>2- Paramétrez-les en fonction de votre besoin et valider l’opération. <br>3- Vous avez la possibilité de lancer la campagne immédiatement ou la différer pour une date ultérieure.</p>"
            ),
            Div(
                Div('libelle', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div('annonces', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div('cibles', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div('toutes_specialites', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div('zones', css_class='col-lg-12'),
                css_class='row'
            ),
            Div(
                Div('toutes_zones', css_class='col-lg-12'),
                css_class='row'
            ),
        )


class CampagneAnnulationForm(ModelForm):
    class Meta:
        model = CampagneImpression
        fields = ('id',)


class CampagneStopForm(ModelForm):
    class Meta:
        model = CampagneImpression
        fields = ('id',)


class CampagneActivationForm(ModelForm):
    class Meta:
        model = CampagneImpression
        fields = ('date_debut', 'date_fin')
        widgets = {
            'date_debut': DateTimePickerInput(
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                    "minDate": str(timezone.now())
                }
            ),
            'date_fin': DateTimePickerInput(
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                    "minDate": str(timezone.now())
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        date_fin = cleaned_data.get('date_fin')
        date_debut = cleaned_data.get('date_debut')
        if date_debut < timezone.now():
            raise forms.ValidationError(_("veuillez entrer une date de début valide."))
        if date_fin < timezone.now():
            raise forms.ValidationError(_("veuillez entrer une date de fin valide."))
        if date_fin <= date_debut:
            raise forms.ValidationError(_("Veuillez entre une date de début et une date de fin valides."))


class StandForm(forms.ModelForm):
    class Meta:
        model = Stand
        fields = ("link", "banner", "signaletique", "slogan","publie")
        labels = {
            "banner": _("Photo d'habillage du stand")
        }

    def __init__(self, *args, **kwargs):
        self.partenaire = kwargs.pop('partenaire', None)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.layout = Layout(
            'signaletique',
            'slogan',
            'link',
            'publie',
            'banner',
        )
        self.helper.add_input(Submit('submit', _("Mettre à jour"), css_class='btn btn-etabib'))
        super(StandForm, self).__init__(*args, **kwargs)
        self.is_insert = self.instance.pk == None

    def clean_banner(self):
        content = self.cleaned_data['banner']
        if content :
            if content.size > 10 * 1024 * 1024:
                raise forms.ValidationError(_('Please keep filesize under %s. Current filesize %s') % (
                    filesizeformat(10 * 1024 * 1024), filesizeformat(content.size)))
            w, h = get_image_dimensions(content)
            if w != 1600:
                raise forms.ValidationError(_("The image is %i pixel wide. It's supposed to be 1600px" % w))
            if h != 840:
                raise forms.ValidationError(_("The image is %i pixel high. It's supposed to be 840px" % h))

            return self.cleaned_data['banner']

    def save(self, commit=True):
        stand = super(StandForm, self).save(commit=False)
        link = self.cleaned_data['link']
        publie = self.cleaned_data['publie']
        banner = self.cleaned_data['banner']
        slogan = self.cleaned_data['slogan']
        signaletique = self.cleaned_data['signaletique']

        stand.link = link
        stand.publie = publie
        stand.banner = banner
        stand.slogan = slogan
        stand.signaletique = signaletique
        stand.partner = self.partenaire
        stand.save()
        return stand


class PartenaireProfileForm(ModelForm):
    adresse = forms.CharField(label=_('Adresse'), max_length=255, required=False)
    pays = forms.ModelChoiceField(
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
        required=False
    )
    ville = forms.ModelChoiceField(
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
        required=False
    )
    mobile = forms.CharField(label=_('Téléphone mobile'), max_length=255, required=False)
    fixe = forms.CharField(label=_('Téléphone fixe'), max_length=255, required=False)
    email = forms.EmailField(label=_('Email professionnel'), max_length=255, required=False)
    pageweb = forms.URLField(label=_('Site Web'), max_length=255, required=False)
    facebook = forms.URLField(label=_('Page Facebook'), max_length=255, required=False)
    linkedin = forms.URLField(label=_('Page LinkedIn'), max_length=255, required=False)
    image = forms.CharField(required=False)
    image_as_json = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = Partenaire
        fields = ('raisonsocial', 'nrc', 'banner', 'logo', 'description',)
        help_texts = {
            "banner": _("Résolution: (900x150), Poids < 10Mo"),
            "logo": _("Résolution: (200x200), Poids < 10Mo"),
        }

    class Media:
        js = ('js/dropzone/dropzone-active.js',)

    def clean_banner(self):
        content = self.cleaned_data['banner']
        if content:
            if content.size > 10 * 1024 * 1024:
                raise forms.ValidationError(_('Please keep filesize under %s. Current filesize %s') % (
                    filesizeformat(10 * 1024 * 1024), filesizeformat(content.size)))
            w, h = get_image_dimensions(content)
            if w != 900:
                raise forms.ValidationError(_("The image Width must be 900px"))
            if h != 150:
                raise forms.ValidationError(_("The image Height must be 150px"))

            return self.cleaned_data['banner']

    def clean_logo(self):
        content = self.cleaned_data['logo']
        if content:
            if content.size > 10 * 1024 * 1024:
                raise forms.ValidationError(_('Please keep filesize under %s. Current filesize %s') % (
                    filesizeformat(10 * 1024 * 1024), filesizeformat(content.size)))
            w, h = get_image_dimensions(content)
            if w != 200:
                raise forms.ValidationError(_("The image Width must be 200px"))
            if h != 200:
                raise forms.ValidationError(_("The image Height must be 200px"))

            return self.cleaned_data['logo']

    def save(self):
        partenaire = super(PartenaireProfileForm, self).save(commit=False)
        contact = partenaire.contact

        partenaire.nrc = self.cleaned_data['nrc']
        partenaire.raisonsocial = self.cleaned_data['raisonsocial']
        partenaire.description = self.cleaned_data['description']
        partenaire.banner = self.cleaned_data['banner']
        partenaire.logo = self.cleaned_data['logo']

        contact.adresse = self.cleaned_data['adresse']
        contact.pays = self.cleaned_data['pays']
        contact.ville = self.cleaned_data['ville']
        contact.mobile = self.cleaned_data['mobile']
        contact.fixe = self.cleaned_data['fixe']
        contact.email = self.cleaned_data['email']
        contact.pageweb = self.cleaned_data['pageweb']
        contact.facebook = self.cleaned_data['facebook']
        contact.linkedin = self.cleaned_data['linkedin']

        contact.save()
        partenaire.save()
        return partenaire

    def getimages(self):
        return self.cleaned_data['image_as_json']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.partenaire = self.user.partenaire
        trademark_logos = {}
        if self.partenaire:
            kwargs.update(initial=dict(mobile=self.partenaire.contact.mobile,
                                       fixe=self.partenaire.contact.fixe, pageweb=self.partenaire.contact.pageweb,
                                       email=self.partenaire.contact.email, facebook=self.partenaire.contact.facebook,
                                       linkedin=self.partenaire.contact.linkedin,
                                       adresse=self.partenaire.contact.adresse, pays=self.partenaire.contact.pays,
                                       ville=self.partenaire.contact.ville),)
            logos = PartenaireMarque.objects.filter(partenaire=self.partenaire)
            trademark_logos = json.dumps([logo.to_json() for logo in logos])
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', _("Mettre à jour"), css_class='btn btn-etabib floatright'))
        self.helper.form_method = 'POST'
        self.helper.layout = Layout(
            Div(
                Div(
                    HTML('<h4>Entreprise</h4>'),
                    Div('raisonsocial', 'nrc', 'adresse', 'pays', 'ville', 'mobile', 'fixe', 'email', 'pageweb',
                        'facebook', 'linkedin',
                        css_class='well'),
                    css_class='col-lg-4 col-md-6 col-sm-6 col-xs-12'
                ),
                Div(
                    HTML('<h4>A propos</h4>'),
                    Div('description',
                        css_class='panel-body'),
                    css_class='col-lg-8 col-md-6 col-sm-6 col-xs-12'
                ),
                Field('image', type="hidden"),
                Field('image_as_json', type="hidden", value=trademark_logos),
                Div(
                    HTML('<h4>Marques Représentées</h4>'),
                    Div(
                        HTML(
                            '<div class ="dz-default dz-message" > '
                            '<span>Cliquez pour ajouter un Logo (format accepté: 200x200)'
                            '</span> </div>'
                        ),
                        css_id="logo_tradmarks",
                        css_class="needsclick download-custom dropzone dropzone-custom",
                    ),
                    HTML('<br/>'),
                    css_class="col-lg-8 col-md-6 col-sm-6 col-xs-12"
                ),
                Div(
                    HTML('<h4>Charte Graphique</h4>'),
                    Div('banner', css_class='col-lg-6 col-md-6'),
                    Div('logo', css_class='col-lg-6 col-md-6'),
                    css_class='col-lg-8 col-md-6 col-sm-6 col-xs-12'
                ),
                css_class='row'
            ),
        )
        super(PartenaireProfileForm, self).__init__(*args, **kwargs)


class LogoTrademarkUploadForm(forms.Form):
    image = forms.ImageField()

    def clean_image(self):
        content = self.cleaned_data['image']
        if content.size > 20 * 1024 * 1024:
            raise forms.ValidationError(_('Please keep filesize under %s. Current filesize %s') % (
                filesizeformat(20 * 1024 * 1024), filesizeformat(content.size)))
        return self.cleaned_data['image']

    def save(self):
        partner = get_object_or_404(Partenaire, pk=self.user.pk)
        marque = PartenaireMarque()
        marque.image = self.cleaned_data['image']
        marque.partenaire = partner
        marque.save()
        return marque

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(LogoTrademarkUploadForm, self).__init__(*args, **kwargs)
