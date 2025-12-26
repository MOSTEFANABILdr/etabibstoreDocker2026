from dal import autocomplete
from django import forms
from django.contrib import admin

from clinique.models import Ordonnance, OrdonnanceMedic, CliniqueVirtuelleImage, Consultation, Document, \
    CliniqueVirtuelle


class OrdonnanceForm(forms.ModelForm):
    class Meta:
        model = Ordonnance
        exclude = ['patient']
        widgets = {
            "operateur": autocomplete.ModelSelect2(url='medecin-autocomplete', )
        }


class OrdonnanceMedicForm(forms.ModelForm):
    class Meta:
        model = OrdonnanceMedic
        exclude = ['ordonance']
        widgets = {
            "medicament": autocomplete.ModelSelect2(url='drugs-autocomplete', )
        }


class TeachSubjectInline(admin.TabularInline):
    form = OrdonnanceMedicForm
    model = OrdonnanceMedic
    extra = 2


class OrdonnanceAdmin(admin.ModelAdmin):
    inlines = (TeachSubjectInline,)
    form = OrdonnanceForm
    list_display = ("operateur", "nb_medicament", "date_creation", "date_modification")

    def nb_medicament(self, obj):
        return "%s" % (obj.medicaments.count())

    nb_medicament.short_description = 'Médicaments'


class CliniqueVirtuelleAdmin(admin.ModelAdmin):
    list_display = ("user", "titre", "description", "image", "pays", "ville")
    autocomplete_fields = ["user", "pays", "ville"]
    search_fields = ("titre", "description", "ville__name", "pays__name")


class CliniqueVirtuelleImageAdmin(admin.ModelAdmin):
    list_display = ("user", "image", "default")


class DocumentAdmin(admin.ModelAdmin):
    list_display = ("operateur", "titre", "fichier", "date_creation")
    autocomplete_fields = ("operateur",)


admin.site.register(Ordonnance, OrdonnanceAdmin)
admin.site.register(OrdonnanceMedic)
admin.site.register(CliniqueVirtuelleImage, CliniqueVirtuelleImageAdmin)
admin.site.register(CliniqueVirtuelle, CliniqueVirtuelleAdmin)
admin.site.register(Consultation)
admin.site.register(Document, DocumentAdmin)
