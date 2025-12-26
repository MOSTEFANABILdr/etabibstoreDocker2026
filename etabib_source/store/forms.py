from dal import autocomplete
from django import forms
from django.utils.translation import ugettext_lazy as _
from taggit.models import Tag

from core.templatetags.role_tags import is_doctor


class SearchV2Form(forms.Form):
    CHOICES = (
        ("0", _("eTabib Applications")),
        ("1", _("Mes Applications")),
    )
    sq = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'placeholder': _('Entrez des mots-clés')}))
    category = forms.ChoiceField(choices=CHOICES, required=False)
    sub_category = forms.ModelMultipleChoiceField(
        required=False,
        label=_('Tag'),
        queryset=Tag.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(
            url='tag-autocomplete',
        ),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(SearchV2Form, self).__init__(*args, **kwargs)
        if self.user:
            if not is_doctor(self.user):
                self.fields['category'].choices = self.CHOICES[:-1]
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'