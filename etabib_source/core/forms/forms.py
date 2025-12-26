# -*- coding: utf-8 -*-

from PIL import Image
from allauth.account.models import EmailAddress
from captcha.fields import CaptchaField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Div, HTML, Field, Row, Column
from dal import autocomplete, forward
from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.forms import DateInput
from django.template.defaultfilters import filesizeformat
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from snowpenguin.django.recaptcha3.fields import ReCaptchaField
from validate_email import validate_email

from core.enums import Role
from core.models import Contact, Avatar, CarteProfessionnelle, \
    ProfessionnelSante
from dropzone.forms import DropzoneInput


class VersionedMediaJS():
    def __init__(self, path, version):
        self.path = forms.widgets.Media.absolute_path(None, path)
        self.version = version

    def render(self):
        html = '<script type="text/javascript" src="{0}?v={1}"></script>'
        return format_html(html, mark_safe(self.path), self.version)

    @staticmethod
    def render_js(media_object):
        html = []
        for path in media_object._js:
            if hasattr(path, 'version'):
                html.append(path.render())
            else:
                html.append(
                    format_html('<script type="text/javascript" src="{0}"></script>', media_object.absolute_path(path)))
        return html


forms.widgets.Media.render_js = VersionedMediaJS.render_js


# THIS CLASS WAS USED TO SIGNUP A USER, WE USE NOW THE class SignupForm
class LocalSignupForm(forms.Form):
    first_name = forms.CharField(label=_('Nom'), max_length=255, widget=forms.TextInput(attrs={
        'placeholder': _("Tapez votre nom")
    }))
    last_name = forms.CharField(label=_('Prénom'), max_length=255, widget=forms.TextInput(attrs={
        'placeholder': _("Tapez votre prénom")
    }))
    captcha = ReCaptchaField()

    def signup(self, request, user):
        role = request.GET.get('type', None)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.form_show_labels = False
        self.helper.add_input(Submit('submit', _('Sign Up'), css_class='btn btn-etabib btn-lg'))
        self.helper.form_method = 'POST'
        help_text = _("bienvenue dans eTabib. Ce formulaire vous aidera à vous inscrire sur la plateforme. "
                      "Vous receverez un email de validation dans les 24 heures, "
                      "si ce n'est pas le cas contactez nous via le Livechat (pastille blue)")
        self.helper.layout = Layout(
            HTML("<div class='alert alert-info'>" + str(help_text) + "</div>"),
            Field('first_name', css_class="etabib-form-control"),
            Field('last_name', css_class="etabib-form-control"),
            Field('email', css_class="etabib-form-control"),
            Field('password1', css_class="etabib-form-control"),
            Div(HTML(password_validation.password_validators_help_text_html()), css_class="password-help-text"),
            Field('password2', css_class="etabib-form-control"),
            'captcha'
        )


class SignupForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'placeholder': _("Tapez votre addresse e-mail")
    }))
    captcha = CaptchaField()

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists() or EmailAddress.objects.filter(email=email).exists():
            raise forms.ValidationError(
                _("Vous vous êtes déjà inscrit avec cet e-mail, Veuillez plutôt vous connecter")
            )
        if not validate_email(email_address=email, check_format=True, check_dns=True, check_smtp=False):
            raise forms.ValidationError(
                _("L'adresse mail n'est pas valide!")
            )
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.form_show_labels = False
        self.helper.form_method = 'POST'
        btn_str = _("Envoyer")
        self.helper.layout = Layout(
            HTML("<h1 style='font-size: 18px;'>" + "أين نرسل لك رمزك السري؟" + "</h1>"),
            Field('email', css_class="etabib-form-control center-block"),
            "captcha",
            HTML("<button type='submit' name='submit' class='btn btn-primary btn btn-etabib'>"
                 "<i class='fa fa-send'></i>" + str(btn_str) + "</button>")
        )

    def save(self):
        email = self.cleaned_data['email']
        with transaction.atomic():
            user = User()
            user.email = email
            password = User.objects.make_random_password()
            user.set_password(password)
            user.username = email
            user.save()

            mail = EmailAddress()
            mail.user = user
            mail.primary = True
            mail.verified = False
            mail.email = email
            mail.save()
        return (user, password)


