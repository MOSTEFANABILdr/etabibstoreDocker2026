# -*- coding: utf-8 -*-
from crispy_forms.helper import FormHelper
from dal import autocomplete, forward
from django import forms
from django.forms import formset_factory
from django.utils.translation import gettext as _

from core.models import Medecin, OffrePrepaye, PointsHistory


class ChnageOfferForm1(forms.Form):
    medecin = forms.ModelChoiceField(
        required=True,
        label=_('Médecin'),
        queryset=Medecin.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='medecin-autocomplete',
            attrs={
                'data-placeholder': _('Séléctionnez un Médecin ...'),
            }
        ),
    )
    def save(self):
        pass

class ChnageOfferForm2(forms.Form):
    offre = forms.ModelChoiceField(
        required=True,
        label=_('Offre'),
        queryset=OffrePrepaye.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='offre-prepaye-autocomplete',
            forward=(forward.Const(True, 'disable_filter'),),
            attrs={
                'data-placeholder': _('Séléctionnez une offre ...'),
            }
        ),
    )

    licence = forms.CharField(required=False, disabled=True)

    def __init__(self, *args, **kwargs):
        super(ChnageOfferForm2, self).__init__(*args, **kwargs)
        if self.initial:
            self.fields['offre'].initial = self.initial['fol'].offre
            if self.initial['fol'].licence:
                self.fields['licence'].initial = self.initial['fol'].licence.clef
            poste = None
            if hasattr(self.initial['fol'].licence, "poste"):
                poste = self.initial['fol'].licence.poste
            if self.initial['fol'].licence:
                self.fields['licence'].help_text = "Date d'activation: %s,  Poste: %s" % (
                    self.initial['fol'].licence.date_actiavtion_licence, poste
                )

    def save(self):
        offre = self.cleaned_data['offre']
        old_offre = self.initial['fol'].offre
        if offre != old_offre:
            self.initial['fol'].offre = offre
            self.initial['fol'].facture.total = offre.prix
            self.initial['fol'].facture.save()

            medecin = self.initial['fol'].facture.medecin

            medecin.points = medecin.points + offre.points - old_offre.points
            if medecin.points < 0:
                medecin.points = 0
            medecin.save()

            self.initial['fol'].save()

ChnageOfferFormSet = formset_factory(ChnageOfferForm2)


class ChangePointsForm1(forms.Form):
    medecin = forms.ModelChoiceField(
        required=True,
        label=_('Médecin'),
        queryset=Medecin.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='medecin-autocomplete',
            attrs={
                'data-placeholder': _('Séléctionnez un Médecin ...'),
            }
        ),
    )
    def save(self):
        pass


class ChangePointsForm2(forms.Form):
    points = forms.CharField(disabled=True)
    added_points = forms.IntegerField(
        label=_("Points à ajoutés"),
        help_text=_("Vous pouvez saisir des valeurs négatives ou positives")
    )
    description = forms.CharField(
        max_length="200",
        label=_("Description"),
        widget=forms.Textarea,
        help_text=_("Le médecin peut lire ce texte depuis son espace")
    )

    def __init__(self, *args, **kwargs):
        self.medecin = kwargs.pop('medecin', None)
        super(ChangePointsForm2, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-3'
        self.helper.field_class = 'col-lg-9'

    def save(self):
        if self.medecin:
            added_points = self.cleaned_data['added_points']
            description = self.cleaned_data['description']

            self.medecin.points += added_points
            ph = PointsHistory()
            ph.medecin = self.medecin
            ph.points = added_points
            ph.description = description
            ph.save()
            self.medecin.save()
