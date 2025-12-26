from cities_light.models import Region
from dal import autocomplete, forward
from dateutil import parser
from django import forms
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admin.widgets import AdminDateWidget
from django.contrib.auth.models import User
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from core.forms.forms import VersionedMediaJS
from core.models import Specialite, Contact
from enewsletter.models import Newsletter, Message, NewsletterHistory
from enewsletter.utils import get_criteria_by_destination


#################
#    FORMS
#################
class NewsCriteriaChoicesAutocomplete(autocomplete.Select2ListView):
    def get_list(self):
        destination = self.forwarded.get('destination', None)
        return get_criteria_by_destination(destination)

    def results(self, results):
        """Return the result dictionary."""
        return [dict(id=x[0], text=x[1]) for x in results]

class NewsLetterForm(forms.ModelForm):
    regions = forms.ModelMultipleChoiceField(
        required=False,
        label=_('Régions'),
        queryset=Region.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(
            url='region-autocomplete',
            attrs={'data-html': True},
            forward=(forward.Const(62, 'country'),)
        ),
    )
    specialites = forms.ModelMultipleChoiceField(
        required=False,
        label=_('Spécialités'),
        queryset=Specialite.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(
            url='speciality-autocomplete',
            attrs={'data-html': True},
        ),
    )
    date_ajout = forms.DateField(label=_("Date d'ajout"), required=False, widget=AdminDateWidget())

    class Meta:
        model = Newsletter
        fields = ['title', 'destination', 'type', 'criteria_exp', 'criteria_days', 'criteria', 'regions', 'specialites',
                  'date_ajout', 'active']
        widgets = {
            'criteria': autocomplete.ListSelect2(
                url='news-criteria-choices-autocomplete',
                forward=['destination']
            )
        }

    class Media:
        js = (
            "/static/admin/js/vendor/jquery/jquery.min.js",
            VersionedMediaJS("newsletter_script.js", '1.0'),
        )

    def clean(self):
        cleaned_data = super(NewsLetterForm, self).clean()
        criteria = cleaned_data.get("criteria")
        destination = cleaned_data.get("destination")
        criteria_days = cleaned_data.get("criteria_days")
        criteria_exp = cleaned_data.get("criteria_exp")
        if not destination == Newsletter.DESTINATION_CHOICES[4][0]:
            if not criteria or not any(criteria == elem[0] for elem in get_criteria_by_destination(destination)):
                raise forms.ValidationError(
                    "criteria is required"
                )
            if not criteria_days:
                raise forms.ValidationError(
                    "Nb days is required"
                )
            if not criteria_exp:
                raise forms.ValidationError(
                    "Condition is required"
                )
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super(NewsLetterForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        nw = super(NewsLetterForm, self).save(commit=False)
        destination = self.cleaned_data.get("destination")
        regions = self.cleaned_data.get("regions")
        specialites = self.cleaned_data.get("specialites")
        date_ajout = self.cleaned_data.get("date_ajout")

        if destination == Newsletter.DESTINATION_CHOICES[4][0]:
            nw.criteria = Newsletter.CRITERIA_CHOICES[6][0]
            nw.criteria_days = None
            nw.criteria_exp = Newsletter.EXP_CHOICES[3][0]
            regions_ids = [region.id for region in regions]
            specialites_ids = [sp.id for sp in specialites]
            nw.criteria_json = {
                "regions": regions_ids,
                "specialites": specialites_ids,
                "date_ajout": date_ajout.strftime("%Y-%m-%d") if date_ajout else ""
            }
        else:
            nw.criteria_json = None

        if commit:
            nw.save()
        return nw


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = '__all__'

    def clean(self):
        cleaned_data = super(MessageForm, self).clean()
        newsletter = cleaned_data.get("newsletter")
        html_content = cleaned_data.get("html_content")
        content = cleaned_data.get("content")
        if newsletter.type == Newsletter.TYPE_CHOICES[1][0]:  # SMS
            if html_content:
                raise forms.ValidationError("SMS newsletter doesn't need html content.")
            if len(content) > 160:
                raise forms.ValidationError(
                    "The maximum length of text SMS message that you can send is 160 characters.")
        if newsletter.type == Newsletter.TYPE_CHOICES[0][0]:  # MAIL
            if not html_content:
                raise forms.ValidationError("The html content cannot be empty.")
        return cleaned_data


#################
#    MODELADMINS
#################
class MessageAdmin(admin.StackedInline):
    form = MessageForm
    extra = 1
    list_display = ('title', 'newsletter', 'draft')
    model = Message


class NewsTypeFilter(SimpleListFilter):
    title = 'Type'
    parameter_name = 'type'

    def lookups(self, request, model_admin):
        return Newsletter.TYPE_CHOICES

    def queryset(self, request, queryset):
        if self.value() == Newsletter.TYPE_CHOICES[0][0]:
            return queryset.filter(message__newsletter__type=Newsletter.TYPE_CHOICES[0][0])
        if self.value() == Newsletter.TYPE_CHOICES[1][0]:
            return queryset.filter(message__newsletter__type=Newsletter.TYPE_CHOICES[1][0])


class NewsletterHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_source', 'get_newsletter', 'get_newsletter_type', 'message', 'create_date')
    model = NewsletterHistory
    search_fields = ("id", "user__username", "user__first_name", "user__last_name", "message__title")
    list_filter = (NewsTypeFilter, "create_date")

    def get_newsletter(self, obj):
        if obj.message:
            link = reverse("admin:enewsletter_newsletter_change", args=[obj.message.newsletter.id])
            return mark_safe('<a href="%s">%s</a>' % (link, obj.message.newsletter.title))
        return ""

    def get_newsletter_type(self, obj):
        if obj.message:
            if obj.message.newsletter:
                return obj.message.newsletter.get_type_display()
        return ""

    def get_source(self, obj):
        if obj.source:
            if isinstance(obj.source, User):
                link = reverse("admin:auth_user_change", args=[obj.source.id])
                return mark_safe('<a href="%s">%s</a>' % (
                    link,
                    obj.source.get_full_name() if obj.source.get_full_name() else obj.source.username
                ))
            elif isinstance(obj.source, Contact):
                link = reverse("admin:core_contact_change", args=[obj.source.id])
                return mark_safe('<a href="%s">%s %s</a>' % (
                    link,
                    obj.source.nom,
                    obj.source.prenom if obj.source.prenom else ""
                ))
        return ""

    get_newsletter.short_description = _("Newsletter")
    get_source.short_description = _("User/Contact")
    get_newsletter_type.short_description = _("Type")


class NewsLetterAdmin(admin.ModelAdmin):
    change_form_template = "admin/change_newsletter.html"
    form = NewsLetterForm
    list_display = (
        'title', 'type', 'destination', 'criteria_exp', 'criteria_days', 'criteria', "criteria_json", "create_date",
        "get_normal_message", "get_draf_message", 'active'
    )
    list_filter = ("active", "type", 'destination', 'criteria')
    inlines = [
        MessageAdmin,
    ]

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super(NewsLetterAdmin, self).get_form(request, obj, change, **kwargs)
        if obj and obj.criteria_json:
            if 'regions' in obj.criteria_json:
                if isinstance(obj.criteria_json['regions'], list):
                    form.base_fields['regions'].initial = Region.objects.filter(id__in=obj.criteria_json['regions'])

            if 'specialites' in obj.criteria_json:
                if isinstance(obj.criteria_json['specialites'], list):
                    form.base_fields['specialites'].initial = Specialite.objects.filter(
                        id__in=obj.criteria_json['specialites']
                    )

            if 'date_ajout' in obj.criteria_json:
                if obj.criteria_json['date_ajout']:
                    form.base_fields['date_ajout'].initial = parser.parse(obj.criteria_json['date_ajout'])

        return form

    def get_normal_message(self, obj):
        span = "<strong style='color:green;'>{}<strong>"
        return format_html(span.format(obj.message_set.filter(draft=False).count()))

    def get_draf_message(self, obj):
        span = "<strong style='color:red;'>{}<strong>"
        return format_html(span.format(obj.message_set.filter(draft=True).count()))

    @staticmethod
    @staff_member_required
    def previewMessage(request, pk):
        context = {}
        try:
            obj = Newsletter.objects.get(pk=pk)
            context["newsletter"] = obj
        except Message.DoesNotExist:
            messages.warning(request, "The item does not exist")
        return render(request, "admin/newsletter_message_preview.html", context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        nl = Newsletter.objects.get(pk=object_id)
        extra_context['hide_extra_fields'] = (nl.destination != Newsletter.DESTINATION_CHOICES[4][0])
        return super(NewsLetterAdmin, self).change_view(request, object_id, form_url, extra_context)

    get_normal_message.short_description = _("Messages")
    get_draf_message.short_description = _("Drafts")


admin.site.register(Newsletter, NewsLetterAdmin)
admin.site.register(NewsletterHistory, NewsletterHistoryAdmin)
