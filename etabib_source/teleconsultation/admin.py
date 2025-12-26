from django.contrib import admin

from teleconsultation.models import Tdemand, Room, Presence, Tsession, TspeakerStats, Tfeedback, \
    Treclamation


class TeleconsultationDemandAdmin(admin.ModelAdmin):
    list_display = ('id', 'medecin', 'patient', 'annulee', 'acceptee', 'coupon', 'facturee', 'tarif', 'date_demande')


class PresenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'last_seen', 'busy', 'remove_busy_after')


admin.site.register(Tdemand, TeleconsultationDemandAdmin)
admin.site.register(Tsession)
admin.site.register(TspeakerStats)
admin.site.register(Tfeedback)
admin.site.register(Treclamation)
admin.site.register(Room)
admin.site.register(Presence, PresenceAdmin)