class SignupFormWorkspace(forms.ModelForm):
    card = forms.CharField(
        label=_("Carte professionnelle"),
        widget=DropzoneInput(
            maxFilesize=10,
            acceptedFiles="image/*",
            paramName='image',
            placeholder=_("cliquer pour uploader une image"),
            maxFiles=1,
            upload_path='/cp-upload/'
        ),
        help_text=_("Un document attestant votre affiliation au corps médical (Carte professionnelle,\
                                        ou tout autre document")
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists() or EmailAddress.objects.filter(email=email).exists():
            raise forms.ValidationError(
                _("Vous vous êtes déjà inscrit avec cet e-mail, Veuillez plutôt vous connecter")
            )
        if not validate_email(email_address=email, check_format=True, check_dns=True, check_smtp=False):
            raise forms.ValidationError(
                _("L'adresse mail n'est pas valide!")
            )
        return email

    def clean(self):
        cleaned_data = super().clean()
        card = cleaned_data.get('card')
        if not card:
            raise forms.ValidationError(_("Veuillez ajouter une carte professionnelle"))

    class Meta:
        model = Contact
        fields = ["nom", "prenom", "date_naissance", "sexe", "mobile", "specialite", "type_exercice", "email"]
        widgets = {
            "specialite": autocomplete.ModelSelect2(
                url='speciality-autocomplete',
                attrs={
                    'data-placeholder': _('Choisir une spécialité ...'),
                    'data-html': True,
                    'data-theme': 'bootstrap'
                }
            ),
            'date_naissance': DateInput(attrs={'type': 'date'})
        }

    class Media:
        js = (VersionedMediaJS('js/dropzonee/dropzone.django.js', '2.2'),)

    def __init__(self, *args, **kwargs):
        super(SignupFormWorkspace, self).__init__(*args, **kwargs)
        for field in self.Meta.fields:
            self.fields[field].required = True
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        btn_str = _("Envoyer")
        self.helper.layout = Layout(
            Field(
                Row(
                    Column('nom', css_class='form-group col-md-6 mb-0'),
                    Column('prenom', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
            ),
            Field(
                Row(
                    Column('date_naissance', css_class='col-md-6'),
                    Column('sexe', css_class='col-md-6 mb-0'),
                    css_class='form-row'
                ),
            ),
            Field(
                Row(
                    Column('specialite', css_class='col-md-12'),
                    css_class='form-row'
                ),
            ),
            Field(
                Row(
                    Column('type_exercice', css_class='col-md-12'),
                    css_class='form-row'
                ),
            ),
            Field(
                Row(
                    Column('mobile', css_class='col-md-12'),
                    css_class='form-row'
                ),
            ),
            Field('email', css_class="col-md-12 center-block"),
            Field('card', css_class="col-md-12 center-block"),
            HTML("<button type='submit' name='submit' class='btn btn-primary btn btn-etabib'>"
                 "<i class='fa fa-send'></i>" + str(btn_str) + "</button>")
        )

    def save(self, commit=True):
        contact = super(SignupFormWorkspace, self).save(commit=False)
        with transaction.atomic():
            user = User()
            password = User.objects.make_random_password()
            contact.mdp_genere = password
            user.set_password(password)
            user.username = contact.email
            user.email = contact.email
            contact.save()
            user.save()
            user.groups.add(Group.objects.get(name=Role.VISITOR.value))
            email_add = EmailAddress()
            email_add.user = user
            email_add.primary = True
            email_add.verified = True
            email_add.email = contact.email
            email_add.save()
            try:
                carte = CarteProfessionnelle.objects.get(pk=self.cleaned_data['card'])
            except CarteProfessionnelle.DoesNotExist:
                carte = None
            pro = ProfessionnelSante()
            pro.user = user
            pro.contact = contact
            pro.carte = carte
            pro.save()
        return (user, password)


class EtabibExpoSignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.form_show_labels = False
        self.helper.form_method = 'POST'
        btn_str = _("Commander Votre e-Badge")
        self.helper.layout = Layout(
            Field('email', css_class="etabib-form-control center-block"),
            HTML("<button type='submit' style='width: 250px;' name='submit' class='btn btn-primary btn-etabib-dark'>"
                 "<i class='fa fa-id-badge'></i>" + str(btn_str) + "</button>")
        )

    def save(self):
        (user, password) = super(EtabibExpoSignupForm, self).save()
        with transaction.atomic():
            contact = Contact()
            contact.save()

            pro = ProfessionnelSante()
            pro.user = user
            pro.contact = contact
            pro.save()
            pro.user.groups.add(Group.objects.get(name=Role.VISITOR.value))
        return (user, password)


class ChangePasswordForm(forms.Form):
    """
    A form that lets a user change set their password with entering the old
    password
    """
    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
    }
    old_password = forms.CharField(
        label=_("Old password"),
        widget=forms.PasswordInput,
        strip=False,
    )
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput,
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        strip=False,
        widget=forms.PasswordInput,
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.instance = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise forms.ValidationError(_('Ancien mot de passe incorrect.'))
        return old_password

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(
                    self.error_messages['password_mismatch'],
                    code='password_mismatch',
                )
        password_validation.validate_password(password2, self.user)
        return password2

    def save(self, commit=True):
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user


class AvatarForm(forms.ModelForm):
    x = forms.FloatField(widget=forms.HiddenInput())
    y = forms.FloatField(widget=forms.HiddenInput())
    width = forms.FloatField(widget=forms.HiddenInput())
    height = forms.FloatField(widget=forms.HiddenInput())

    class Meta:
        model = Avatar
        fields = ('image', 'x', 'y', 'width', 'height',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.form_id = "avatar-form"

    def save(self):
        avatar = super(AvatarForm, self).save(commit=False)

        return avatar

    def cropImage(self, avatar):
        x = self.cleaned_data.get('x')
        y = self.cleaned_data.get('y')
        w = self.cleaned_data.get('width')
        h = self.cleaned_data.get('height')

        image = Image.open(avatar.image)
        cropped_image = image.crop((x, y, w + x, h + y))
        resized_image = cropped_image.resize((200, 200), Image.ANTIALIAS)
        resized_image.save(avatar.image.path)
        return avatar


class ProfessionalIdentityForm(forms.Form):
    nom = forms.CharField(label=_('Nom'), max_length=255)
    prenom = forms.CharField(label=_('Prénom'), max_length=255)
    mobile = forms.CharField(label=_("Numéro Téléphone (Non Publique)"), max_length=255)
    fonction = forms.CharField(label=_("Fonction"), max_length=255)
    organisme = forms.CharField(label=_("Organisme"), max_length=255)
    card = forms.CharField(
        label=_("Carte professionnelle"),
        widget=DropzoneInput(
            maxFilesize=10,
            acceptedFiles="image/*",
            paramName='image',
            placeholder=_("cliquer pour uploader une image"),
            maxFiles=1,
            upload_path='/cp-upload/'
        ),
        help_text=_("Un document attestant votre affiliation au corps médical (Carte professionnelle,\
                                    ou tout autre document")
    )

    def clean(self):
        cleaned_data = super().clean()
        card = cleaned_data.get('card')
        if not card:
            raise forms.ValidationError(_("Veuillez ajouter une carte professionnelle"))

    class Media:
        js = (VersionedMediaJS('js/dropzonee/dropzone.django.js', '2.2'),)

    def __init__(self, *args, **kwargs):
        self.professionnelsante = kwargs.pop('professionnelsante', None)
        super(ProfessionalIdentityForm, self).__init__(*args, **kwargs)
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
        mobile = self.cleaned_data['mobile']
        fonction = self.cleaned_data['fonction']
        organisme = self.cleaned_data['organisme']
        with transaction.atomic():
            self.professionnelsante.contact.nom = nom
            self.professionnelsante.contact.prenom = prenom
            self.professionnelsante.contact.mobile = mobile
            self.professionnelsante.contact.fonction = fonction
            self.professionnelsante.contact.organisme = organisme
            self.professionnelsante.user.first_name = nom
            self.professionnelsante.user.last_name = prenom
            try:
                carte = CarteProfessionnelle.objects.get(pk=self.cleaned_data['card'])
            except CarteProfessionnelle.DoesNotExist:
                carte = None
            self.professionnelsante.carte = carte

            self.professionnelsante.user.save()
            self.professionnelsante.contact.save()
            self.professionnelsante.save()
        return self.professionnelsante
