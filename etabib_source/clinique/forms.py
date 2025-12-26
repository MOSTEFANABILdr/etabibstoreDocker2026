from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Div, Field, HTML, Fieldset, Button
from django import forms
from bootstrap_datepicker_plus import DateTimePickerInput
from django.forms import ModelForm, Textarea
from django.utils.translation import ugettext_lazy as _
from location_field.forms.plain import PlainLocationField

from appointements.models import DemandeRendezVous
from clinique.models import CliniqueVirtuelleImage, Document, Consultation
from core.models import CarteID, Certificat


class CliniqueVirtuelleImageForm(forms.ModelForm):
    class Meta:
        model = CliniqueVirtuelleImage
        fields = ('image',)


class DocumentForm(ModelForm):
    date_ajout = forms.DateTimeField(label=_("Date"), widget=DateTimePickerInput(
        options={
            "locale": "fr",
            "defaultDate": "now",
            "showClose": True,
            "showClear": True,
            "showTodayButton": True,
        }
    ))

    class Meta:
        model = Document
        fields = ["titre", "description", "date_ajout", "fichier"]
        required = (
            'titre',
            'fichier',
            'date_ajout'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.Meta.required:
            self.fields[field].required = True


class ConsultationForm(ModelForm):
    date_ajout = forms.DateTimeField(label=_("Date"), widget=DateTimePickerInput(
        options={
            "locale": "fr",
            "defaultDate": "now",
            "showClose": True,
            "showClear": True,
            "showTodayButton": True,
        }
    ))

    class Meta:
        model = Consultation
        exclude = ["operateur", ]
        labels = {
            "motif": _("Motif De Consultation"),
            "conduite_tenir": _("Conduite à tenir/ Résultat de Consultation"),
            "diag_retenu": _("Dtic. Retenu(s)"),
            "diag_suppose": _("Hypothèses Dtic."),
            "interrogatoire": _("Données De L'interrogatoire"),
            "examen_clinique": _("Examens Cliniques"),
            "examen_demande": _("Exploration à Demander"),
            "resultat_examen": _("Conclusions Des Explorations"),
        }
        widgets = {
            'motif': Textarea(attrs={'placeholder': _("Motif De Consultation"),
                                     'rows': 4, 'class': "form-control"}),
            'conduite_tenir': Textarea(attrs={'placeholder': _("Conduite à tenir/ Résultat de Consultation"),
                                              'rows': 4, 'class': "form-control"}),
            'diag_retenu': Textarea(attrs={'placeholder': _("Dtic. Retenu(s)"), 'rows': 4,
                                           'class': "form-control"}),
            'diag_suppose': Textarea(attrs={'placeholder': _("Hypothèses Dtic."), 'rows': 4,
                                            'class': "form-control"}),
            'interrogatoire': Textarea(attrs={'placeholder': _("Données De L'interrogatoire"), 'rows': 4,
                                              'class': "form-control"}),
            'examen_clinique': Textarea(attrs={'placeholder': _("Examens Cliniques"), 'rows': 4,
                                               'class': "form-control"}),
            'examen_demande': Textarea(attrs={'placeholder': _("Exploration à Demander"), 'rows': 4,
                                              'class': "form-control"}),
            'resultat_examen': Textarea(attrs={'placeholder': _("Conclusions Des Explorations"), 'rows': 4,
                                               'class': "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        hide_date_ajout = kwargs.pop('hide_date_ajout', True)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        if hide_date_ajout:
            del self.fields['date_ajout']
            self.helper.layout = Layout(
                Row(
                    Div(Field('motif'), css_class='col-lg-4'),
                    Div(Field('interrogatoire'), css_class='col-lg-4'),
                    Div(Field('diag_suppose'), css_class='col-lg-4'),
                ),
                Row(
                    Div(Field('examen_clinique'), css_class='col-lg-4'),
                    Div(Field('examen_demande'), css_class='col-lg-4'),
                    Div(Field('resultat_examen'), css_class='col-lg-4'),
                ),
                Row(
                    Div(Field('diag_retenu'), css_class='col-lg-6'),
                    Div(Field('conduite_tenir'), css_class='col-lg-6'),
                ),
            )
        else:
            self.helper.layout = Layout(
                "date_ajout",
                Row(
                    Div(Field('motif'), css_class='col-lg-6'),
                    Div(Field('interrogatoire'), css_class='col-lg-6'),
                ),
                Row(
                    Div(Field('diag_suppose'), css_class='col-lg-6'),
                    Div(Field('examen_clinique'), css_class='col-lg-6'),
                ),
                Row(
                    Div(Field('examen_demande'), css_class='col-lg-6'),
                    Div(Field('resultat_examen'), css_class='col-lg-6'),
                ),
                Row(
                    Div(Field('diag_retenu'), css_class='col-lg-6'),
                    Div(Field('conduite_tenir'), css_class='col-lg-6'),
                ),
            )


class LocationForm(forms.Form):
    gps = PlainLocationField(label=_("GPS"), based_fields=['adresse'], initial='36.7538,3.0588', zoom=5)


class RendezVousCreateForm(forms.ModelForm):
    class Meta:
        model = DemandeRendezVous
        fields = ['type', ]
        labels = {
            'type': _('اختر نوعا من هذه القائمة نوع الموعد الذي تريده'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].required = False
        self.helper = FormHelper()
        self.helper.form_id = 'lettre_form'
        self.helper.layout = Layout(
            Fieldset(
                '',
                'type',
                HTML("<h5>قم بتحميل رسالة التوجيه حتى يطَّلِع عليها الطبيب (بإمكانك تخطي هذه المرحلة)</h5>"),
                Div(css_id='div_lettres'),
            )
        )

