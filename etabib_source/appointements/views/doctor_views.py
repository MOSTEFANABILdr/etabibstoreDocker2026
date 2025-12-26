import json
import os

from dal import autocomplete
from datatableview import Datatable, columns
from datatableview.views import DatatableView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.timesince import timeuntil
from django.utils.translation import ugettext_lazy as _
from fm.views import AjaxUpdateView, AjaxCreateView

from appointements.enums import RdvStatus
from appointements.forms import TraiterRendezVousForm, CreateAppointmentForm, RendezVousDoctorCreateFormStep1, \
    RendezVousDoctorCreateFormStep2
from appointements.models import DemandeRendezVous, LettreOrientation
from appointements.templatetags.rdv_tags import renderStatus
from core.decorators import is_doctor, has_access, is_partner
from core.enums import EtabibService
from core.mixins import TemplateVersionMixin
from core.models import Patient
from core.templatetags.utils_tags import offer_id_unhash
from core.utils import getEventTitle, getEventColor, getEventIcon, hasEnoughMoney
from teleconsultation.models import Tdemand


class DemandeRendezVousDatatable(Datatable):
    actions = columns.TextColumn(_("Actions"), source=None, processor='get_entry_action')
    status = columns.TextColumn(_("Etat"), source=None, processor='get_entry_status')
    type = columns.TextColumn(_("Lieu"), source=None, processor='get_entry_type')
    demandeur_nom = columns.TextColumn(source=['demandeur__first_name'])
    demandeur = columns.TextColumn(_("Patient"), source=['demandeur__get_full_name'])
    demandeur_prenom = columns.TextColumn(source=['demandeur__last_name'])
    date_demande = columns.TextColumn(_("Date de la demande"), source=None, processor='get_entry_date_demande')
    lettre = columns.TextColumn(_("Lettre"), source=None, processor='get_entry_lettre')
    date_rendez_vous = columns.TextColumn(_("Date de rendez-vous"), source=None, processor='get_entry_date_rendez_vous')

    class Meta:
        columns = ["demandeur", "date_demande", "type", "status", "date_rendez_vous", "lettre","actions"]
        labels = {
            "demandeur": _("Patient")
        }
        hidden_columns = ["demandeur_nom", "demandeur_prenom"]
        search_fields = ['demandeur__first_name', "demandeur__last_name"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 10

    def get_entry_date_demande(self, instance, **kwargs):
        if instance.date_creation:
            return instance.date_creation.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_entry_date_rendez_vous(self, instance, **kwargs):
        str = "<p>{}</p><p>{}</p>"
        if instance.date_rendez_vous:
            text = _("Restant")
            return str.format(
                instance.date_rendez_vous.strftime("%Y-%m-%d %H:%M:%S"),
                "<strong>%s:</strong> %s" % (text, timeuntil(
                    instance.date_rendez_vous, timezone.now()
                )) if instance.status == RdvStatus.ACCEPTED else ""
            )
        return ""

    def get_entry_lettre(self, instance, **kwargs):
        lettres = LettreOrientation.objects.filter(demande=instance)
        html = ''
        if lettres:
            for lettre in lettres:
                print(lettre.lettre.url)
                html += """
                <a class="image-link" data-lightbox="%s" href="%s" alt="">
                    <div class="widget-img widget-img-xl rounded bg-inverse pull-left m-r-5 m-b-5" 
                    style="background-image: url(%s)"></div>
                </a>
                """ % (f"image-{instance.pk}", lettre.lettre.url, lettre.lettre.url)
        return html

    def get_entry_type(self, instance, **kwargs):
        if instance.type:
            return instance.get_type_display()
        return ""

    def get_entry_status(self, instance, **kwargs):
        return renderStatus(instance)

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-dmnd-rv-actions.html", {'demande': instance,
                                                                           "user": self.view.request.user})


class DemandeRendezVousDatatableView(TemplateVersionMixin, DatatableView):
    template_name = "doctor/rdv_demands.html"
    model = DemandeRendezVous
    datatable_class = DemandeRendezVousDatatable

    @method_decorator(login_required)
    @method_decorator(is_doctor)
    @method_decorator(has_access(EtabibService.ETABIB_CARE))
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DemandeRendezVousDatatableView, self).get_context_data(**kwargs)
        context['title'] = "Demandes de Rendez-Vous"
        context['sidebar_metting'] = True
        context.update({
            "step1": RendezVousDoctorCreateFormStep1(), "step2": RendezVousDoctorCreateFormStep2(),
        })
        return context

    def get_queryset(self):
        if self.user:
            return DemandeRendezVous.objects.filter(destinataire=self.user)
        return DemandeRendezVous.objects.all()


class RendezVousProcessView(SuccessMessageMixin, AjaxUpdateView):
    form_class = TraiterRendezVousForm
    model = DemandeRendezVous
    success_message = "Demande Traitée!"

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        if not self.get_object().destinataire == request.user:
            return self.render_json_response({'status': 'error', 'message': "403 UNAUTHORIZED"})
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(RendezVousProcessView, self).get_form_kwargs()
        if is_partner(self.user):
            kwargs.update({"hide_type": True})
        if self.object:
            kwargs.update({"NOT_ENOUGH_MONEY": False})
            self.NOT_ENOUGH_MONEY = False
            if hasattr(self.object.demandeur, "patient") and hasattr(self.object.destinataire, "medecin"):
                if not hasEnoughMoney(self.object.demandeur.patient, self.object.destinataire.medecin):
                    kwargs.update({"NOT_ENOUGH_MONEY": True})
                    self.NOT_ENOUGH_MONEY = True

        return kwargs

    def form_valid(self, form):
        tDemande = None
        demande = form.save(commit=False)
        refusee = form.cleaned_data['refusee']
        if not refusee:
            demande.acceptee = True
            if self.NOT_ENOUGH_MONEY:
                demande.gratuit = True

            if hasattr(demande.demandeur, "patient") and hasattr(demande.destinataire, "medecin"):
                # create TeleconsultationDemand object after accepting the demande RDV
                tDemande = Tdemand()
                tDemande.medecin = demande.destinataire.medecin
                tDemande.patient = demande.demandeur.patient
                tDemande.rendez_vous = demande
                tDemande.acceptee = True
                tDemande.createRoom()

        demande.date_traitement = timezone.now()
        demande.save()
        if tDemande:
            tDemande.skip_signal = True  # to skip signal from triggering
            tDemande.save()

        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(self.get_success_result())


