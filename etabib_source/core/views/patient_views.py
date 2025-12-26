from datetime import datetime

from cities_light.models import Country, City
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from el_pagination.decorators import page_template

from core.decorators import is_patient, is_registered, v2_only
from core.enums import Role
from core.forms.patient_forms import PatientProfileForm, DciForm
from core.models import Patient, EquipeSoins
from drugs.models import DciAtc


@v2_only
@login_required
@is_patient
def dashboard(request):
    return render(request, "patient/dashboard.html", using=request.template_version)


@login_required
@is_registered
def registerPatient(request):
    if request.user.groups.count() == 0:
        with transaction.atomic():
            request.user.groups.add(Group.objects.get(name=Role.PATIENT.value))
            patient = Patient()
            patient.user = request.user
            patient.save()
    else:
        raise Http404
    return redirect(reverse("patient-dashboard"))


@login_required
@is_patient
def profile(request):
    patient = get_object_or_404(Patient, user=request.user)
    if request.method == 'POST':
        form = PatientProfileForm(request.POST, user=request.user, instance=patient)
        if form.is_valid():
            patient = form.save()
            messages.success(request, _("Profil mis à jour"))
    else:
        form = PatientProfileForm(user=request.user, instance=patient)
    context = {
        "form": form,
        "patient": patient,
        "sidebar_profile": True,
        "title": _("Mon Profil"),
        "dciform": DciForm()
    }
    return render(request, "patient/profile.html", context, using=request.template_version)


@login_required
def update_profile(request, patient_pk):
    if request.is_ajax():
        out = {}
        patient = get_object_or_404(Patient, id=patient_pk)
        name = request.POST.get("name", None)
        value = request.POST.get("value", None)
        if name:
            if name == "nom":
                patient.user.first_name = value
            elif name == "prenom":
                patient.user.last_name = value
            elif name == "sexe":
                patient.sexe = value
            elif name == "chifa":
                patient.chifa = value
            elif name == "date-naissance":
                patient.date_naissance = datetime.strptime(value, '%d-%m-%Y')
            elif name == "phone":
                patient.telephone = value
            elif name == "pays":
                patient.pays = Country.objects.get(id=value)
            elif name == "ville":
                patient.ville = City.objects.get(id=value)
            elif name == "allergies":
                dci = DciAtc.objects.get(id=value)
                allergies = patient.donnees_medicales.get("allergies", [])
                allergies.append({"id": dci.id, "value": dci.designation_fr})
                patient.donnees_medicales["allergies"] = allergies
            elif name == "mld":
                maladies_chroniques = patient.donnees_medicales.get("maladies_chroniques", [])
                maladies_chroniques.append(value)
                out["mld_index"] = maladies_chroniques.index(value)
                patient.donnees_medicales["maladies_chroniques"] = maladies_chroniques
            patient.save()
            patient.user.save()
    return JsonResponse(out, status=200)


@login_required
@is_patient
def remove_profile_data(request, patient_pk):
    if request.is_ajax():
        patient = get_object_or_404(Patient, id=patient_pk)
        name = request.POST.get("name", None)
        value = request.POST.get("value", None)
        if name == "allergies":
            allergies = patient.donnees_medicales.get("allergies", [])
            patient.donnees_medicales["allergies"] = [allergie for allergie in allergies if
                                                      str(allergie["id"]) != value]
        if name == "mld":
            maladies_chroniques = patient.donnees_medicales.get("maladies_chroniques", [])
            maladies_chroniques.pop(int(value))
            patient.donnees_medicales["maladies_chroniques"] = maladies_chroniques
        patient.save()
    return JsonResponse({}, status=200)


@login_required
@is_patient
@page_template('partial/care-team-partial.html')
def care_team(request, template="patient/care-team.html", extra_context=None):
    objects = EquipeSoins.objects.filter(patient__user=request.user)
    context = {
        "objects": objects
    }
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context, using=request.template_version)
