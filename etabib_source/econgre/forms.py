import traceback

from allauth.account.models import EmailAddress
from bootstrap_datepicker_plus import DateTimePickerInput, DatePickerInput, TimePickerInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, HTML, Field, Submit
from dal import autocomplete
from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.forms import ModelForm
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import filesizeformat
from django.utils.text import slugify
from django.utils.translation import gettext as _

from core.enums import Role
from core.forms.forms import VersionedMediaJS
from ads.forms.partner_forms import CustomMoneyWidget
from core.models import Medecin, Video
from core.utils import generate_username
from dropzone.forms import DropzoneInput
from econgre.models import Congre, Webinar, CongressInvitation, Speaker, Sponsor, CongreImage, Moderateur, WebinarVideo, \
    WebinarUrl, Organisateur
from etabibWebsite import settings


class CongressForm(forms.ModelForm):
    banner_prog = forms.CharField(
        required=False,
        label=_("Affiche"),
        widget=DropzoneInput(
            maxFilesize=2,
            acceptedFiles="image/*",
            paramName='image',
            placeholder=_("cliquer pour uploader une Affiche"),
            maxFiles=1,
            width=CongreImage.IMAGE_SIZE_CHOICES[0][0],
            height=CongreImage.IMAGE_SIZE_CHOICES[0][1],
            upload_path='/econgre/congre-image-upload/'
        ),
        help_text=_("L'image doit avoir une largeur = %s px et un hauteur = %s px") %
                  (CongreImage.IMAGE_SIZE_CHOICES[0][0], CongreImage.IMAGE_SIZE_CHOICES[0][1])
    )

    sponsor_gold_logo = forms.CharField(
        required=False,
        label=_("Logo"),
        widget=DropzoneInput(
            maxFilesize=2,
            acceptedFiles="image/*",
            paramName='image',
            placeholder=_("cliquer pour uploader un logo"),
            maxFiles=1,
            width=CongreImage.IMAGE_SIZE_CHOICES[2][0],
            height=CongreImage.IMAGE_SIZE_CHOICES[2][1],
            upload_path='/econgre/congre-image-upload/'
        ),
        help_text=_("L'image doit avoir une largeur = %s px et un hauteur = %s px") %
                  (CongreImage.IMAGE_SIZE_CHOICES[2][0], CongreImage.IMAGE_SIZE_CHOICES[2][1])
    )
    sponsor_gold_banniere = forms.CharField(
        required=False,
        label=_("Bannière"),
        widget=DropzoneInput(
            maxFilesize=2,
            acceptedFiles="image/*",
            paramName='image',
            placeholder=_("cliquer pour uploader une bannière"),
            maxFiles=1,
            width=CongreImage.IMAGE_SIZE_CHOICES[1][0],
            height=CongreImage.IMAGE_SIZE_CHOICES[1][1],
            upload_path='/econgre/congre-image-upload/'
        ),
        help_text=_("L'image doit avoir une largeur = %s px et un hauteur = %s px") %
                  (CongreImage.IMAGE_SIZE_CHOICES[1][0], CongreImage.IMAGE_SIZE_CHOICES[1][1])
    )
    autre_sponsors = forms.CharField(
        required=False,
        label=_("Autre sponsors"),
        widget=DropzoneInput(
            maxFilesize=2,
            acceptedFiles="image/*",
            paramName='image',
            placeholder=_("cliquer pour uploader une image de sponsor"),
            maxFiles=8,
            width=CongreImage.IMAGE_SIZE_CHOICES[3][0],
            height=CongreImage.IMAGE_SIZE_CHOICES[3][1],
            upload_path='/econgre/congre-image-upload/'
        ),
        help_text=_("L'image doit avoir une largeur = %s px et un hauteur = %s px") %
                  (CongreImage.IMAGE_SIZE_CHOICES[3][0], CongreImage.IMAGE_SIZE_CHOICES[3][1])
    )

    banner_prog_as_json = forms.CharField(widget=forms.Textarea, required=False)
    sponsor_gold_banniere_as_json = forms.CharField(widget=forms.Textarea, required=False)
    sponsor_gold_logo_as_json = forms.CharField(widget=forms.Textarea, required=False)
    autre_sponsors_as_json = forms.CharField(widget=forms.Textarea, required=False)

    class Media:
        js = (
            VersionedMediaJS('js/dropzonee/dropzone.django.js', '2.2'),
            "js/dropzonee/jquery.cookie.js",
            "/static/js/congre.js",
        )

    class Meta:
        model = Congre
        extra_required = (
            'description',
        )
        labels = {
            "nom": _("Titre du Congrès"),
            "description": _("Thème du Congrès"),
            "adresse": _("Ajouter Une Adresse Postale de l'emplacement du congrè"),
            "emplacement": _("Coordonées GPS : (latitude..)"),
            "etablissement": _("Idiquer l'établissement abritant le congrès (Hotel..)")
        }
        exclude = ["organisateur", "slug", "publie", "archive", "annule"]
        widgets = {
            'date_debut': DateTimePickerInput(
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                }
            ),
            'date_fin': DateTimePickerInput(
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                }
            ),
            'date_limite_inscription': DateTimePickerInput(
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                }
            ),
        }

    def clean_banner_prog(self):
        banner = self.cleaned_data['banner_prog']
        if banner:
            try:
                banner = CongreImage.objects.get(id=banner)
                banner.type = CongreImage.TYPE_CHOICES[0][0]
                banner.save()
                return banner
            except Exception as e:
                traceback.print_exc()
                return None

    def clean_sponsor_gold_logo(self):
        sponsor_gold_logo = self.cleaned_data['sponsor_gold_logo']
        if sponsor_gold_logo:
            try:
                sponsor_gold_logo = CongreImage.objects.get(id=sponsor_gold_logo)
                sponsor_gold_logo.type = CongreImage.TYPE_CHOICES[2][0]
                sponsor_gold_logo.save()
                return sponsor_gold_logo
            except Exception as e:
                traceback.print_exc()
                return None

    def clean_sponsor_gold_banniere(self):
        sponsor_gold_banniere = self.cleaned_data['sponsor_gold_banniere']
        if sponsor_gold_banniere:
            try:
                sponsor_gold_banniere = CongreImage.objects.get(id=sponsor_gold_banniere)
                sponsor_gold_banniere.type = CongreImage.TYPE_CHOICES[1][0]
                sponsor_gold_banniere.save()
                return sponsor_gold_banniere
            except Exception as e:
                traceback.print_exc()
                return None

    def clean_autre_sponsors(self):
        autre_sponsors = self.cleaned_data['autre_sponsors']
        if autre_sponsors:
            sponsorsImages = set()
            for sid in autre_sponsors.split(","):
                try:
                    ci = CongreImage.objects.get(id=sid)
                    ci.type = CongreImage.TYPE_CHOICES[3][0]
                    ci.save()
                    sponsorsImages.add(ci)
                except Exception as e:
                    print("Ignored Exception")
                    print(e)
                    pass
            return sponsorsImages
        return set()

    def __init__(self, *args, **kwargs):
        super(CongressForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = False
        amount, currency = self.fields['prix'].fields
        amount.widget.attrs['class'] = "form-control"
        currency.widget.attrs['class'] = "form-control"
        self.fields['prix'].widget = CustomMoneyWidget(
            amount_widget=amount.widget, currency_widget=currency.widget
        )
        for field in self.Meta.extra_required:
            self.fields[field].required = True
        h_text = _("GéoLocalisation  Du Congrès.")
        self.helper.layout = Layout(
            'nom', 'type',
            Div(
                Div(
                    HTML("<h1>%s</h1>" % h_text),
                    css_class="col-md-12"
                ),
                Div("adresse", css_class="col-md-12"),
                Div("etablissement", css_class="col-md-12"),
                # TODO: https://www.w3schools.com/html/html5_geolocation.asp
                Div("emplacement", css_class="col-md-12"),
                css_class="row congress_location"
            ),
            'description',
            Div(
                Div("date_debut", css_class="col-md-6"),
                Div("date_fin", css_class="col-md-6"),
                css_class="row"
            ),
            Div(
                Div("date_limite_inscription", css_class="col-md-6"),
                css_class="row"
            ),
            'payant', 'prix',
            'banner_prog',
            HTML("<h1>" + _("Parain du congrès") + "</h1>"),
            "sponsor_gold_logo",
            "autre_sponsors",
            "sponsor_gold_banniere",
            Field('banner_prog_as_json', type="hidden"),
            Field('sponsor_gold_banniere_as_json', type="hidden"),
            Field('sponsor_gold_logo_as_json', type="hidden"),
            Field('autre_sponsors_as_json', type="hidden"),
        )

    def clean(self):
        cleaned_data = super().clean()
        type = cleaned_data.get('type')
        date_fin = cleaned_data.get('date_fin')
        date_debut = cleaned_data.get('date_debut')
        if date_debut and date_fin:
            if date_fin <= date_debut:
                raise forms.ValidationError(_("Veuillez entrer une date de début et une date de fin valides."))

        if type in (Congre.TYPE_CHOICES[2][0], Congre.TYPE_CHOICES[1][0]):
            adresse = cleaned_data.get('adresse')
            etablissement = cleaned_data.get('etablissement')
            if not adresse and not etablissement:
                raise forms.ValidationError(
                    _("Veuillez entrer le lieu du congrès (adresse, établissement).")
                )


class CancelCongressForm(forms.ModelForm):
    class Meta:
        model = Congre
        fields = ["id"]


class WebinarForm(forms.ModelForm):
    sponsor = forms.CharField(
        required=False,
        label=_("Sponsor"),
        widget=DropzoneInput(
            maxFilesize=2,
            acceptedFiles="image/*",
            paramName='image',
            placeholder=_("Insérer ici le visuels du Sponsor dans le format demandé"),
            maxFiles=1,
            width=Sponsor.IMAGE_SIZE_CHOICES[0][0],
            height=Sponsor.IMAGE_SIZE_CHOICES[0][1],
            upload_path='/econgre/sponsor-image-upload/'
        ),
        help_text=_("Veuillez uploader des images avec les tailles %sx%s pixel") %
                  (Sponsor.IMAGE_SIZE_CHOICES[0][0], Sponsor.IMAGE_SIZE_CHOICES[0][1])
    )
    sponsor_as_json = forms.CharField(widget=forms.Textarea, required=False)
    congre_type = forms.CharField(required=False)

    def clean_sponsor(self):
        sponsor = self.cleaned_data['sponsor']
        if sponsor:
            try:
                sponsor = Sponsor.objects.get(id=sponsor)
                return sponsor
            except Sponsor.DoesNotExist():
                return None
        return None

    class Media:
        js = (VersionedMediaJS('js/dropzonee/dropzone.django.js', '2.2'),
              "js/dropzonee/jquery.cookie.js",
              "js/webinar.js"
              )

    class Meta:
        model = Webinar
        exclude = ["moderateurs", "speakers", "annule", "congre", "slug", "salle_discussion", "mot_de_passe",
                   "publie", "archive"]
        widgets = {
            'date_debut': DatePickerInput(
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                }
            ),
            'heure_debut': TimePickerInput(
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                }
            ),
            'heure_fin': TimePickerInput(
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                }
            ),
            'date_diffustion': DatePickerInput(
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                }
            ),
            'heure_debut_diffusion': TimePickerInput(
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                }
            ),
            'heure_fin_diffusion': TimePickerInput(
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                }
            ),
        }

        required = (
            'nom',
            'description',
            'date_debut',
            'heure_debut',
            'heure_fin',
            'nb_max_participant',
        )
        labels = {
            "nom": _("Titre de la Session"),
            "description": _("Thèmatique"),
        }
        help_texts = {
            'description': _("Insérer ici la thèmatique qu'aborde votre session (sans le nom du Speaker)")
        }

    def __init__(self, *args, **kwargs):
        self.congre = kwargs.pop('congre')
        super().__init__(*args, **kwargs)
        for field in self.Meta.required:
            self.fields[field].required = True
        self.fields["congre_type"].initial = self.congre.type  # used to hide some fields using webinar.js
        self.helper = FormHelper()
        self.helper.include_media = False
        update = True if self.instance.pk else False
        if update:
            h_text = _("Modifiez Les informations relatives à la session puis cliquer sur Mettre à jour.")
        else:
            h_text = _("Ajouter Les informations relatives à la session puis cliquer sur Ok.")

        self.helper.layout = Layout(
            HTML("<p>%s</p>" % h_text),
            'nom',
            'type',
            'description',
            Div(
                Div('date_debut', css_class='col-lg-6'),
                Div('heure_debut', css_class='col-lg-3'),
                Div('heure_fin', css_class='col-lg-3'),
                css_class='row'
            ),
            Div(
                Div(
                    'salle_physique',
                    css_class="col-md-12"
                ), css_class='row webinar_location'
            ),
            Div(
                Div(
                    HTML("<h1>%s</h1>" % _("Diffusion en ligne le:")),
                    css_class="col-md-12"
                ),
                Div('date_diffustion', css_class='col-lg-6'),
                Div('heure_debut_diffusion', css_class='col-lg-3'),
                Div('heure_fin_diffusion', css_class='col-lg-3'),
                css_class='row webinar_diffusion_date'
            ),
            'nb_max_participant',
            'sponsor',
            Field('sponsor_as_json', type="hidden"),
            Field('congre_type', type="hidden"),
        )

    def clean(self):
        cleaned_data = super(WebinarForm, self).clean()
        date_debut = cleaned_data.get("date_debut")
        heure_fin = cleaned_data.get("heure_fin")
        heure_debut = cleaned_data.get("heure_debut")
        if date_debut and heure_debut and heure_fin:
            if date_debut < self.congre.date_debut.date() or date_debut > self.congre.date_fin.date():
                raise forms.ValidationError(_("Veuillez entrer une date de début valide."))
            if heure_fin < heure_debut:
                raise forms.ValidationError(_("Veuillez entrer une heure de début et de fin valides."))

        if self.congre.type == Congre.TYPE_CHOICES[2][0]:
            date_diffustion = cleaned_data.get("date_diffustion")
            heure_debut_diffusion = cleaned_data.get("heure_debut_diffusion")
            heure_fin_diffusion = cleaned_data.get("heure_fin_diffusion")

            if heure_debut_diffusion and heure_fin_diffusion:
                if heure_fin_diffusion <= heure_debut_diffusion:
                    raise forms.ValidationError(
                        _("Veuillez entrer une heure de début de diffusion et de fin de diffusion valides."))


