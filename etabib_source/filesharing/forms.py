import os

import requests
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, HTML
from dal import autocomplete
from django import forms
from django.forms import HiddenInput
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils.translation import gettext as _

from core import tasks
from core.enums import Role
from core.forms.forms import VersionedMediaJS
from core.models import Patient, Medecin
from etabibWebsite import settings
from filesharing.encrypt import EncryptionService
from filesharing.utils import getPatientFileTypeName, generateAuthenticationJwtToken, generateUniqueUserId, \
    decryptUserUiqueId


class UploadFileForm(forms.Form):
    file = forms.FileField()

    def clean_file(self):
        content = self.cleaned_data['file']
        if content.size > 4 * 1024 * 1024:
            raise forms.ValidationError(_('Please keep filesize under %s. Current filesize %s') % (
                filesizeformat(4 * 1024 * 1024), filesizeformat(content.size)))
        return self.cleaned_data['file']

    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop('patient', None)
        self.doctor = kwargs.pop('doctor', None)
        self.type = kwargs.pop('type')
        super(UploadFileForm, self).__init__(*args, **kwargs)

    def save(self):
        file = self.cleaned_data['file']
        old_name = file.name.split(os.extsep)[0]
        url = settings.SH_UPLOAD_FILE_ENDPOINT + "?type=" + self.type
        # encrypt the uploaded file
        service = EncryptionService(raise_exception=True)
        encrypted_file = service.encrypt_file(file, settings.SH_ENCRYPTION_PASSWORD)  # it will save readme.md.enc
        # write the encrypted file(bytes) to the tempFile
        # create temporary file
        if self.patient:
            data = {"patient_id": generateUniqueUserId(self.patient.id, Role.PATIENT), "alt_name": old_name}
        elif self.doctor:
            data = {"doctor_id": generateUniqueUserId(self.doctor.id, Role.DOCTOR), "alt_name": old_name}
        files = {'file': encrypted_file}
        headers = {
            'TAFWID': generateAuthenticationJwtToken(self.patient.user if self.patient else self.doctor.user)
        }
        response = requests.post(url, files=files, data=data, verify=False, headers=headers)
        os.remove(encrypted_file.name)
        if response.status_code == 200:
            return (True, 200)
        else:
            return (False, response.status_code)


class FileForm(forms.Form):
    file = forms.CharField(required=False)

    class Media:
        css = {
            'all': ('css/dropzone/dropzone.css',)
        }
        js = (
            "js/dropzone/dropzone.js",
            VersionedMediaJS('js/dropzone/dropzone-active.js', '2.5'),
        )

    def __init__(self, *args, **kwargs):
        super(FileForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = True
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Div(
                Div(
                    HTML(
                        '<div class ="dz-default dz-message" > '
                        '<span>' + _('Cliquer pour uploader un ficher') +
                        '</span> <br>'
                        '<small>' + _('Les types de fichiers acceptés sont: une image ou un fichier PDF') + '</small>'
                        '<small> < 4Mb </small>'
                        '</div>'
                    ),
                    css_id="file_upload",
                    css_class="needsclick download-custom dropzone ",
                ),
                css_class="row"
            )
        )


