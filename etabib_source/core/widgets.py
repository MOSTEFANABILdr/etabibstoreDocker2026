import re

from dal.widgets import WidgetMixin
from dal_select2.widgets import Select2WidgetMixin, ModelSelect2, ModelSelect2Multiple
from django import forms
from django.forms import TextInput, Media
from django.urls import reverse


class AudioFileWidget(TextInput):
    class Media:
        js = (
            'js/audio_recorder/recorder.js',
            'js/audio_recorder/csrf.js',
        )

    def __init__(self, url=None, choices=None, *args, **kwargs):
        self.url = url
        self.choices = choices
        super(AudioFileWidget, self).__init__(*args, **kwargs)

    def build_attrs(self, *args, **kwargs):
        """Build HTML attributes for the widget."""
        attrs = super(AudioFileWidget, self).build_attrs(*args, **kwargs)
        if self.url is not None:
            attrs['data-url'] = reverse(self.url)
            attrs['data-django-audio-recorder'] = True

        return attrs

    def render(self, name, value, attrs=None, renderer=None):
        attrs['hidden'] = 'hidden'
        html = super(AudioFileWidget, self).render(name, value, attrs=attrs)
        if value:
            instance = self.choices.filter(id=value).first()
            audio_template = (
                '<audio id="js-audio" controls>'
                '    <source src={url}>'
                '</audio>'
            ).format(url=instance.file.url)
        else:
            audio_template = (
                '<audio class="hide" id="js-audio" controls>'
                '    <source>'
                '</audio>'
            )
        return audio_template + (
            '<section class="main-controls">'
            '<canvas class="visualizer hide" height="30px"></canvas>'
            '<div class="time blue"></div>'
            '<div class="btn-group">'
            '<button class="record btn btn-default">Record</button>'
            '<button class="stop btn btn-default">Stop</button>'
            '</div>'
            '</section>'
            '<span id="js-upload-span" '
            '      class="hide">'
            '    Uploading...'
            '</span>'
        ) + html


class CustomSelect2WidgetMixin(Select2WidgetMixin):
    @property
    def media(self):
        # get the default js and css media
        media = super().media

        # remove the jQuery script manually
        # this causes errors with datepicker-plus,
        # see https://github.com/monim67/django-bootstrap-datepicker-plus/issues/42
        # TODO this code patch can be removed in future,
        # because of https://github.com/yourlabs/django-autocomplete-light/commit/e46300d
        regex = re.compile(r"^admin/.*jquery(\.min)?\.js$")
        filtered_js = [item for item in media._js if not regex.search(item)]

        return Media(js=tuple(filtered_js), css=media._css)


class CustomAutoCompleteWidgetSingle(ModelSelect2, CustomSelect2WidgetMixin):
    pass


class CustomAutoCompleteWidgetMultiple(ModelSelect2Multiple, CustomSelect2WidgetMixin):
    pass


class DalQuerySetSelectMixin(WidgetMixin):
    """QuerySet support for choices."""

    # added (an override of) this method, to accept an optional 'to_field' parameter
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('to_field', 'pk')
        self.to_field_name = kwargs.pop('to_field')
        super().__init__(*args, **kwargs)

    # then use the value here
    def filter_choices_to_render(self, selected_choices):
        """Filter out un-selected choices if choices is a QuerySet."""
        filter_args = {'%s__in' % self.to_field_name: [c for c in selected_choices if
                                                       c]}  # Construct the 'pk__in' part with the chosen to_field name
        self.choices.queryset = self.choices.queryset.filter(
            **filter_args  # use the filter
        )


class DalModelSelect2(DalQuerySetSelectMixin,
                      Select2WidgetMixin,
                      forms.Select):
    """Custom Select widget for QuerySet choices and Select2."""
