# -*- coding: utf-8 -*-
from bootstrap_datepicker_plus import DatePickerInput
from cities_light.models import City
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from dal import autocomplete, forward
from django import forms
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _

from core.enums import Role
from core.models import Patient, Specialite
from crm.models import Ville
from drugs.models import DciAtc


class PatientRegistrationForm(forms.ModelForm):
    nom = forms.CharField(label=_('Nom'), max_length=255)
    prenom = forms.CharField(label=_('Prénom'), max_length=255)

    class Meta:
        model = Patient
        fields = ['nom', 'prenom', 'date_naissance', 'sexe', 'telephone']
        widgets = {
            'date_naissance': DatePickerInput(
                format="%Y-%m-%d",
                options={
                    "locale": "fr",
                    "showClose": True,
                    "showClear": True,
                    "showTodayButton": True,
                }
            ),
        }
        extra_required = (
            'telephone',
        )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        if self.user:
            kwargs.update(initial={
                'nom': self.user.first_name,
                'prenom': self.user.last_name
            })
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.add_input(Submit('submit', _("S'inscrire"), css_class='btn btn-etabib btn-block'))
        self.helper.form_method = 'POST'
        super(PatientRegistrationForm, self).__init__(*args, **kwargs)
        for field in self.Meta.extra_required:
            self.fields[field].required = True

    def save(self, commit=True):
        patient = super(PatientRegistrationForm, self).save(commit=False)
        patient.user = self.user
        patient.user.first_name = self.cleaned_data['nom']
        patient.user.last_name = self.cleaned_data['prenom']
        if patient.user.groups.count() == 0:
            patient.user.groups.add(Group.objects.get(name=Role.PATIENT.value))

        if commit:
            patient.user.save()
            patient.save()
        return patient


class PatientProfileForm(PatientRegistrationForm):
    class Meta:
        model = Patient
        fields = ['nom', 'prenom', 'date_naissance', 'sexe', 'telephone', 'pays', 'ville']
        widgets = {
            'date_naissance': forms.DateInput(attrs={'type': 'date'}),
            'pays': autocomplete.ModelSelect2(
                url='country-autocomplete',
                attrs={
                    'data-placeholder': _('Choisir un pays ...'),
                }
            ),
            'ville': autocomplete.ModelSelect2(
                url='city-autocomplete',
                forward=(forward.Field('pays', 'country'),),
                attrs={
                    'data-placeholder': _('Choisir une ville ...'),
                }
            )
        }
        extra_required = (
            'telephone',
        )

    def __init__(self, *args, **kwargs):
        super(PatientProfileForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.add_input(Submit('submit', _("Mettre à jour"), css_class='btn btn-etabib btn-block'))
        self.helper.form_method = 'POST'


class DciForm(forms.Form):
    dci = forms.ModelChoiceField(
        queryset=DciAtc.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='dci-autocomplete',
            attrs={
                'data-html': True,
                'id': 'allergyinput',
                'class': "form-control",
                'data-placeholder': _('Tapez une allergie...'),
            }
        )
    )


class AdvancedSearchForm(forms.Form):
    specialite_q = forms.ModelChoiceField(
        label=_('Spécialité'),
        required=False,
        queryset=Specialite.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='speciality-autocomplete',
            attrs={
                'data-placeholder': _('Choisir une spécialité ...'),
                'data-html': True,
                'class': "form-control f-s-12 adv-search-input",
            }
        ),
    )

    city_q = forms.ModelChoiceField(
        label=_('Ville'),
        required=False,
        queryset=Ville.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='ville-autocomplete',
            attrs={
                'data-placeholder': _('Choisir une ville ...'),
                'class': "form-control f-s-12 adv-search-input",
                'data-theme': 'bootstrap'
            }
        ),
    )