class ShareFileForm(forms.Form):
    patient = forms.ModelChoiceField(
        label=_('Patient'),
        queryset=Patient.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2(
            url='recently-patient-autocomplete',
            attrs={
                'data-placeholder': _('Choisir une patient ...'),
            }
        ),
    )

    medecin = forms.ModelChoiceField(
        label=_('Médecin'),
        queryset=Medecin.objects.all(),
        required=False,
        widget=autocomplete.ModelSelect2(
            url='recently-doctor-autocomplete',
            attrs={
                'data-placeholder': _('Choisir un médecin ...'),
                'data-html': True
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        self.file_id = kwargs.pop('file_id', None)
        self.doctor = kwargs.pop('doctor', None)
        self.patient = kwargs.pop('patient', None)
        self.user = self.doctor.user if self.doctor else self.patient.user
        self.type = kwargs.pop('type', None)
        self.sharedWith = kwargs.pop('sharedWith', None)
        self.hide_doctor_field = kwargs.pop('hide_doctor_field', None)
        self.hide_patient_field = kwargs.pop('hide_patient_field', None)
        super(ShareFileForm, self).__init__(*args, **kwargs)
        patientIds = []
        for encryptedPatientId in self.sharedWith['patients']:
            patient_id = decryptUserUiqueId(encryptedPatientId, Role.PATIENT)
            patientIds.append(patient_id)
        doctorIds = []
        for encryptedDoctorId in self.sharedWith['doctors']:
            doctor_id = decryptUserUiqueId(encryptedDoctorId, Role.DOCTOR)
            doctorIds.append(doctor_id)

        sharedWithPatients = Patient.objects.filter(id__in=patientIds)
        sharedWithDoctors = Medecin.objects.filter(id__in=doctorIds)
        if self.hide_patient_field:
            self.fields['patient'].widget = HiddenInput()
        if self.hide_doctor_field:
            self.fields['medecin'].widget = HiddenInput()
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "medecin",
            'patient',
            HTML("<hr>"),
            HTML("<strong>" + _("Le fichier est partagé avec") + ":</strong>"),
            Div(
                HTML("<p>%s</p>" % ",".join([p.full_name for p in sharedWithPatients])),
                HTML("<p>%s</p>" % ",".join(["Dr: %s" % d.full_name for d in sharedWithDoctors])),
            ),
        )

    def save(self, commit=False):
        patient = self.cleaned_data['patient']
        doctor = self.cleaned_data['medecin']
        url = settings.SH_SHARE_FILE_ENDPOINT
        headers = {'TAFWID': generateAuthenticationJwtToken(self.user)}
        if self.hide_patient_field and doctor:
            data = {
                "patient_id": generateUniqueUserId(self.patient.id, Role.PATIENT),
                "doctor_id": generateUniqueUserId(doctor.id, Role.DOCTOR),
                "file_id": self.file_id
            }
            response = requests.post(url, data=data, headers=headers, verify=False)
            if response.status_code == 200:
                tasks.notify(
                    self.patient,
                    recipients=[doctor.user],
                    description=_("Le patient %s a partagé un fichier de type %s avec vous.") % (
                        self.patient.full_name,
                        getPatientFileTypeName(self.type)
                    ),
                    verb="Partage des fichiers",
                    url=reverse("doctor-files-list")
                )
            else:
                return False

        elif self.hide_doctor_field and patient:
            data = {
                "patient_id": generateUniqueUserId(patient.id, Role.PATIENT),
                "doctor_id": generateUniqueUserId(self.doctor.id, Role.DOCTOR),
                "file_id": self.file_id
            }
            response = requests.post(url, data=data, verify=False, headers=headers)
            if response.status_code == 200:
                tasks.notify(
                    self.doctor, recipients=[patient.user], target=patient.user,
                    description=_("Dr %s a partagé un fichier de type %s avec vous.") % (
                        self.doctor.full_name,
                        getPatientFileTypeName(self.type)
                    ),
                    verb="Partage des fichiers",
                    url=reverse("patient-files-list")
                )
            else:
                return False
        return True


class RenameFileForm(forms.Form):
    filename = forms.CharField(label=_('Nouveau nom'), max_length=255)

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        self.file_id = kwargs.pop('file_id', None)
        self.user = kwargs.pop('user', None)
        super(RenameFileForm, self).__init__(*args, **kwargs)

    def save(self, commit=False):
        filename = self.cleaned_data['filename']
        url = settings.SH_RENAME_FILE_ENDPOINT
        headers = {'TAFWID': generateAuthenticationJwtToken(self.user)}

        data = {
            "file_id": self.file_id,
            "alternative_name": filename
        }
        response = requests.post(url, data=data, verify=False, headers=headers)
        if response.status_code == 200:
            return True
        return False