class PublishWebinarForm(forms.ModelForm):
    class Meta:
        model = Webinar
        fields = ["id"]


class SendInvitationsForm(forms.ModelForm):
    emails = forms.CharField(
        widget=forms.Textarea(attrs={'cols': 80, 'rows': 30}),
        help_text=_("liste des e-mails séparés par une virgule")
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'cols': 80, 'rows': 30}),
    )

    def clean_emails(self):
        emails = self.cleaned_data['emails']
        emails = emails.split(',')
        for email in emails:
            try:
                validate_email(email)
            except ValidationError:
                raise forms.ValidationError(_('Saisissez des adresses email valables.'))
        return self.cleaned_data['emails']

    class Meta:
        model = CongressInvitation
        fields = ['emails', 'message']

    def __init__(self, *args, **kwargs):
        self.congre = kwargs.pop('congre')
        super(SendInvitationsForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        emails = self.cleaned_data['emails']
        message = self.cleaned_data['message']
        emails = emails.split(',')
        cis = []
        for email in emails:
            # if this email exists in the database don't  send an invitation
            # Add the doctor to
            invitations = CongressInvitation.objects.filter(
                email=email, congre=self.congre
            )
            medecins = Medecin.objects.filter(user__email=email)
            if invitations.exists():
                pass
            elif medecins.exists():
                ci = CongressInvitation()
                ci.email = email
                ci.message = message
                ci.accepted = True
                cis.append(ci)
            else:
                ci = CongressInvitation()
                ci.email = email
                ci.message = message
                cis.append(ci)
        return cis


class SponsorImageUploadForm(forms.Form):
    image = forms.ImageField()

    def clean_image(self):
        content = self.cleaned_data['image']
        if content.size > settings.ECONGRE_SPONSOR_IMAGE_SIZE * 1024 * 1024:
            raise forms.ValidationError(
                _('Please keep filesize under %s. Current filesize %s') % (
                    filesizeformat(settings.ECONGRE_SPONSOR_IMAGE_SIZE * 1024 * 1024),
                    filesizeformat(content.size)
                )
            )
        return self.cleaned_data['image']

    def save(self):
        pi = Sponsor()
        pi.image = self.cleaned_data['image']
        pi.save()
        return pi


class CongreImageUploadForm(forms.Form):
    image = forms.ImageField()

    def clean_image(self):
        content = self.cleaned_data['image']
        if content.size > settings.ECONGRE_IMAGE_SIZE * 1024 * 1024:
            raise forms.ValidationError(
                _('Please keep filesize under %s. Current filesize %s') % (
                    filesizeformat(settings.ECONGRE_IMAGE_SIZE * 1024 * 1024),
                    filesizeformat(content.size)
                )
            )
        return self.cleaned_data['image']

    def save(self):
        pi = CongreImage()
        pi.image = self.cleaned_data['image']
        pi.save()
        return pi


class SpeakerForm(forms.ModelForm):
    speaker = forms.ModelChoiceField(
        required=False,
        label='',
        queryset=Speaker.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='speaker-autocomplete',
            attrs={
                'data-html': True
            }
        ),
        help_text=_("Recherchez par le nom ou le prénom")
    )
    nom = forms.CharField(required=False, label=_('Nom'), max_length=255, widget=forms.TextInput(attrs={
        'placeholder': _("Nom")
    }))
    prenom = forms.CharField(required=False, label=_('Prénom'), max_length=255, widget=forms.TextInput(attrs={
        'placeholder': _("Prénom")
    }))
    qualification = forms.CharField(required=False, label=_('Qualification'), max_length=255,
                                    help_text=_(
                                        "Inserer ici les qualificatifs du Speaker tel que vous voulez qu'elle apparaissent en bas du titre de la session"),
                                    widget=forms.TextInput(attrs={
                                        'placeholder': _("Qualification")
                                    }))
    email = forms.EmailField(required=False, label=_('Email'), )
    mot_de_passe = forms.CharField(
        required=False, label=_('Mot de passe'),
        widget=forms.PasswordInput(),
        validators=[validate_password]
    )
    confirmation_mot_de_passe = forms.CharField(
        required=False, label=_('Confirmation mot de passe'),
        widget=forms.PasswordInput(),
        help_text=_("Enter the same password as before, for verification.")
    )

    class Meta:
        model = Speaker
        fields = []

    def clean(self):
        cleaned_data = super(SpeakerForm, self).clean()
        speaker = cleaned_data.get("speaker")
        nom = cleaned_data.get('nom')
        confirmation_mot_de_passe = cleaned_data.get('confirmation_mot_de_passe')
        mot_de_passe = cleaned_data.get('mot_de_passe')
        prenom = cleaned_data.get('prenom')
        email = cleaned_data.get('email')
        qualification = cleaned_data.get('qualification')
        if not speaker:
            if not nom:
                raise forms.ValidationError(
                    "Nom est un champ est oblogatoire"
                )
            if not prenom:
                raise forms.ValidationError(
                    "Prénom est un champ est oblogatoire"
                )
            if not email:
                raise forms.ValidationError(
                    "Email est un champ est oblogatoire"
                )
            if not mot_de_passe:
                raise forms.ValidationError(
                    "Mot de passe est un champ est oblogatoire"
                )
            if not confirmation_mot_de_passe:
                raise forms.ValidationError(
                    "Confirmation de Mot de passe est un champ est oblogatoire"
                )

            if not qualification:
                raise forms.ValidationError(
                    "Qualification est un champ est oblogatoire"
                )

            password = cleaned_data.get("mot_de_passe")
            confirm_password = cleaned_data.get("confirmation_mot_de_passe")

            if password != confirm_password:
                raise forms.ValidationError(
                    "mot de passe et confirmation mot de passe ne correspondent pas"
                )
            if email:
                if User.objects.filter(email=email).exists() or EmailAddress.objects.filter(email=email).exists():
                    raise forms.ValidationError(
                        "email déjà enregistré, utilisez un autre."
                    )
        return cleaned_data

    def __init__(self, *args, **kwargs):
        self.webinar = kwargs.pop('webinar')
        super(SpeakerForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.layout = Layout(
            HTML(
                '<h1>' + _("Recercher un intervenant déjà inscrit comme speaker sur eTabib.") + '</h1>'
            ),
            'speaker',
            HTML(
                '<hr>'
            ),
            HTML(
                '<h1>Ou créez-en un nouveau.</h1>' +
                '<p>' +
                _(
                    "Ajouter une personnalité Comme Speaker sur eTabib (fournir une Nouvelle adresse e-mail jamais inscrite sur le système)") +
                '</p>'
            ),
            Div(
                Div('nom', css_class='col-lg-6'),
                Div('prenom', css_class='col-lg-6'),
                css_class='row'
            ),
            "email",
            Div(
                Div('mot_de_passe', css_class='col-lg-6'),
                Div('confirmation_mot_de_passe', css_class='col-lg-6'),
                css_class='row'
            ),
            "qualification"
        )

    def save(self, commit=True):
        speaker = self.cleaned_data['speaker']
        if not speaker:
            nom = self.cleaned_data['nom']
            prenom = self.cleaned_data['prenom']
            email = self.cleaned_data['email']
            qualification = self.cleaned_data['qualification']
            mot_de_passe = self.cleaned_data['mot_de_passe']

            speaker = Speaker()
            speaker.qualification = qualification

            user = User()
            user.first_name = nom
            user.last_name = prenom
            user.email = email
            user.set_password(mot_de_passe)
            user.username = generate_username(slugify(user.first_name, allow_unicode=True), slugify(user.last_name, allow_unicode=True))
            speaker.user = user
            if commit:
                user.save()

                mail = EmailAddress()
                mail.user = user
                mail.primary = True
                mail.verified = True
                mail.email = email
                mail.save()

                group = Group.objects.get(name=Role.SPEAKER.value)
                user.groups.add(group)

                speaker.user = user
                speaker.save()
        return speaker


class ModerateurForm(forms.ModelForm):
    moderateur = forms.ModelChoiceField(
        required=False,
        label='',
        queryset=Moderateur.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='moderateur-autocomplete',
            attrs={
                'data-html': True
            }
        ),
        help_text=_("Recherchez par le nom ou le prénom")
    )
    nom = forms.CharField(required=False, label=_('Nom'), max_length=255, widget=forms.TextInput(attrs={
        'placeholder': _("Nom")
    }))
    prenom = forms.CharField(required=False, label=_('Prénom'), max_length=255, widget=forms.TextInput(attrs={
        'placeholder': _("Prénom")
    }))
    email = forms.EmailField(required=False, label=_('Email'), )
    mot_de_passe = forms.CharField(
        required=False, label=_('Mot de passe'),
        widget=forms.PasswordInput(),
        validators=[validate_password]
    )
    confirmation_mot_de_passe = forms.CharField(
        required=False, label=_('Confirmation mot de passe'),
        widget=forms.PasswordInput(),
        help_text=_("Enter the same password as before, for verification.")
    )

    class Meta:
        model = Moderateur
        fields = []

    def clean(self):
        cleaned_data = super(ModerateurForm, self).clean()
        moderateur = cleaned_data.get("moderateur")
        nom = cleaned_data.get('nom')
        confirmation_mot_de_passe = cleaned_data.get('confirmation_mot_de_passe')
        mot_de_passe = cleaned_data.get('mot_de_passe')
        prenom = cleaned_data.get('prenom')
        email = cleaned_data.get('email')
        if not moderateur:
            if not nom:
                raise forms.ValidationError(
                    "Nom est un champ est oblogatoire"
                )
            if not prenom:
                raise forms.ValidationError(
                    "Prénom est un champ est oblogatoire"
                )
            if not email:
                raise forms.ValidationError(
                    "Email est un champ est oblogatoire"
                )
            if not mot_de_passe:
                raise forms.ValidationError(
                    "Mot de passe est un champ est oblogatoire"
                )
            if not confirmation_mot_de_passe:
                raise forms.ValidationError(
                    "Confirmation de Mot de passe est un champ est oblogatoire"
                )

            password = cleaned_data.get("mot_de_passe")
            confirm_password = cleaned_data.get("confirmation_mot_de_passe")

            if password != confirm_password:
                raise forms.ValidationError(
                    "mot de passe et confirmation mot de passe ne correspondent pas"
                )
            if email:
                if User.objects.filter(email=email).exists() or EmailAddress.objects.filter(email=email).exists():
                    raise forms.ValidationError(
                        "email déjà enregistré, utilisez un autre."
                    )
        return cleaned_data

    def __init__(self, *args, **kwargs):
        self.webinar = kwargs.pop('webinar')
        super(ModerateurForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.layout = Layout(
            HTML(
                '<h1>' + _("Recercher un modérateur déjà inscrit sur eTabib.") + '</h1>'
            ),
            'moderateur',
            HTML(
                '<hr>'
            ),
            HTML(
                '<h1>Ou créez-en un nouveau.</h1>' +
                '<p>' +
                _(
                    "Ajouter une personnalité Comme modérateur sur eTabib (fournir une Nouvelle adresse e-mail jamais inscrite sur le système)") +
                '</p>'
            ),
            Div(
                Div('nom', css_class='col-lg-6'),
                Div('prenom', css_class='col-lg-6'),
                css_class='row'
            ),
            "email",
            Div(
                Div('mot_de_passe', css_class='col-lg-6'),
                Div('confirmation_mot_de_passe', css_class='col-lg-6'),
                css_class='row'
            ),
        )

    def save(self, commit=True):
        moderateur = self.cleaned_data['moderateur']
        if not moderateur:
            nom = self.cleaned_data['nom']
            prenom = self.cleaned_data['prenom']
            email = self.cleaned_data['email']
            mot_de_passe = self.cleaned_data['mot_de_passe']

            moderateur = Moderateur()

            user = User()
            user.first_name = nom
            user.last_name = prenom
            user.email = email
            user.set_password(mot_de_passe)
            user.username = generate_username(slugify(user.first_name, allow_unicode=True),
                                              slugify(user.last_name, allow_unicode=True))
            moderateur.user = user
            if commit:
                user.save()

                mail = EmailAddress()
                mail.user = user
                mail.primary = True
                mail.verified = True
                mail.email = email
                mail.save()

                group = Group.objects.get(name=Role.MODERATOR.value)
                user.groups.add(group)

                moderateur.user = user
                moderateur.save()
        return moderateur


class SpeakerProfileForm(forms.ModelForm):
    nom = forms.CharField(max_length=255)
    prenom = forms.CharField(max_length=255)

    class Meta:
        model = Speaker
        fields = ['qualification']

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-3'
        self.helper.field_class = 'col-lg-9'
        self.helper.layout = Layout(
            "nom",
            "prenom",
            'qualification',
        )
        self.helper.add_input(Submit('submit', _("Mettre à jour"), css_class='btn btn-etabib'))
        super(SpeakerProfileForm, self).__init__(*args, **kwargs)

    def save(self, commit=False):
        speaker = super(SpeakerProfileForm, self).save(commit=commit)
        nom = self.cleaned_data['nom']
        prenom = self.cleaned_data['prenom']
        speaker.user.first_name = nom
        speaker.user.last_name = prenom
        if commit:
            speaker.user.save()
            speaker.save()
        return speaker


class OrganizerProfileForm(forms.ModelForm):
    nom = forms.CharField(max_length=255)
    prenom = forms.CharField(max_length=255)

    class Meta:
        model = Organisateur
        exclude = ["points", "user"]

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-3'
        self.helper.field_class = 'col-lg-9'
        self.helper.layout = Layout(
            "nom",
            "prenom",
            "profession",
        )
        self.helper.add_input(Submit('submit', _("Mettre à jour"), css_class='btn btn-etabib'))
        super(OrganizerProfileForm, self).__init__(*args, **kwargs)

    def save(self, commit=False):
        organisateur = super(OrganizerProfileForm, self).save(commit=commit)
        nom = self.cleaned_data['nom']
        prenom = self.cleaned_data['prenom']
        organisateur.user.first_name = nom
        organisateur.user.last_name = prenom
        if commit:
            organisateur.user.save()
            organisateur.save()
        return organisateur


class WebinarVideoForm(ModelForm):
    _video = forms.CharField(
        required=True,
        label=_("Video"),
        widget=DropzoneInput(
            maxFilesize=settings.ADS_MAX_VIDEO_SIZE,
            acceptedFiles="video/*",
            maxDuration=settings.CONGRE_VIDEO_DURATION,  # in seconds
            paramName='video',
            placeholder=_("cliquer pour uploader une video"),
            maxFiles=1,
            upload_path='/annonce-video-upload/'
        ),
        help_text=_("ajouter une vidéo de durée max de %s secondes "
                    "en suivant les Règles relatives aux Contenues"
                    " comme apparissant sur le <a id='tos' href='#'>lien</a>. La Vidéo sera "
                    "soumise à une validation avant publication." % settings.CONGRE_VIDEO_DURATION
                    ),
    )

    class Meta:
        model = WebinarVideo
        fields = ('_video',)

    class Media:
        js = (
            VersionedMediaJS('js/dropzonee/dropzone.django.js', '2.2'),
            "js/dropzonee/jquery.cookie.js",
            VersionedMediaJS('js/congre.js', '1.0')
        )

    def __init__(self, *args, **kwargs):
        super(WebinarVideoForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.layout = Layout(
            # audio element used to calculate duration of the video before uploading it to the server
            '_video', HTML("<audio id='audio'></audio")
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


class CancelWebinarVideoForm(ModelForm):
    class Meta:
        model = WebinarVideo
        fields = ('id',)


class WebinarUrlForm(ModelForm):
    class Meta:
        model = WebinarUrl
        fields = ('libelle', 'url')

    def __init__(self, *args, **kwargs):
        super(WebinarUrlForm, self).__init__(*args, **kwargs)
