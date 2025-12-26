from django import forms
from django.contrib import admin
# Register your models here.
from django.core.exceptions import ValidationError
from django.db import models
from django.forms import BaseInlineFormSet
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _
from post_office.admin import SubjectField

from etabibWebsite import settings
from smsgateway.models import Sms, Critere, SmsModel, Listenvoi, SMSTemplate


class SMSTemplateAdminFormSet(BaseInlineFormSet):
    def clean(self):
        """
        Check that no two Sms templates have the same default_template and language.
        """
        super().clean()
        data = set()
        for form in self.forms:
            default_template = form.cleaned_data['default_template']
            language = form.cleaned_data['language']
            if (default_template.id, language) in data:
                msg = _("Duplicate template for language '{language}'.")
                language = dict(form.fields['language'].choices)[language]
                raise ValidationError(msg.format(language=language))
            data.add((default_template.id, language))


class SMSTemplateAdminForm(forms.ModelForm):
    language = forms.ChoiceField(
        choices=settings.LANGUAGES,
        required=False,
        label=_("Language"),
        help_text=_("Render template in alternative language"),
    )

    class Meta:
        model = SMSTemplate
        fields = ['name', 'description', 'content', 'language',
                  'default_template']

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if instance and instance.language:
            self.fields['language'].disabled = True


class SMSTemplateInline(admin.StackedInline):
    form = SMSTemplateAdminForm
    formset = SMSTemplateAdminFormSet
    model = SMSTemplate
    extra = 0
    fields = ('language', 'content',)
    formfield_overrides = {
        models.CharField: {'widget': SubjectField}
    }

    def get_max_num(self, request, obj=None, **kwargs):
        return len(settings.LANGUAGES)


class SMSTemplateAdmin(admin.ModelAdmin):
    form = SMSTemplateAdminForm
    list_display = ('name', 'description_shortened', 'languages_compact', 'created')
    search_fields = ('name', 'description')
    fieldsets = [
        (None, {
            'fields': ('name', 'description'),
        }),
        (_("Default Content"), {
            'fields': ('content',),
        }),
    ]
    inlines = (SMSTemplateInline,) if settings.USE_I18N else ()
    formfield_overrides = {
        models.CharField: {'widget': SubjectField}
    }

    def get_queryset(self, request):
        return self.model.objects.filter(default_template__isnull=True)

    def description_shortened(self, instance):
        return Truncator(instance.description.split('\n')[0]).chars(200)
    description_shortened.short_description = _("Description")
    description_shortened.admin_order_field = 'description'

    def languages_compact(self, instance):
        languages = [tt.language for tt in instance.translated_templates.order_by('language')]
        return ', '.join(languages)
    languages_compact.short_description = _("Languages")

    def save_model(self, request, obj, form, change):
        obj.save()

        # if the name got changed, also change the translated templates to match again
        if 'name' in form.changed_data:
            obj.translated_templates.update(name=obj.name)

class SmsAdmin(admin.ModelAdmin):
    list_display = ('id', 'source', 'message', 'status')
    list_filter = ('status', )

admin.site.register(Sms, SmsAdmin)
admin.site.register(SmsModel)
admin.site.register(Listenvoi)
admin.site.register(Critere)
admin.site.register(SMSTemplate, SMSTemplateAdmin)