@login_required
def fetchAppointmentsEvents(request):
    from datetime import datetime as dt
    from django.utils.timezone import make_aware
    if request.is_ajax():
        start = request.GET.get('start', False)
        end = request.GET.get('end', False)
        startDate = make_aware(dt.fromtimestamp(int(start)))
        endDate = make_aware(dt.fromtimestamp(int(end)))

        demands = DemandeRendezVous.objects.filter(
            Q(destinataire=request.user) | Q(demandeur=request.user)
        ).filter(
            acceptee=True,
            refusee=False,
            annulee=False,
            date_rendez_vous__isnull=False,
            date_rendez_vous__lte=endDate,
            date_rendez_vous__gte=startDate,
        ).distinct()

        datas = []
        if request.user.is_authenticated:
            for demand in demands:
                data = {}
                data['editable'] = False
                data['title'] = getEventTitle(demand, request.user)
                data['description'] = data['title']
                data['start'] = demand.date_rendez_vous
                data['color'] = getEventColor(demand)
                data['icon'] = getEventIcon(demand)
                data['url'] = "#"
                datas.append(data)
            return JsonResponse(datas, safe=False)
        else:
            return JsonResponse({'error': _("Forbidden")}, status=403)


@login_required
@is_doctor
@has_access(EtabibService.ONLINE_AGENDA)
def AppointmentEvents(request):
    conext = {
        'title': _('events'),
        'sidebar_appoinments': True
    }
    if request.template_version == "v2":
        return render(request, "doctor/agenda.html", conext, using=request.template_version)
    return render(request, "events.html", conext, using=request.template_version)


class RecentlyPatientAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Patient.objects.none()
        qs = Patient.objects.filter(Q(user__applicant_drdv__destinataire=self.request.user) |
                                    Q(tdemand__medecin__user=self.request.user) |
                                    Q(cree_par=self.request.user)).distinct()
        if self.q:
            qs = qs.filter(
                Q(user__first_name__istartswith=self.q) | Q(user__last_name__istartswith=self.q)
            )
        return qs


class CreateAppointmentView(SuccessMessageMixin, AjaxCreateView):
    form_class = CreateAppointmentForm
    model = DemandeRendezVous
    success_message = "Rendez-vous Crée!"

    @method_decorator(login_required)
    @method_decorator(is_doctor)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(CreateAppointmentView, self).get_form_kwargs()
        return kwargs

    def form_valid(self, form):
        demande = form.save(commit=False)
        patient = form.cleaned_data['patient']
        demande.destinataire = self.user
        demande.demandeur = patient.user
        demande.date_traitement = timezone.now()
        demande.skip_signal = True  # to skip signal from triggering
        demande.acceptee = True
        demande.save()

        tDemande = Tdemand()
        tDemande.medecin = demande.destinataire.medecin
        tDemande.acceptee = True
        tDemande.patient = patient
        tDemande.rendez_vous = demande
        tDemande.skip_signal = True  # to skip signal from triggering
        tDemande.createRoom()
        tDemande.save()

        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(self.get_success_result())


@login_required
def create_dmd_rdv(request):
    key = request.POST['pk']
    type = request.POST.get("type_rdv", None)
    lettre = request.FILES.get("lettre", None)
    patient = get_object_or_404(Patient, pk=key)
    demande = DemandeRendezVous()
    if lettre:
        demande.lettre_orientation = lettre
    demande.type = type
    demande.destinataire = request.user
    demande.demandeur = patient.user
    demande.date_traitement = timezone.now()
    demande.skip_signal = False  # to skip signal from triggering
    demande.save()
    return JsonResponse({'sucuss': 'sucuss'}, status=200, safe=False)


@login_required
def qrCodeReader(request):
    if request.is_ajax():
        key = request.POST['pk']
        try:
            patient = Patient.objects.get(pk=offer_id_unhash(key))
            data = {}
            dmnds = DemandeRendezVous.objects.filter(
                destinataire=request.user,
                demandeur=patient.user,
                acceptee=False,
                refusee=False,
                annulee=False
            )
            if dmnds.exists():
                data['rdv'] = dmnds.first().id
            else:
                data['rdv'] = None
            if patient:
                data['pk'] = patient.pk
                data['full_name'] = patient.full_name
                if patient.date_naissance:
                    data['age'] = patient.age()
                if patient.nin:
                    data['nin'] = patient.nin
                if patient.chifa:
                    data['chifa'] = patient.chifa
                return JsonResponse({'patient': data}, status=200)
        except ObjectDoesNotExist as e:
            return JsonResponse({'error': 'error'}, status=404)


@login_required
def doctor_dmd_rdv_can(request):
    key = request.POST['key']
    demande = DemandeRendezVous.objects.get(pk=key)
    demande.annulee = True
    demande.save()
    return JsonResponse({'sucuss': None}, status=200, safe=False)
