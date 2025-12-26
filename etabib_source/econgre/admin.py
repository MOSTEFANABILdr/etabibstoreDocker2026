from django.contrib import admin

from econgre.models import Congre, Organisateur, Webinar, Speaker, UserParticipationWebinar, Sponsor, CongreImage, \
    Moderateur, WebinarVideo, WebinarUrl


class WebinarAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom', 'date_debut', "heure_debut", "heure_fin")
    search_fields = ['nom',]

admin.site.register(Congre)
admin.site.register(CongreImage)
admin.site.register(Organisateur)
admin.site.register(Webinar, WebinarAdmin)
admin.site.register(WebinarVideo)
admin.site.register(WebinarUrl)
admin.site.register(Speaker)
admin.site.register(Moderateur)
admin.site.register(Sponsor)
admin.site.register(UserParticipationWebinar)

