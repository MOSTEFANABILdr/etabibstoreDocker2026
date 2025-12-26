from captcha.fields import CaptchaField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML
from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from core.models import Virement


class EpaymentForm(forms.Form):
    montant = forms.IntegerField(
        label="", required=False,
        widget=forms.NumberInput(attrs={'placeholder': 'DZD'})
    )
    agree = forms.BooleanField(
        required=True, widget=forms.CheckboxInput()
    )
    mode_paiement = forms.ChoiceField(
        label="",
        choices=[
            ("1", mark_safe('<img width="100" height="120" src="/static/img/icone-dahabia.png" alt="">')),
        ],
        widget=forms.RadioSelect(attrs={'required': 'true'}),
        initial="1"
    )
    montant_select = forms.ChoiceField(
        label="",
        choices=[("10000", "100 d.a"), ("50000", "500 d.a"), ("100000", "1000 d.a"), ("150000", "1500 d.a"),
                 ("200000", "2000 d.a")],
        required=False,
        widget=forms.RadioSelect(attrs={'required': 'true'}),
    )
    captcha = CaptchaField(label="")

    montant_a_recharger = -1

    def __init__(self, *args, **kwargs):
        self.montant_is_intialised = False
        self.montant_a_payer = None
        if kwargs.get('initial', None):
            self.montant_a_payer = kwargs['initial'].get("montant", None)
            if self.montant_a_payer:
                self.montant_is_intialised = True
        super(EpaymentForm, self).__init__(*args, **kwargs)
        if self.montant_is_intialised:
            self.fields['montant'].widget.attrs['required'] = True
            self.fields['montant'].widget.attrs['disabled'] = True
            self.fields['montant_select'].widget.attrs['disabled'] = True
            self.fields['montant_select'].widget.attrs['required'] = False

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data['montant'] and not cleaned_data['montant_select']:
            forms.ValidationError("Veuillez entrer un montant valide.")
        if self.montant_is_intialised:
            self.montant_a_recharger = int(self.montant_a_payer * 100)
        else:
            if cleaned_data['montant'] is None:
                self.montant_a_recharger = cleaned_data['montant_select']
            else:
                # Centimes
                self.montant_a_recharger = cleaned_data['montant'] * 100


class SendTicketForm(forms.Form):
    email = forms.EmailField()


class DoctorVirementForm(forms.ModelForm):
    class Meta:
        model = Virement
        fields = ['montant', 'ref', "image"]
        required = (
            'montant',
            'ref',
            'image',
        )
        labels = {
            "ref": _("N° de Référence"),
            "image": _("Importez le talon")
        }

    def __init__(self, *args, **kwargs):
        self.type = kwargs.pop('type', None)
        super().__init__(*args, **kwargs)
        for field in self.Meta.required:
            self.fields[field].required = True
        htmlmsgBody = ""
        htmlmsgFooter = ""
        if self.type == "1":  # Virement postal ou bancaire
            htmlmsgBody = "<p><strong>" + str(_("Faite vos virement")) + "</strong></p>" \
                      "<p>" + str(_("AU COMPTE CCP IBN HAMZA SERVICE MICROAPPLICATIONS")) + "</p>" \
                      "<p class='blue-etabib' style='font-size:20px;font-weight: bold;'>00799999002100242460</p>" \
                      "<p>" + str(_("AU COMPTE BANCAIRE SOCIETE GENERALE IBN HAMZA SM")) + "</p>" \
                      "<p class='blue-etabib' style='font-size:20px;font-weight: bold;'>02100019113004107814</p>"
            htmlmsgFooter = "<p><small>" + str(_("L'OPERATION EST SOUMISE A LA VALIDATION D'UN ADMINISTRATEUR APRES QUE LE TRANSFERT SOIT EFFECTIF SUR NOS COMPTES")) + "</small></p>"
        elif self.type == "2":  # Virement postal ou bancaire
            htmlmsgBody = "<p>" + str(_("EFFECTUEZ LE VIREMENT AU RIP SUIVANT")) + "</p>" \
                      "<p class='blue-etabib' style='font-size:20px;font-weight: bold;'>00799999000423246029</p>" \
                      "<p>" + str(_("DECOUVREZ COMMENT FAIRE EN VIDEO")) + "</p>"\
                      "<p><a target='_blank'  href='https://youtu.be/-CLVIUscAio'>https://youtu.be/-CLVIUscAio</a></p>"
            htmlmsgFooter = "<p><small>" + str(_("L'OPERATION EST SOUMISE A LA VALIDATION D'UN ADMINISTRATEUR APRES QUE LE TRANSFERT SOIT EFFECTIF SUR NOS COMPTES")) + "</small></p>"

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML(htmlmsgBody),
            "montant",
            "ref",
            "image",
            HTML(htmlmsgFooter),
        )
