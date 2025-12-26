from crispy_forms.helper import FormHelper
from dal import autocomplete
from django import forms
from django.forms import ModelForm
from django.utils.translation import ugettext_lazy as _

from core.models import Stand, PrecommandeArticle


class StandSearchForm(forms.Form):
    stand = forms.ModelChoiceField(
        label=_('Recherche'),
        queryset=Stand.objects.filter(publie=True),
        widget=autocomplete.ModelSelect2(
            url='stand-autocomplete',
            attrs={'data-placeholder': _('Rechercher...')}
        ),
    )

    def __init__(self, *args, **kwargs):
        super(StandSearchForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False


class PrecommandeForm(ModelForm):
    class Meta:
        model = PrecommandeArticle
        exclude = ["article", "cree_par", "date_creation"]
