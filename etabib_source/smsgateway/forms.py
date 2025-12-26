from dal import autocomplete, forward
from django import forms
from django.utils.translation import gettext as _

from core.models import Contact
from etabibWebsite import settings
from smsgateway.models import SmsModel, Critere, Listenvoi, EmailModel


class ListenvoiCreateForm(forms.ModelForm):
    class Meta:
        model = Listenvoi
        fields = [
            'libelle',
        ]


class SmsModelCreateForm(forms.ModelForm):
    class Meta:
        model = SmsModel
        fields = [
            'libelle',
            'message'
        ]
        widgets = {
            "message": forms.Textarea()
        }


class SendSmsModelForm(forms.Form):
    SIM_NUMBER = (
        ("1", "Sim1 %s" % settings.SMS_PHONE.get("Sim1")),
        ("2", "Sim2 %s" % settings.SMS_PHONE.get("Sim2")),
    )

    smsmodel = forms.ModelChoiceField(
        label=_('Sms'),
        queryset=SmsModel.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='smsmodel-autocomplete',
            attrs={
                'data-placeholder': _('Choisir un sms...'),
                'data-html': True,
            }
        ),
    )
    sim = forms.ChoiceField(label=_('Sim'), choices=SIM_NUMBER)

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        super(SendSmsModelForm, self).__init__(*args, **kwargs)


class SendSmsForm(forms.Form):
    SIM_NUMBER = (
        ("1", "Sim1 %s" % settings.SMS_PHONE.get("Sim1")),
        ("2", "Sim2 %s" % settings.SMS_PHONE.get("Sim2")),
    )
    message = forms.CharField(label=_('Message'), max_length=160, widget=forms.Textarea())
    sim = forms.ChoiceField(label=_('Sim'), choices=SIM_NUMBER)

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        super(SendSmsForm, self).__init__(*args, **kwargs)


class SmsCritereCreateForm(forms.ModelForm):
    class Meta:
        model = Critere
        fields = [
            'libelle',
            'pays',
            'ville',
            'specialite',
            'offre',
        ]
        widgets = {
            'specialite': autocomplete.ModelSelect2(
                url='speciality-autocomplete',
                attrs={
                    'data-placeholder': _('Choisir une spécialité ...'),
                    'data-html': True,
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
                forward=['country'],
                attrs={
                    'data-placeholder': _('Choisir une ville ...'),
                    'class': "form-control",
                    'data-theme': 'bootstrap'
                }
            ),
            'offre': autocomplete.ModelSelect2(
                url='offre-prepaye-autocomplete',
                forward=(forward.Const(True, 'disable_filter'),),
                attrs={
                    'data-placeholder': _('Choisir un offre ...'),
                    'class': "form-control",
                    'data-theme': 'bootstrap'
                }
            ),
        }


class AddContactToListModelForm(forms.Form):
    listenvoie = forms.ModelChoiceField(
        label=_("Liste d'envoi"),
        queryset=Listenvoi.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='smsliste-autocomplete',
            attrs={
                'data-placeholder': _('Choisir une liste...'),
                'data-html': True,
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        super(AddContactToListModelForm, self).__init__(*args, **kwargs)


class SmsConactProblemForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = [
            'nom',
            'prenom',
            'mobile',
            'email',
        ]


class EmailModelCreateForm(forms.ModelForm):
    class Meta:
        model = EmailModel
        fields = [
            'libelle',
            'subject',
            'message'
        ]
        widgets = {
            "message": forms.Textarea()
        }


class SendEmailModelForm(forms.Form):
    emailmodel = forms.ModelChoiceField(
        label=_('Email'),
        queryset=EmailModel.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='emailmodel-autocomplete',
            attrs={
                'data-placeholder': _('Choisir un Email...'),
                'data-html': True,
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        super(SendEmailModelForm, self).__init__(*args, **kwargs)


class SendEmailForm(forms.Form):
    subject = forms.CharField(label=_("Sujet"), max_length=200)
    message = forms.CharField(label=_('Message'), widget=forms.Textarea())

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        super(SendEmailForm, self).__init__(*args, **kwargs)
