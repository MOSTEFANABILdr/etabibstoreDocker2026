from bootstrap_datepicker_plus import DateTimePickerInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Field, Fieldset, Div
from dal import autocomplete
from django import forms
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from appointements.models import DemandeRendezVous
from core.models import Patient
from core.widgets import CustomAutoCompleteWidgetSingle


class TraiterRendezVousForm(forms.ModelForm):

    def clean(self):
        cleaned_data = super().clean()
        date_rendez_vous = cleaned_data.get('date_rendez_vous')
        refusee = cleaned_data.get('refusee')
        if not date_rendez_vous and not refusee:
            raise forms.ValidationError(_("Veuillez accepter la demande ou bien la refuser"))
        if date_rendez_vous and refusee:
            raise forms.ValidationError(_("Veuillez accepter la demande ou bien la refuser"))
        if date_rendez_vous and date_rendez_vous < timezone.now():
            raise forms.ValidationError(_("Veuillez introduire une date de rendez-vous valide"))

    class Meta:
        model = DemandeRendezVous
        fields = ['date_rendez_vous', 'refusee', 'type', 'motif_refus']
        labels = {
            "refusee": _("Refuser cette demande"),
            "motif_refus": _("Motif de refus"),
            "date_rendez_vous": _("Date de rendez vous"),
            "type": _("Type de Rendez-vous")
        }
        widgets = {
            'date_rendez_vous': DateTimePickerInput(
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                    "minDate": str(timezone.now())
                }
            ),
            'motif_refus': forms.Textarea(attrs={
                'maxlength': '100',
                'rows': '3',
            }),
            'refusee': forms.CheckboxInput(attrs={'style': 'z-index:2'}),
        }

    def __init__(self, *args, **kwargs):
        self.NOT_ENOUGH_MONEY = kwargs.pop("NOT_ENOUGH_MONEY", False)
        self.hide_type = kwargs.pop("hide_type", False)
        super(TraiterRendezVousForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        title = _("Attention!")
        text1 = _("Le patient n'a pas suffisamment de crédit pour faire la téléconsultation.")
        text2 = _("Pour une téléconsultation gratuite")
        text3 = _("Fixez le rendez-vous.")
        html = '<div class="alert alert-warning">' + \
                                '<strong>{0}</strong> {1}' \
                                '<ul>' \
                                '<li>{2}, <strong>{3}</strong></li>' \
                                '</ul>' \
                                '</div>'
        self.helper.layout = Layout(
            HTML(
                html.format(
                    title,
                    text1, text2, text3
                )
            ) if self.NOT_ENOUGH_MONEY else HTML(''),
            Fieldset("Fixer un rendez-vous",
                     'type',
                     'date_rendez_vous',
                     ),
            Fieldset(str(_("Ou")),
                     'refusee',
                     'motif_refus',
                     ),
        )
        if self.hide_type:
            self.fields['type'].required = False
            self.fields['type'].widget.attrs['disabled'] = 'disabled'


class CreateAppointmentForm(forms.ModelForm):
    patient = forms.ModelChoiceField(
        label=_('Patient'),
        queryset=Patient.objects.all(),
        widget=CustomAutoCompleteWidgetSingle(
            url='recently-patient-autocomplete',
            attrs={
                'data-placeholder': _('Choisir une patient ...'),
            }
        ),
    )

    class Meta:
        model = DemandeRendezVous
        fields = ['patient', 'date_rendez_vous', ]
        labels = {
            "date_rendez_vous": _("Date de rendez vous"),
        }
        widgets = {
            'date_rendez_vous': DateTimePickerInput(
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                    "minDate": str(timezone.now())
                }
            ),
        }
        extra_required = (
            'patient',
            'date_rendez_vous'
        )

    def clean(self):
        cleaned_data = super().clean()
        date_rendez_vous = cleaned_data.get('date_rendez_vous')
        if date_rendez_vous and date_rendez_vous < timezone.now():
            raise forms.ValidationError(_("Veuillez introduire une date de rendez-vous valide"))

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        super(CreateAppointmentForm, self).__init__(*args, **kwargs)
        for field in self.Meta.extra_required:
            self.fields[field].required = True


class RendezVousDoctorCreateFormStep1(forms.ModelForm):
    class Meta:
        model = DemandeRendezVous
        fields = ['type', ]

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        super().__init__(*args, **kwargs)
        self.helper.form_id = "rdvform1"
        self.fields['type'].required = False


class RendezVousDoctorCreateFormStep2(forms.ModelForm):
    class Meta:
        model = DemandeRendezVous
        fields = ['lettre_orientation', ]

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        super().__init__(*args, **kwargs)
        self.helper.form_id = "rdvform2"
