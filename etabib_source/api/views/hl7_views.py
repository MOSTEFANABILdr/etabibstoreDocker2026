from django.db.models import Q
from django.shortcuts import get_object_or_404
from fhir.resources.bundle import Bundle
from fhir.resources.patient import Patient as PatietFhir
from hl7apy.core import Message
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_tracking.mixins import LoggingMixin

from api.serializers.hl7_serializers import Hl7Serializer
from core.models import Patient


def patient_to_hl7(patient_id):
    m = Message('ADT_A01', version='2.7')
    m.msh.msh_3 = "etabibstore"
    # m.msh.msh_4 = "Hopital N°1"
    m.msh.msh_5 = "eTabib Workspace"
    # m.msh.msh_6 = "Clinic N°1"

    patient = get_object_or_404(Patient, id=patient_id)
    m.pid
    m.pid.pid_2 = str(patient.id) or ""
    m.pid.pid_3 = str(patient.id or "")
    m.pid.pid_5.pid_5_1 = patient.nom
    m.pid.pid_5.pid_5_2 = patient.prenom
    m.pid.pid_7 = patient.date_naissance.strftime("%Y%m%d") if patient.date_naissance else ""
    m.pid.pid_8 = "M" if patient.sexe == Patient.GENDER_CHOICES[0][0] else "F" if patient.sexe == \
                                                                                  Patient.GENDER_CHOICES[1][0] else ""
    m.pid.pid_11 = patient.adresse or ""
    m.pid.pid_12 = "DZ"
    # m.pid.pid_19 = patient.numero_de_securite_sociale or ""
    return m.to_er7()


def patient_to_fhir(patient):
    pFhir = PatietFhir()
    pFhir.birthDate = patient.date_naissance
    pFhir.gender = "male" if patient.sexe == Patient.GENDER_CHOICES[0][0] else "female" if patient.sexe == \
                                                                                           Patient.GENDER_CHOICES[1][
                                                                                               0] else "unknown"
    json_obj = {
        "resourceType": "Patient",
        "id": patient.id,
        "active": True,
        "name": [
            {
                "text": patient.full_name,
                "family": patient.nom,
                "given": [patient.prenom, ]
            },
        ],
        "address": [{
            "country": patient.pays.name if patient.pays else "Algeria",
            "city": patient.ville.name if patient.ville else "Algiers",
        }],
    }
    pFhir = PatietFhir.parse_obj(json_obj)
    pFhir.birthDate = patient.date_naissance
    pFhir.active = True

    return pFhir

def get_hl7(request):
    patient_id = request.GET.get("patient_id", None)
    if patient_id:
        data = patient_to_hl7(patient_id)
        return data


def get_fhir(request):
    patient_id = request.GET.get("patient_id", None)
    if patient_id:
        patient = get_object_or_404(Patient, id=patient_id)
        pfhir = patient_to_fhir(patient)
        return pfhir.dict()

    patients = Patient.objects.all().exclude(
        Q(user__first_name__isnull=True) | Q(user__first_name='')
    ).exclude(
        Q(user__last_name__isnull=True) | Q(user__last_name='')
    ).order_by("-id")[:10]
    json_bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": []
    }

    arr = []
    for patient in patients:
        pfhir = patient_to_fhir(patient)
        arr.append({"resource": pfhir.dict()})
    json_bundle["entry"] = arr

    bundle = Bundle.parse_obj(json_bundle)

    return bundle.dict()


class Hl7View(LoggingMixin, generics.GenericAPIView):
    serializer_class = Hl7Serializer

    def handle_log(self):
        super(Hl7View, self).handle_log()

    def get(self, request):
        data = {}
        t = request.GET.get("t", None)
        if t == "hl7":
            data = get_hl7(request)
        if t == "fhir":
            data = get_fhir(request)
        if data:
            return Response(data, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_400_BAD_REQUEST)

