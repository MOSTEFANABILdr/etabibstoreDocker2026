from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from nomenclature.models import Links, Motif, SnomedD, SnomedF, SnomedP, Dictionary, MotifCategorie, LOINC, \
    PanelsAndForms, LoincAnswerListLink, AnswerList, FR18LinguisticVariant, NABM, NABM_LOINC


class LinksAdmin(admin.ModelAdmin):
    list_display = ('id', 'motif', 'snomed_d', 'snomed_f', 'snomed_p')


class LinksIEAdmin(LinksAdmin, ImportExportModelAdmin):
    pass


class MotifAdmin(admin.ModelAdmin):
    list_display = ('id', 'code_class',  'name_class', 'version_class', 'abrev', 'motif', 'motif_en', 'motif_ar', 'motif_es', 'definition', 'categorie', 'code_map', 'map_to', 'active')
    search_fields = ['motif', 'definition', 'categorie__designation', 'motif_en', 'motif_ar', 'motif_es', 'code_map', 'map_to']


class MotifIEAdmin(MotifAdmin, ImportExportModelAdmin):
    pass


class SnomedDAdmin(admin.ModelAdmin):
    list_display = (
    'id', 'termcode', 'fmod', 'fclass', 'fnomen', 'reference', 'icdcode', 'icd10', 'icd10_e', 'icdref', 'sno2')
    search_fields = ['termcode', 'fnomen']


class SnomedDIEAdmin(SnomedDAdmin, ImportExportModelAdmin):
    pass


class SnomedFAdmin(admin.ModelAdmin):
    list_display = (
    'id', 'termcode', 'fmod', 'fclass', 'fnomen', 'reference', 'icdcode', 'icd10', 'icd10_e', 'iub', 'sno2')
    search_fields = ['termcode']


class SnomedFIEAdmin(SnomedFAdmin, ImportExportModelAdmin):
    pass


class SnomedPAdmin(admin.ModelAdmin):
    list_display = ('id', 'termcode', 'fmod', 'fclass', 'fnomen', 'reference', 'icdcode', 'sno2')
    search_fields = ['termcode']


class SnomedPIEAdmin(SnomedPAdmin, ImportExportModelAdmin):
    pass


class DictionaryAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Dictionary._meta.get_fields()]
    search_fields = ['termcode']


class DictionaryIEAdmin(DictionaryAdmin, ImportExportModelAdmin):
    pass



class MotifCategorieAdmin(admin.ModelAdmin):
    list_display = ('id', 'designation')


class MotifCategorieIEAdmin(MotifCategorieAdmin, ImportExportModelAdmin):
    pass

@admin.register(LOINC, PanelsAndForms, LoincAnswerListLink, AnswerList, FR18LinguisticVariant, NABM, NABM_LOINC)
class NomenclatureAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        return [field.name for field in self.model._meta.concrete_fields]

    def get_search_fields(self, request):
        return [field.name for field in self.model._meta.concrete_fields]

admin.site.register(Links, LinksIEAdmin)
admin.site.register(Motif, MotifIEAdmin)
admin.site.register(SnomedD, SnomedDIEAdmin)
admin.site.register(SnomedF, SnomedFIEAdmin)
admin.site.register(SnomedP, SnomedPIEAdmin)
admin.site.register(Dictionary, DictionaryIEAdmin)
admin.site.register(MotifCategorie, MotifCategorieIEAdmin)
