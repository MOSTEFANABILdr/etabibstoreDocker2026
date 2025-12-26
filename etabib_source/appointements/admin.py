from dal import autocomplete
from django import forms
from django.contrib import admin

from appointements.models import DemandeRendezVous, LettreOrientation


class DemandeRendezVousForm(forms.ModelForm):
    class Meta:
        model = DemandeRendezVous
        # exclude = ['zones']
        fields = "__all__"
        widgets = {
            "demandeur": autocomplete.ModelSelect2(url='user-autocomplete', ),
            "destinataire": autocomplete.ModelSelect2(url='user-autocomplete', ),
        }

    class Media:
        js = [
            "admin/js/vendor/jquery/jquery.js",
            "autocomplete_light/jquery.init.js",
            "vendor/select2/dist/js/select2.full.js",
            "admin/js/vendor/select2/select2.full.js",
        ]


class DemandeRendezVousAdmin(admin.ModelAdmin):
    form = DemandeRendezVousForm
    list_display = ("id", "demandeur", "destinataire", "type", "acceptee", "refusee", "date_creation")


admin.site.register(DemandeRendezVous, DemandeRendezVousAdmin)
admin.site.register(LettreOrientation)
