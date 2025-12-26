from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from crm.models import Commande, BordereauVersement, Pays, Wilaya, Ville


class CommandeAdmin(admin.ModelAdmin):
    list_display = ('id', 'cree_par', 'user', "offre", 'quantite', 'methode_paiement', "totalHt", "versement_initial", "traitee")
    autocomplete_fields = ["cree_par", "user"]

    def contact(self, obj):
        if obj.facture and obj.facture.medecin:
            return obj.facture.medecin.contact.full_name
        return ""

class PaysImportExportAdmin(ImportExportModelAdmin):
    list_display = ('id', 'nom', "nom_ar")
    search_fields = ('id', 'nom', 'nom_ar')


class WilayaImportExportAdmin(ImportExportModelAdmin):
    list_display = ('id', 'nom', "nom_ar", "get_pays")
    search_fields = ('id', 'nom', 'nom_ar', 'pays__nom')

    def get_pays(self, obj):
        return obj.pays

class VilleResource(resources.ModelResource):

    class Meta:
        model = Ville
        fields = ('id', 'nom', 'nom_ar', 'latitude', 'longitude', 'cl_map__geoname_id')


class VilleImportExportAdmin(ImportExportModelAdmin):
    resource_class = VilleResource
    list_display = ('id', 'nom', "nom_ar", "get_pays", "get_wilaya", "cl_map", "get_city_light", "latitude", "longitude")
    search_fields = ('id', 'nom', 'nom_ar', 'pays__nom', 'wilaya__nom', 'latitude', 'longitude')
    list_editable =("latitude", "longitude", "cl_map")
    autocomplete_fields = ("cl_map",)

    def get_pays(self, obj):
        return obj.pays

    def get_wilaya(self, obj):
        return obj.wilaya

    def get_city_light(self, obj):
        return f'{obj.cl_map.name if obj.cl_map else ""} ,{obj.cl_map.region.name if (obj.cl_map and obj.cl_map.region) else ""}'



admin.site.register(Commande, CommandeAdmin)
admin.site.register(BordereauVersement)
admin.site.register(Pays, PaysImportExportAdmin)
admin.site.register(Wilaya, WilayaImportExportAdmin)
admin.site.register(Ville, VilleImportExportAdmin)