import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from fm.views import AjaxCreateView

from etabibWebsite import settings
from filesharing.forms import ShareFileForm, RenameFileForm
from filesharing.utils import generateAuthenticationJwtToken


class ShareFileView(SuccessMessageMixin, AjaxCreateView):
    form_class = ShareFileForm
    success_message = _("Fichier partagé")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.file_id = kwargs['file_id'] if 'file_id' in kwargs else None
        self.type = kwargs['type'] if 'type' in kwargs else None
        self.doctor = None
        self.patient = None
        if hasattr(request.user, 'medecin'):
            self.doctor = request.user.medecin
        if hasattr(request.user, 'patient'):
            self.patient = request.user.patient
        # get list of users have access to this file
        url = settings.SH_FILE_SHARED_WITH_ENDPOINT + "%s"
        headers = {'TAFWID': generateAuthenticationJwtToken(self.request.user)}
        response = requests.get(url % (self.file_id), verify=False, headers=headers)
        response.raise_for_status()
        # access JSOn content
        context = {}
        self.sharedWith = None
        jsonResponse = response.json()
        if jsonResponse:
            self.sharedWith = jsonResponse
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(ShareFileView, self).get_form_kwargs()
        kwargs["file_id"] = self.file_id
        kwargs["type"] = self.type
        kwargs["doctor"] = self.doctor
        kwargs["patient"] = self.patient
        kwargs["sharedWith"] = self.sharedWith
        kwargs["hide_patient_field"] = False if self.doctor else True
        kwargs["hide_doctor_field"] = False if self.patient else True
        return kwargs

    def form_valid(self, form):
        valid = form.save()
        if not valid:
            return self.render_json_response({'status': 'error', 'message':
                _("Vous n'avez pas assez de privilèges pour effectuer cette action")})

        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(self.get_success_result())


class RenameFileView(SuccessMessageMixin, AjaxCreateView):
    form_class = RenameFileForm
    success_message = _("Fichier renomé")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.file_id = kwargs['file_id'] if 'file_id' in kwargs else None
        self.user = request.user
        # get list of users have access to this file
        url = settings.SH_RETRIEVE_FILE_ENDPOINT + "%s"
        headers = {'TAFWID': generateAuthenticationJwtToken(self.request.user)}
        response = requests.get(url % (self.file_id), verify=False, headers=headers)
        response.raise_for_status()
        jsonResponse = response.json()
        self.old_filename = jsonResponse['filename']
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        context = super(RenameFileView, self).get_initial()
        context['filename'] = self.old_filename
        return context

    def get_form_kwargs(self):
        kwargs = super(RenameFileView, self).get_form_kwargs()
        kwargs["file_id"] = self.file_id
        kwargs["user"] = self.user
        return kwargs

    def form_valid(self, form):
        valid = form.save()
        if not valid:
            return self.render_json_response({'status': 'error', 'message':
                _("Vous n'avez pas assez de privilèges pour effectuer cette action")})

        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(self.get_success_result())
