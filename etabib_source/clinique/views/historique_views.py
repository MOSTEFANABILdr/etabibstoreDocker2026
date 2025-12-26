from functools import reduce
from operator import or_

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from el_pagination.decorators import page_template

from clinique.models import DetailClinique, Consultation, Document
from core.models import Patient


@login_required
@page_template('partial/care-path-partial.html')
def care_path(request, patient_pk=None, template="care-path.html", extra_context=None):
    if patient_pk:
        patient = get_object_or_404(Patient, pk=patient_pk)
    elif hasattr(request.user, "patient"):
        patient = request.user.patient
    else:
        raise Http404

    details = DetailClinique.objects.filter(
        patient__pk=patient.pk
    ).order_by('-date_creation')
    context = {
        'patient': patient,
        'events': details
    }
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context, using=request.template_version)


@login_required
def filter_historique(request, patient_pk):
    patient = Patient.objects.get(pk=patient_pk)

    # searching parameters
    type_ev = request.GET.get("type_ev", None)
    q = request.GET.get("q", None)

    qs = DetailClinique.objects.filter(patient__pk=patient_pk)

    if type_ev:
        """
        1 = Consultation
        2 = Document
        3 = Tous
        """
        if type_ev == "1":
            qs = qs.instance_of(Consultation)
        elif type_ev == "2":
            qs = qs.instance_of(Document)

    if q:
        filters = [
            "consultation__motif", "consultation__interrogatoire", "consultation__examen_clinique",
            "consultation__examen_demande", "consultation__resultat_examen", "consultation__diag_suppose",
            "consultation__diag_retenu", "consultation__conduite_tenir", "document__titre", "document__titre",
            "document__description", "consultation__operateur__last_name",
            "document__operateur__first_name",
            "document__operateur__last_name",
        ]
        qs = qs.filter(
            reduce(or_, (Q(**{f'{k}__icontains': q}) for k in filters))
        )

    context = {
        'events': qs.order_by('-date_creation'),
        'patient': patient,
    }
    return render(request, "partial/care-path-partial.html", context)
