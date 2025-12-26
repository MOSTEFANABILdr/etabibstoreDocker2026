from django.contrib import admin
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from core.widgets import DalModelSelect2
from drugs.models import *


class DciAtcResource(resources.ModelResource):
    class Meta:
        model = DciAtc
        import_id_fields = ('unique_id',)
        export_id_fields = ('unique_id',)


class DciAtcIEAdmin(ImportExportModelAdmin):
    resource_class = DciAtcResource
    list_display = ('unique_id', 'designation_fr', 'deleted')
    search_fields = ['designation_fr', 'unique_id']


class CodeAtcResource(resources.ModelResource):
    dciAtc = fields.Field(
        column_name='dciAtc',
        attribute='dciAtc',
        widget=ForeignKeyWidget(DciAtc, 'unique_id')
    )

    class Meta:
        model = CodeAtc
        import_id_fields = ('unique_id',)
        export_id_fields = ('unique_id',)


class CodeAtcIEAdmin(ImportExportModelAdmin):
    resource_class = CodeAtcResource
    list_display = ('id', 'unique_id', 'designation', 'deleted')
    search_fields = ['unique_id', 'designation']


class FormeHomogeneIEAdmin(ImportExportModelAdmin):
    list_display = ('id', 'designation')
    search_fields = ['designation']


class InteractionIEAdmin(ImportExportModelAdmin):
    list_display = ('id', 'dci_atc_a', 'dci_atc_b', 'type_interraction')
    search_fields = ['dci_atc_a__designation_fr', 'dci_atc_b__designation_fr', 'type_interraction']


class MedicamentResource(resources.ModelResource):
    dci_atc = fields.Field(
        column_name='dci_atc',
        attribute='dci_atc',
        widget=ForeignKeyWidget(DciAtc, 'unique_id')

    )

    nom_commercial = fields.Field(
        column_name='nom_commercial',
        attribute='nom_commercial',
        widget=ForeignKeyWidget(NomCommercial, 'unique_id')

    )

    class Meta:
        model = Medicament
        import_id_fields = ('unique_id',)
        export_id_fields = ('unique_id',)


class MedicamentIEAdmin(ImportExportModelAdmin):
    resource_class = MedicamentResource
    list_display = ('unique_id', 'dci_pays', 'dci_atc', 'nom_commercial', 'forme', 'deleted')
    search_fields = ['unique_id', 'dci_pays', 'dci_atc__designation_fr', 'nom_commercial__nom_fr', 'forme']
    list_filter = ('deleted',)
    autocomplete_fields = ("dci_atc", "nom_commercial")

    def get_instance(self, instance_loader, row):
        # Utilisez la colonne "unique_id" comme valeur de test pour la mise à jour ou la création d'objets
        unique_id = row.get('unique_id')
        if unique_id:
            queryset = self.get_queryset()
            try:
                return queryset.get(unique_id=unique_id)
            except Medicament.DoesNotExist:
                pass
        return None


class NomCommercialResource(resources.ModelResource):
    class Meta:
        model = NomCommercial
        import_id_fields = ('unique_id',)
        export_id_fields = ('unique_id',)


class NomCommercialIEAdmin(ImportExportModelAdmin):
    resource_class = NomCommercialResource
    list_display = ('unique_id', 'nom_fr', 'deleted')
    search_fields = ['unique_id', 'nom_fr']
    list_filter = ("deleted",)


class MapCnasResource(resources.ModelResource):
    medicament = fields.Field(
        column_name='medicament',
        attribute='medicament',
        widget=ForeignKeyWidget(Medicament, 'unique_id')

    )
    medicamentcnas = fields.Field(
        column_name='medicamentcnas',
        attribute='medicamentcnas',
        widget=ForeignKeyWidget(MedicamentCnas, 'n_enregistrement')
    )

    class Meta:
        model = MapCnas
        fields = ('medicamentcnas__n_enregistrement', 'medicament__unique_id', "remborsable")
        import_id_fields = ('medicament',)
        export_id_fields = ('medicament',)


class MapCnasAdmin(ImportExportModelAdmin):
    resource_class = MapCnasResource
    list_display = ('id', 'get_n_enregistrement', 'get_unique_id', 'remborsable')
    search_fields = ['medicament__unique_id', 'medicamentcnas__n_enregistrement']
    list_filter = ("remborsable",)
    autocomplete_fields = ("medicament", "medicamentcnas")

    def get_n_enregistrement(self, obj):
        return obj.medicamentcnas.n_enregistrement if obj.medicamentcnas else ""

    get_n_enregistrement.short_description = 'Cnas unique Id'
    get_n_enregistrement.admin_order_field = 'medicamentcnas__n_enregistrement'

    def get_unique_id(self, obj):
        return obj.medicament.unique_id

    get_unique_id.short_description = 'Medicament unique Id'
    get_unique_id.admin_order_field = 'medicament__unique_id'


