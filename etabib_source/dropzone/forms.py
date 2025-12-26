from django import forms
from dropzone.utils import flatatt
from django.template import loader, Context


class TemplateBasedInput(forms.widgets.Input):
    template_name = ''

    def get_context_data(self, name, value, attrs):
        context = {
            'upload_name': name,
            'value': value,
            'attrs': flatatt(self.build_attrs(attrs, {'type': self.input_type, 'name': name}))
        }

        return context

    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = ''

        t = loader.get_template(self.template_name)

        c = self.get_context_data(name, value, attrs)

        return t.render(c)


class DropzoneInput(TemplateBasedInput, forms.TextInput):
    template_name = 'dropzone/dropzone.html'

    def __init__(self, *args, **kwargs):
        self.acceptedFiles = kwargs.pop('acceptedFiles', '')
        self.width = kwargs.pop('width', '')
        self.height = kwargs.pop('height', '')
        self.paramName = kwargs.pop('paramName', '')
        self.maxFilesize = kwargs.pop('maxFilesize', '')
        self.maxFiles = kwargs.pop('maxFiles', '')
        self.upload_path = kwargs.pop('upload_path', '')
        self.placeholder = kwargs.pop('placeholder', '')
        self.maxDuration = kwargs.pop('maxDuration', '')
        super(DropzoneInput, self).__init__(*args, **kwargs)

    def get_context_data(self, name, value, attrs):
        context = super(DropzoneInput, self).get_context_data(name, value, attrs)
        context['acceptedFiles'] = self.acceptedFiles
        context['maxFilesize'] = self.maxFilesize
        context['height'] = self.height
        context['width'] = self.width
        context['maxFiles'] = self.maxFiles
        context['upload_path'] = self.upload_path
        context['paramName'] = self.paramName
        context['placeholder'] = self.placeholder
        context['maxDuration'] = self.maxDuration
        return context
