import os
import re
import urllib
from datetime import datetime
from urllib.parse import urlparse, parse_qs

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.temp import gettempdir
from django.http import JsonResponse, HttpResponse, FileResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _

from core.enums import Role
from core.models import Medecin, Patient
from core.templatetags.offer_tags import is_including_etabib_care
from etabibWebsite import settings
from filesharing.encrypt import EncryptionService, ValidationError
from filesharing.enums import PatientFileType
from filesharing.forms import FileForm, UploadFileForm
from filesharing.utils import generateUniqueUserId, decryptUserUiqueId, \
    getPatientFileTypeName, generateAuthenticationJwtToken


@login_required
def listFiles(request):
    context = {
        'form': FileForm(),
    }
    if hasattr(request.user, "patient"):
        context["sidebar_files"] = True
    elif hasattr(request.user, "medecin"):
        context["sidebar_files"] = True
    return render(request, "patient/my-files.html", context)


@login_required
def fetchFiles(request):
    if request.is_ajax():
        page = request.GET.get('page', None)
        type = request.GET.get('type', "1")

        headers = {'TAFWID': generateAuthenticationJwtToken(request.user)}
        if hasattr(request.user, 'medecin'):
            # url format settings.SH_FETCH_DOCTOR_FILES_ENDPOINT/doctor_id?type=x&page=y
            url = settings.SH_FETCH_DOCTOR_FILES_ENDPOINT + "%s" + ("?type=" + type) + ("&page=" + page if page else "")
            response = requests.get(url % (
                generateUniqueUserId(request.user.medecin.id, Role.DOCTOR)
            ), headers=headers, verify=False)
        elif hasattr(request.user, 'patient'):
            url = settings.SH_FETCH_PATIENT_FILES_ENDPOINT + "%s" + ("?type=" + type) + (
                "&page=" + page if page else "")
            response = requests.get(url % (
                generateUniqueUserId(request.user.patient.id, Role.PATIENT)
            ), headers=headers, verify=False)

        response.raise_for_status()
        # access JSOn content
        context = {}
        jsonResponse = response.json()
        if jsonResponse:
            count = jsonResponse['count']
            ord_count = jsonResponse['ord_count']
            bil_count = jsonResponse['bil_count']
            certif_count = jsonResponse['certif_count']
            letr_count = jsonResponse['letr_count']
            crend_count = jsonResponse['crend_count']
            if jsonResponse['next']:
                parsed = urlparse(jsonResponse['next'])
                next = parse_qs(parsed.query)['page'] if 'page' in parse_qs(parsed.query) else ""
            else:
                next = None
            if jsonResponse['previous']:
                parsed = urlparse(jsonResponse['previous'])
                previous = parse_qs(parsed.query)['page'] if 'page' in parse_qs(parsed.query) else "1"
            else:
                previous = None
            results = jsonResponse['results']
            files = []
            for item in results:
                file = dict()
                file["id"] = item["id"]
                file["url"] = item["file"]
                file["filename"] = item["filename"]
                if item["owner"]:
                    # owner may be a patient or a doctor
                    try:
                        owner_id = decryptUserUiqueId(item["owner"], Role.DOCTOR)
                        medecin = Medecin.objects.get(id=owner_id)
                        file['owner'] = "me" if medecin.user == request.user else "Dr " + medecin.full_name
                        file['can_delete'] = True if medecin.user == request.user else False
                    except Exception as e:
                        pass
                    try:
                        owner_id = decryptUserUiqueId(item["owner"], Role.PATIENT)
                        patient = Patient.objects.get(id=owner_id)
                        file['owner'] = _("Moi") if patient.user == request.user else patient.full_name
                        file['can_delete'] = True if patient.user == request.user else False
                    except Exception as e:
                        pass
                path = urllib.parse.urlsplit(file["url"]).path
                ext = os.path.splitext(path)[1]
                file["date_creation"] = datetime.strptime(item["date_creation"], '%Y-%m-%d %H:%M:%S')
                files.append(file)

            # get title
            title = ""
            for item in PatientFileType:
                if item.value[0] == type:
                    title = item.value[1]
            context.update({
                'count': count,
                'next': next,
                'type': type,
                'previous': previous,
                'files': files,
                'title': title,
            })
        return JsonResponse(
            {
                'content': render_to_string('partial/files-partial.html', context),
                "ord_count": ord_count,
                'bil_count': bil_count,
                'certif_count': certif_count,
                'letr_count': letr_count,
                'crend_count': crend_count
            },
            status=200
        )


@login_required
def uploadFile(request):
    if request.is_ajax():
        if hasattr(request.user, "medecin"):
            if not is_including_etabib_care(request.user.medecin.current_services):
                messages.warning(request, _("Désolé, votre abonnement ne contient pas le service: eTabib Care."))
                return JsonResponse({'redirect_url': reverse("doctor-offers") }, status=403)

        type = request.GET.get('type', None)
        if hasattr(request.user, "patient"):
            form = UploadFileForm(request.POST, request.FILES, patient=request.user.patient, type=type)
        elif hasattr(request.user, "medecin"):
            form = UploadFileForm(request.POST, request.FILES, doctor=request.user.medecin, type=type)
        if form.is_valid():
            valid, status = form.save()
            if valid:
                messages.success(
                    request,
                    _("Le fichier de type: %s a été chiffré et téléchargé avec succès ") % getPatientFileTypeName(type)
                )
                return JsonResponse({}, status=200)
            else:
                return JsonResponse({"error": status}, status=status)
        else:
            return JsonResponse({'error': form.errors}, status=400)


@login_required
def deleteFile(request, file_id):
    if request.is_ajax():
        headers = {'TAFWID': generateAuthenticationJwtToken(request.user)}
        url = settings.SH_DELETE_FILE_ENDPOINT + file_id
        response = requests.delete(url, headers=headers)
        return JsonResponse({}, status=response.status_code)
    else:
        return JsonResponse({}, status=500)


@login_required
def getFile(request, file_id):
    context = {}
    headers = {'TAFWID': generateAuthenticationJwtToken(request.user)}
    url = settings.SH_GET_FILE_ENDPOINT + file_id
    r = requests.get(url, allow_redirects=True, headers=headers)
    d = r.headers['content-disposition']
    fname = re.findall("filename=\"(.+)\"", d)[0]

    tmpDir = os.path.join(gettempdir(), '.{}'.format(hash(os.times())))
    os.makedirs(tmpDir)
    encryptedFilepath = os.path.join(tmpDir, fname)
    with open(encryptedFilepath, 'wb') as encrypted_file:
        encrypted_file.write(r.content)
        encrypted_file.flush()

    try:
        service = EncryptionService(raise_exception=True)
        decrypt_file = service.decrypt_file(encrypted_file, settings.SH_ENCRYPTION_PASSWORD)
    except ValidationError as e:
        return HttpResponse(status=500)
    return FileResponse(decrypt_file)
