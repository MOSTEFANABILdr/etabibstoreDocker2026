from django.contrib import admin

# Register your models here.
from epayment.models import OrdreDePaiement

class OrdreDePaiementAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'etat', 'montant', 'date_creation')
    search_fields = ['user__username',]

admin.site.register(OrdreDePaiement, OrdreDePaiementAdmin)
