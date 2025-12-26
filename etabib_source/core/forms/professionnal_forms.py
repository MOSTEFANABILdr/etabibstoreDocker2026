from cities_light.models import Country, City
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit
from dal import autocomplete
from django import forms
from django.utils.translation import ugettext_lazy as _
from location_field.forms.plain import PlainLocationField

from drugs.models import DciAtc


class DciAtcForm(forms.Form):
    dci = forms.ModelChoiceField(
        label=_('Recherche'),
        queryset=DciAtc.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='drugs-autocomplete',
            attrs={'data-placeholder': _('Tapez Une DCI ou un Nom Comercial')}
        ),
    )

    def __init__(self, *args, **kwargs):
        super(DciAtcForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False


class ProfileForm(forms.Form):
    nom = forms.CharField(label=_("Nom"), max_length=255)
    prenom = forms.CharField(label=_("Prénom"), max_length=255)
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
    adresse = forms.CharField(label=_("Adresse"))
    gps = PlainLocationField(label=_("GPS"), based_fields=['adresse'])

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-3'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            "nom",
            "prenom",
            'country',
            'city',
            'adresse',
            'gps',
        )
        self.helper.add_input(Submit('submit', _("Mettre à jour"), css_class='btn btn-etabib'))
        super(ProfileForm, self).__init__(*args, **kwargs)

    def save(self, commit=False):
        speaker = super(ProfileForm, self).save(commit=commit)
        nom = self.cleaned_data['nom']
        prenom = self.cleaned_data['prenom']
        speaker.user.first_name = nom
        speaker.user.last_name = prenom
        if commit:
            speaker.user.save()
            speaker.save()
        return speaker