class AmmAdmin(ImportExportModelAdmin):
    list_display = ('id', 'get_medicament', 'amm', 'date_retrait', 'motif_retrait')
    search_fields = ['id', 'medicament__unique_id', 'amm']

    def get_medicament(self, obj):
        return obj.medicament.unique_id

    get_medicament.short_description = 'Medicament unique Id'
    get_medicament.admin_order_field = 'medicament__unique_id'


class MedicamentCnasFormeAdmin(ImportExportModelAdmin):
    list_display = ('id', 'code', 'libelle', 'libelle_court')
    search_fields = ['id', 'code', 'libelle', "libelle_court"]


class CnasResource(resources.ModelResource):
    fields = (
        'n_enregistrement', 'nom_commercial', 'nom_dci', 'dosage', 'conditionnement', 'remboursable',
        'tarif_de_reference',
        "forme")

    class Meta:
        model = MedicamentCnas
        import_id_fields = ('n_enregistrement',)
        export_id_fields = ('n_enregistrement',)


class MedicamentCnasAdmin(ImportExportModelAdmin):
    resource_class = CnasResource
    list_display = ('id', 'n_enregistrement', 'nom_commercial', 'nom_dci', 'dosage', 'conditionnement', 'remboursable',
                    'tarif_de_reference', "forme")
    search_fields = ['id', 'n_enregistrement', 'nom_commercial', 'nom_dci', 'dosage', 'conditionnement', 'remboursable',
                     'tarif_de_reference', "forme"]


class LaboratoireAdmin(ImportExportModelAdmin):
    list_display = ('id', 'unique_id', 'designation', 'pays')
    search_fields = ('id', 'unique_id', 'designation', 'pays')


class MapAutoriseResource(resources.ModelResource):
    medicament = fields.Field(
        column_name='medicament',
        attribute='medicament',
        widget=ForeignKeyWidget(Medicament, 'unique_id')
    )

    class Meta:
        model = MapAutorise
        fields = ('medicament', 'autorise')
        import_id_fields = ('medicament',)
        export_id_fields = ('medicament',)


class MapAutoriseAdmin(ImportExportModelAdmin):
    resource_class = MapAutoriseResource
    list_display = ('id', 'get_medicament', 'autorise')
    search_fields = ('id', 'medicament__unique_id', 'autorise')
    list_filter = ("autorise",)
    autocomplete_fields = ("medicament",)

    def get_medicament(self, obj):
        return obj.medicament.unique_id

    get_medicament.short_description = 'Medicament unique Id'
    get_medicament.admin_order_field = 'medicament__unique_id'


class ChangeLogAdmin(ImportExportModelAdmin):
    list_display = ('id', 'source', 'fields', 'date_mise_a_jour')
    search_fields = (
        'id',
        'dciatc__unique_id',
        'dciatc__designation_fr',
        'medicament__unique_id',
        'nomcommercial__unique_id',
        'nomcommercial__nom_fr',
        'mapcnas__medicament__unique_id',
        'mapautorise__medicament__unique_id',
    )
    ordering = ["-date_mise_a_jour", ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ChangeLogDrugsAdmin(ImportExportModelAdmin):
    list_display = ('id', 'query', 'date_mise_a_jour')
    search_fields = (
        'id',
        'query',
    )
    ordering = ["-date_mise_a_jour", ]

    # def has_add_permission(self, request):
    #     return False
    #
    # def has_change_permission(self, request, obj=None):
    #     return False
    #
    # def has_delete_permission(self, request, obj=None):
    #     return False


admin.site.register(DciAtc, DciAtcIEAdmin)
admin.site.register(FormeHomogene, FormeHomogeneIEAdmin)
admin.site.register(Interaction, InteractionIEAdmin)
admin.site.register(Medicament, MedicamentIEAdmin)
admin.site.register(Laboratoire, LaboratoireAdmin)
admin.site.register(CodeAtc, CodeAtcIEAdmin)
admin.site.register(MedicCategorie)
admin.site.register(NomCommercial, NomCommercialIEAdmin)
admin.site.register(MapCnas, MapCnasAdmin)
admin.site.register(Amm, AmmAdmin)
admin.site.register(MedicamentCnasForme, MedicamentCnasFormeAdmin)
admin.site.register(MedicamentCnas, MedicamentCnasAdmin)
admin.site.register(Stock)
admin.site.register(MapAutorise, MapAutoriseAdmin)
admin.site.register(ChangeLog, ChangeLogAdmin)
admin.site.register(ChangeDrugs, ChangeLogDrugsAdmin)
