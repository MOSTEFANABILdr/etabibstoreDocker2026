from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from stats.models import AtcdciStats, NomComercialStats


class AtcdciStatsAdmin(admin.ModelAdmin):
    list_display = ('id', 'atcdci', 'poste', 'date_insertion')
    search_fields = ['atcdci__designation_fr', 'poste__libelle']


class AtcdciStatsIEAdmin(AtcdciStatsAdmin, ImportExportModelAdmin):
    pass


class NomComercialStatsAdmin(admin.ModelAdmin):
    list_display = ('id', 'nomCommercial', 'poste', 'date_insertion')
    search_fields = ['nomCommercial__nom_fr', 'poste__libelle']


class NomComercialStatsIEAdmin(NomComercialStatsAdmin, ImportExportModelAdmin):
    pass


admin.site.register(AtcdciStats, AtcdciStatsIEAdmin)
admin.site.register(NomComercialStats, NomComercialStatsIEAdmin)