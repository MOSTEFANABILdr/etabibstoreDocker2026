from cities_light.admin import Region
from dal import autocomplete, forward
from django import forms
from django.utils.translation import gettext as _

from core.models import Contact, Specialite
from crm.models import Ville


class ContactGoogleSpecialiteAutocompleteForm(forms.Form):
    specialite = forms.ModelChoiceField(
        label=_(""),
        required=False,
        queryset=Specialite.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='medecin-autocomplete-gl-sp',
            attrs={
                'class': 'form-control search-input',
                'data-placeholder': _('في أي تخصص ؟'),
            }
        ),
    )

    def save(self):
        pass

class CityGoogleEmplacementAutocompleteForm(forms.Form):
    position = forms.ModelChoiceField(
        label=_(""),
        required=False,
        queryset=Ville.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='ville-autocomplete',
            attrs={
                'class': 'form-control search-input',
                'data-placeholder': _('في أي مدينة ؟'),
            },
            forward=(forward.Const(1, 'pays'),)
        ),
    )

    def save(self):
        pass
