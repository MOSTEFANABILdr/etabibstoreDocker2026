from django.contrib import admin

from core.models import Contact
from smsicosnet.models import Smsicosnet, STATUS
from smsicosnet.utils import correct_numbers


def requeue(modeladmin, request, queryset):
    queryset.update(status=STATUS.queued)


requeue.short_description = 'Requeue selected sms'


class SmsicosnetAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_name', 'get_telephone', 'get_message', "date_creation", "status")
    actions = [requeue, ]

    def get_message(self, obj):
        return obj.message

    def get_telephone(self, obj):
        return correct_numbers(obj.source)

    def get_name(self, obj):
        if obj.source:
            if isinstance(obj.source, Contact):
                return obj.source.full_name

    get_message.short_description = 'Message'
    get_telephone.short_description = 'Téléphone'
    get_name.short_description = 'Nom & Prénom'


admin.site.register(Smsicosnet, SmsicosnetAdmin)
