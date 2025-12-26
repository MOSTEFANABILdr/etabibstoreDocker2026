# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from allauth.account.models import EmailAddress
from datatableview import columns
from datatableview.datatables import Datatable
from datatableview.views import DatatableView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View
from fm.views import AjaxUpdateView, AjaxCreateView, AjaxDeleteView

from core.decorators import is_operator
from core.enums import Role
from core.models import Action, DetailAction, DetailActionFile, Contact, Operateur, DemandeIntervention, ListeProspect
from core.models import ProchaineRencontre, Prospect, CarteProfessionnelle, Medecin
from core.templatetags.event_tags import is_tech_intervention, is_punctual_tracking, is_active_tracking, is_formation, \
    is_commercial_request
from core.templatetags.role_tags import has_no_role, has_group
from core.utils import getEventColor, getEventIcon, getEventTitle, convert_distance
from crm.enums import EventType
from crm.forms.operator_forms import ActionUpdateForm, ActionCreateForm, DetailActionForm, \
    DetailActionFileForm, InactivateActionForm, DetailActionAudioFileForm, DelegueStep1Form, DelegueStep2Form, \
    DelegueStep3Form
from crm.forms.operator_forms import CreatePisteForm, ProspectForm, ProchaineRencontreForm, \
    TreatProchaineRencontreForm, ClotureActionForm, ProlongerPisteForm
from crm.templatetags.agenda_tags import renderMobileStatus
from crm.views.contact_views import _filter_contacts
from etabibWebsite import settings


@login_required
@is_operator
def events(request):
    conext = {
        'title': _('events'),
        'sidebar_events': True
    }

    return render(request, "events.html", conext)


@login_required
@is_operator
def fetchEvents(request):
    if request.is_ajax():
        datas = []
        if request.user.has_perm("core.crm_can_view_comn_agenda"):
            start = request.GET.get('start', False)
            end = request.GET.get('end', False)
            startDate = datetime.fromtimestamp(int(start))
            endDate = datetime.fromtimestamp(int(end))

            ct_user = ContentType.objects.get_for_model(request.user)
            groupe = Group.objects.get(name=Role.COMMUNICATION.value)
            ct_group = ContentType.objects.get_for_model(groupe)

            actions = Action.objects.filter(
                (
                        Q(date_debut__lte=endDate, date_debut__gte=startDate) |
                        Q(date_fin__lte=endDate, date_fin__gte=startDate) |
                        Q(date_debut__lte=startDate, date_fin__gte=startDate) |
                        Q(date_debut__lte=endDate, date_fin__gte=endDate)
                ) &
                ((
                         Q(attribuee_a_type=ct_user, attribuee_a_id=request.user.id) |
                         Q(attribuee_a_type=ct_group, attribuee_a_id=groupe.id)
                 ) | (
                         Q(cree_par__user=request.user)
                         | Q(cree_par__user__groups__in=[groupe])
                 ))).distinct()

            actions = actions.filter(Q(type__in=["2", "3", "4", "5"]) & Q(active=True))

            dis = DemandeIntervention.objects.filter(date_demande__lte=endDate, date_demande__gte=startDate)

            for action in actions:
                show_detail = False
                if is_commercial_request(action) or is_tech_intervention(action) or is_formation(action):
                    if action.detail_set.count() == 0:
                        data = {}
                        data['title'] = getEventTitle(action)
                        data['description'] = data['title']
                        data['start'] = datetime.combine(action.date_debut, action.date_debut_time).isoformat()
                        data['end'] = datetime.combine(action.date_fin, action.date_fin_time).isoformat()
                        data['color'] = getEventColor(action)
                        data['icon'] = getEventIcon(action)
                        data['url'] = reverse('action-detail', kwargs={'pk': action.pk})
                        datas.append(data)
                    else:
                        show_detail = True
                if is_punctual_tracking(action) or show_detail:
                    detail = action.detail_set.last()
                    if detail:
                        data = {}
                        data['editable'] = True
                        data['event_id'] = detail.id
                        data['title'] = getEventTitle(detail)
                        data['description'] = data['title']
                        if hasattr(detail, 'prochainerencontre'):
                            data['start'] = detail.prochainerencontre.date_rencontre.isoformat()
                            data['end'] = detail.prochainerencontre.date_rencontre.isoformat()
                            data['event_type'] = EventType.PROCHAINE_RENCONTRE.value
                        else:
                            data['start'] = detail.date_creation.date().isoformat()
                            data['end'] = detail.date_creation.date().isoformat()
                            data['event_type'] = EventType.DETAIL_ACTION.value
                        data['color'] = getEventColor(detail)
                        data['icon'] = getEventIcon(detail)
                        data['url'] = reverse('action-detail',
                                              kwargs={'pk': action.pk}) + "?scrl=detail_%s" % detail.id
                        datas.append(data)
            for di in dis:
                data = {}
                data['editable'] = False
                data['title'] = getEventTitle(di)
                data['description'] = data['title']
                data['start'] = di.date_demande.isoformat()
                data['end'] = di.date_demande.isoformat()
                data['color'] = getEventColor(di)
                data['icon'] = getEventIcon(di)
                data['url'] = reverse('demande-intervention-detail', kwargs={'pk': di.pk})
                datas.append(data)
        if request.user.has_perm("core.crm_can_view_comm_agenda"):
            start = request.GET.get('start', False)
            end = request.GET.get('end', False)
            startDate = datetime.fromtimestamp(int(start))
            endDate = datetime.fromtimestamp(int(end))

            ct_user = ContentType.objects.get_for_model(request.user)
            groupe = Group.objects.get(name=Role.COMMERCIAL.value)
            ct_group = ContentType.objects.get_for_model(groupe)

            actions = Action.objects.filter(
                (
                        Q(date_debut__lte=endDate, date_debut__gte=startDate) |
                        Q(date_fin__lte=endDate, date_fin__gte=startDate) |
                        Q(date_debut__lte=startDate, date_fin__gte=startDate) |
                        Q(date_debut__lte=endDate, date_fin__gte=endDate)
                ) &
                (
                        Q(attribuee_a_type=ct_user, attribuee_a_id=request.user.id) |
                        Q(attribuee_a_type=ct_group, attribuee_a_id=groupe.id)
                )
            ).distinct()
            actions = actions.filter(type__in=["1", "4", "5"], active=True)  # Suivi Actif or Demande commercial

            for action in actions:
                show_detail = False
                if is_commercial_request(action) or is_formation(action):
                    if action.detail_set.count() == 0:
                        data = {}
                        data['editable'] = False
                        data['title'] = getEventTitle(action)
                        data['description'] = data['title']
                        data['start'] = datetime.combine(action.date_debut, action.date_debut_time).isoformat()
                        data['end'] = datetime.combine(action.date_fin, action.date_fin_time).isoformat()
                        data['color'] = getEventColor(action)
                        data['icon'] = getEventIcon(action)
                        data['url'] = reverse('action-detail', kwargs={'pk': action.pk})
                        datas.append(data)
                    else:
                        show_detail = True
                if is_active_tracking(action) or show_detail:
                    detail = action.detail_set.last()
                    if detail:
                        data = {}
                        data['title'] = getEventTitle(detail)
                        data['description'] = data['title']
                        if hasattr(detail, 'facture') or hasattr(detail, 'clotureaction'):
                            data['start'] = detail.date_creation.date().isoformat()
                            data['end'] = detail.date_creation.date().isoformat()
                        elif hasattr(detail, 'prochainerencontre'):
                            data['editable'] = True
                            data['event_id'] = detail.id
                            data['event_type'] = EventType.PROCHAINE_RENCONTRE.value
                            data['start'] = detail.prochainerencontre.date_rencontre.isoformat()
                            data['end'] = detail.prochainerencontre.date_rencontre.isoformat()
                        else:
                            data['editable'] = True
                            data['event_id'] = detail.id
                            data['event_type'] = EventType.DETAIL_ACTION.value
                            data['start'] = detail.date_creation.date().isoformat()
                            data['end'] = detail.date_creation.date().isoformat()
                        data['color'] = getEventColor(detail)
                        data['icon'] = getEventIcon(detail)
                        data['url'] = reverse('action-detail',
                                              kwargs={'pk': action.pk}) + "?scrl=detail_%s" % detail.id
                        datas.append(data)
        if request.user.has_perm("core.crm_can_view_tech_agenda"):
            start = request.GET.get('start', False)
            end = request.GET.get('end', False)
            startDate = datetime.fromtimestamp(int(start))
            endDate = datetime.fromtimestamp(int(end))

            ct_user = ContentType.objects.get_for_model(request.user)
            groupe = Group.objects.get(name=Role.TECHNICIAN.value)
            ct_group = ContentType.objects.get_for_model(groupe)

            actions = Action.objects.filter(
                (
                        Q(date_debut__lte=endDate, date_debut__gte=startDate) |
                        Q(date_fin__lte=endDate, date_fin__gte=startDate)
                ) &
                (
                        Q(attribuee_a_type=ct_user, attribuee_a_id=request.user.id) |
                        Q(attribuee_a_type=ct_group, attribuee_a_id=groupe.id)
                )
            ).distinct()
            actions = actions.filter(type__in=["3"], active=True)
            for action in actions:
                data = {}
                data['editable'] = False
                data['title'] = getEventTitle(action)
                data['description'] = data['title']
                data['start'] = datetime.combine(action.date_debut, action.date_debut_time).isoformat()
                data['end'] = datetime.combine(action.date_fin, action.date_fin_time).isoformat()
                data['color'] = getEventColor(action)
                data['icon'] = getEventIcon(action)
                data['url'] = reverse('action-detail', kwargs={'pk': action.pk})
                datas.append(data)

        if request.user.has_perm("core.crm_can_view_delg_agenda"):
            print("herere")
            start = request.GET.get('start', False)
            end = request.GET.get('end', False)
            startDate = datetime.fromtimestamp(int(start))
            endDate = datetime.fromtimestamp(int(end))

            ct_user = ContentType.objects.get_for_model(request.user)

            actions = Action.objects.filter(
                (
                        Q(date_debut__lte=endDate, date_debut__gte=startDate) |
                        Q(date_fin__lte=endDate, date_fin__gte=startDate) |
                        Q(date_debut__lte=startDate, date_fin__gte=startDate) |
                        Q(date_debut__lte=endDate, date_fin__gte=endDate)
                ) &
                (
                    Q(attribuee_a_type=ct_user, attribuee_a_id=request.user.id)
                )
            ).distinct()
            actions = actions.filter(type__in=["1", "4", "5"], active=True)  # Suivi Actif or Demande commercial

            for action in actions:
                show_detail = False
                if is_commercial_request(action) or is_formation(action):
                    if action.detail_set.count() == 0:
                        data = {}
                        data['editable'] = False
                        data['title'] = getEventTitle(action)
                        data['description'] = data['title']
                        data['start'] = datetime.combine(action.date_debut, action.date_debut_time).isoformat()
                        data['end'] = datetime.combine(action.date_fin, action.date_fin_time).isoformat()
                        data['color'] = getEventColor(action)
                        data['icon'] = getEventIcon(action)
                        data['url'] = reverse('action-detail', kwargs={'pk': action.pk})
                        datas.append(data)
                    else:
                        show_detail = True
                if is_active_tracking(action) or show_detail:
                    detail = action.detail_set.last()
                    if detail:
                        data = {}
                        data['title'] = getEventTitle(detail)
                        data['description'] = data['title']
                        if hasattr(detail, 'facture') or hasattr(detail, 'clotureaction'):
                            data['start'] = detail.date_creation.date().isoformat()
                            data['end'] = detail.date_creation.date().isoformat()
                        elif hasattr(detail, 'prochainerencontre'):
                            data['editable'] = True
                            data['event_id'] = detail.id
                            data['event_type'] = EventType.PROCHAINE_RENCONTRE.value
                            data['start'] = detail.prochainerencontre.date_rencontre.isoformat()
                            data['end'] = detail.prochainerencontre.date_rencontre.isoformat()
                        else:
                            data['editable'] = True
                            data['event_id'] = detail.id
                            data['event_type'] = EventType.DETAIL_ACTION.value
                            data['start'] = detail.date_creation.date().isoformat()
                            data['end'] = detail.date_creation.date().isoformat()
                        data['color'] = getEventColor(detail)
                        data['icon'] = getEventIcon(detail)
                        data['url'] = reverse('action-detail',
                                              kwargs={'pk': action.pk}) + "?scrl=detail_%s" % detail.id
                        datas.append(data)

        return JsonResponse(datas, safe=False)


@login_required
@is_operator
def updateEvent(request):
    from pytz import timezone

    if request.is_ajax():
        not_acceptable = False
        event_id = request.POST.get("event_id", None)
        event_type = request.POST.get("event_type", None)
        start = request.POST.get('start', None)
        end = request.POST.get('end', None)

        if event_type:
            detail = get_object_or_404(DetailAction, id=event_id)
            if start:
                startDate = datetime.fromtimestamp(int(start), timezone(settings.TIME_ZONE))
                if event_type == EventType.DETAIL_ACTION.value:
                    if detail.action.detail_set.exclude(detail).filter(date_creation__gte=startDate):
                        not_acceptable = True
                    else:
                        with transaction.atomic():
                            detail.date_creation = startDate
                            detail.save()
                            if detail.action.date_fin < startDate.date():
                                detail.action.date_fin = startDate.date()
                                detail.action.date_fin_time = startDate.time()
                                detail.action.save()

                elif event_type == EventType.PROCHAINE_RENCONTRE.value:
                    if detail.prochainerencontre.date_rencontre > startDate.date():
                        not_acceptable = True
                    else:
                        with transaction.atomic():
                            detail.prochainerencontre.date_rencontre = startDate.date()
                            detail.prochainerencontre.save()
                            if detail.action.date_fin < startDate.date():
                                detail.action.date_fin = startDate.date()
                                detail.action.date_fin_time = startDate.time()
                                detail.action.save()

                if not_acceptable:
                    return JsonResponse({}, status=406)

            return JsonResponse({}, status=200)
        else:
            return JsonResponse({}, status=400)


#############################################
# Expired suivi ponctuel.
#############################################
class ExpiredEventDatatable(Datatable):
    nom = columns.TextColumn(sources=['contact__nom'])
    prenom = columns.TextColumn(sources=['contact__prenom'])
    date_fin = columns.TextColumn(_("Date de dernier contact"), sources=['date_fin'])
    contact = columns.TextColumn(_("Contact"), source=None, processor='get_entry_contact')
    actions = columns.TextColumn(_("Actions"), sources=None, processor='get_entry_action')

    class Meta:
        columns = ["contact", "date_fin", "actions"]
        search_fields = ["contact__nom", "contact__prenom"]
        hidden_columns = ["nom", "prenom"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['date_fin']
        page_length = 5

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-expired-ponctual-events-actions.html", {'action': instance})

    def get_entry_contact(self, instance, **kwargs):
        return "<a href='{}'>{}</a>".format(
            reverse('operator-detail-contact', args=(instance.contact.id,)), instance.contact.full_name
        )


class ExpiredEventDatatableView(DatatableView):
    model = Action
    datatable_class = ExpiredEventDatatable

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super(ExpiredEventDatatableView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Action.objects.filter(
            Q(type__in=["2"]) & Q(active=True) & Q(date_fin__lt=timezone.now().date())
        ).distinct()


#############################################
# Piste
#############################################

class PisteDatatable(Datatable):
    actions = columns.TextColumn(_("Actions"), source=None, processor='get_entry_action')
    contact_nom = columns.TextColumn(source=['contact__nom'])
    contact_prenom = columns.TextColumn(source=['contact__prenom'])
    date_creation = columns.TextColumn(_("Date de création"), source=None, processor='get_entry_date_creation')
    active = columns.TextColumn(_("Active"), source=None, processor='get_entry_active')
    type = columns.TextColumn(_("Type"), source=None, processor='get_entry_type')
    score = columns.IntegerColumn(_("Score"), sources=["contact__score"])

    class Meta:
        columns = ["contact", "score", "date_debut", "date_fin", "type", "active", "actions"]
        hidden_columns = ["contact_nom", "contact_prenom"]
        search_fields = ["id", 'contact__nom', 'contact__prenom']
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 20

    def get_entry_date_creation(self, instance, **kwargs):
        if instance.date_creation:
            return instance.date_creation.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_entry_active(self, instance, **kwargs):
        if instance.active:
            return "<i class='fa fa-check green'></i>"
        return "<i class='fa fa-remove red'></i>"

    def get_entry_type(self, instance, **kwargs):
        return instance.get_type_display()

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-pistes-actions.html",
                                {'action': instance, "user": self.view.request.user})


class PisteDatatableView(DatatableView):
    template_name = "commercial/piste-list.html"
    model = Action
    datatable_class = PisteDatatable

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.contact_pk = kwargs['contact_pk'] if 'contact_pk' in kwargs else None
        self.contact = None
        if self.contact_pk:
            try:
                self.contact = Contact.objects.get(pk=self.contact_pk)
            except Action.DoesNotExist:
                pass
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(PisteDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Listes des pistes")
        context['com_sidebar_list_piste'] = True
        context['contact'] = self.contact
        return context

    def get_queryset(self):
        if self.request.user.has_perm("core.crm_can_manage_pistes"):
            actions = Action.objects.filter(Q(contact=self.contact))
        else:
            ct_user = ContentType.objects.get_for_model(self.request.user)
            actions = Action.objects.filter(Q(attribuee_a_type=ct_user, attribuee_a_id=self.request.user.id) &
                                            Q(contact=self.contact))
        return actions


class PisteCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = CreatePisteForm
    model = Action
    success_message = _("Piste créée avec succès")
    error_message = _("Il existe une piste pour le même prospect  avec la même intervalle de date")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.contact_pk = kwargs['contact_pk'] if 'contact_pk' in kwargs else None
        if self.contact_pk:
            self.contact = get_object_or_404(Contact, id=self.contact_pk)
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        date_debut = form.cleaned_data["date_piste"]
        date_fin = date_debut + timedelta(days=15)

        # Check if date_debut < today
        if date_debut < timezone.now().date():
            messages.error(self.request, _("La date doit être > la date d'aujourd'hui"))
            return self.render_json_response({'status': 'ok', 'message': reverse("commercial-list-prospect")})

        # Check if another piste exists
        ats = Action.objects.filter(
            Q(contact=self.contact, date_debut__range=[date_debut, date_fin])
            | Q(contact=self.contact, date_fin__range=[date_debut, date_fin])
            | Q(contact=self.contact, date_debut__lte=date_debut, date_fin__gte=date_fin)
        )
        if ats.filter(type=Action.CHOICES[0][0]).exists():
            error_message = self.error_message
            if error_message:
                messages.error(self.request, error_message)
            return self.render_json_response({'status': 'ok', 'message': reverse("commercial-list-prospect")})

        # create piste
        with transaction.atomic():
            action = Action()
            action.cree_par = self.request.user.operateur
            action.contact = self.contact
            action.type = "1"  # suivi actif
            action.attribuee_a = self.request.user
            action.date_debut = date_debut
            action.date_fin = date_fin
            action.save()

            detail = DetailAction()
            detail.cree_par = self.request.user.operateur
            detail.type = "0"  # Prospection
            detail.action = action
            detail.save()

            rencontre = ProchaineRencontre()
            rencontre.detail_action = detail
            rencontre.date_rencontre = date_debut
            rencontre.save()

            success_message = self.get_success_message(form.cleaned_data)
            if success_message:
                messages.success(self.request, success_message)
            return self.render_json_response(
                {
                    'status': 'ok',
                    'message': reverse('action-detail', kwargs={'pk': action.id})
                }
            )


class PisteBulkCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = CreatePisteForm
    model = Action
    success_message = _("Pistes créées avec succès")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.list_pk = kwargs['list_pk'] if 'list_pk' in kwargs else None
        if self.list_pk:
            self.listeProspect = get_object_or_404(ListeProspect, id=self.list_pk)
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        date_debut = form.cleaned_data["date_piste"]
        date_fin = date_debut + timedelta(days=15)

        # Check if date_debut < today
        if date_debut < timezone.now().date():
            messages.error(self.request, _("La date doit être > la date d'aujourd'hui"))
            return self.render_json_response({'status': 'ok', 'message': reverse("commercial-list-prospect")})

        for prospect in self.listeProspect.prospect_set.all():
            # Check if another piste exists
            contact = prospect.contact
            ats = Action.objects.filter(
                Q(contact=contact, date_debut__range=[date_debut, date_fin])
                | Q(contact=contact, date_fin__range=[date_debut, date_fin])
                | Q(contact=contact, date_debut__lte=date_debut, date_fin__gte=date_fin)
            ).filter(type=Action.CHOICES[0][0])
            if ats.exists():
                #if a piste exists add a detail
                detail = DetailAction()
                detail.cree_par = self.request.user.operateur
                detail.type = "0"  # Prospection
                detail.action = ats.last()
                detail.save()

                rencontre = ProchaineRencontre()
                rencontre.detail_action = detail
                rencontre.date_rencontre = date_debut
                rencontre.save()
            else:
                # create piste
                with transaction.atomic():
                    action = Action()
                    action.cree_par = self.request.user.operateur
                    action.contact = contact
                    action.type = "1"  # suivi actif
                    action.attribuee_a = self.request.user
                    action.date_debut = date_debut
                    action.date_fin = date_fin
                    action.save()

                    detail = DetailAction()
                    detail.cree_par = self.request.user.operateur
                    detail.type = "0"  # Prospection
                    detail.action = action
                    detail.save()

                    rencontre = ProchaineRencontre()
                    rencontre.detail_action = detail
                    rencontre.date_rencontre = date_debut
                    rencontre.save()

        self.listeProspect.traite = True
        self.listeProspect.save()

        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(
            {
                'status': 'ok',
                'message': reverse('commercial-list-prospect')
            }
        )




class DetailPisteCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = DetailActionForm
    model = DetailAction
    success_message = _("Détail Piste créée avec succès")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.action_id = kwargs['action_id'] if 'action_id' in kwargs else None
        if self.action_id:
            try:
                self.action = Action.objects.get(pk=self.action_id)
            except Action.DoesNotExist:
                pass
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(DetailPisteCreateView, self).get_form_kwargs()
        if self.action:
            if is_active_tracking(self.action):
                kwargs.update({"type_choices": DetailAction.TYPE_CHOICES_CMR})
            if is_punctual_tracking(self.action):
                kwargs.update({"type_choices": DetailAction.TYPE_CHOICES_CMN})
            if is_tech_intervention(self.action):
                kwargs.update({"type_choices": DetailAction.TYPE_CHOICES_TEC})
            if has_group(self.operateur.user, Role.DELEGUE_COMMERCIAL.value):
                kwargs.update({"is_delegue": True})
        return kwargs

    def form_valid(self, form):
        detail_action = form.save(commit=False)
        detail_action.cree_par = self.operateur
        file = form.getFile()
        if file:
            try:
                daf = DetailActionFile.objects.get(pk=file)
                detail_action.pj = daf
            except Exception:
                pass
        if self.action:
            detail_action.action = self.action
        detail_action.save()
        return super().form_valid(form)


#############################################
# Prospect
#############################################


class ProspectCreateView(AjaxCreateView):
    form_class = ProspectForm
    model = Prospect
    success_message = _("%s est ajouté à votre liste des prospects %s avec succès")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.contact_pk = kwargs['contact_pk'] if 'contact_pk' in kwargs else None
        self.contact = None
        if self.contact_pk:
            try:
                self.contact = Contact.objects.get(pk=self.contact_pk)
            except Action.DoesNotExist:
                pass
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(ProspectCreateView, self).get_form_kwargs()
        kwargs['list_is_required'] = self.operateur.liste_prospect.count() > 0
        kwargs['operateur'] = self.operateur

        return kwargs

    def get_initial(self):
        context = {}
        if self.contact:
            context["contact"] = self.contact
        return context

    def form_valid(self, form):
        prospect = form.save(commit=False)
        prospect.cree_par = self.operateur
        lp = None
        if not prospect.liste:
            lp = ListeProspect()
            lp.cree_par = self.operateur
            lp.save()
            prospect.liste = lp
        else:
            lp = prospect.liste
        prospect.save()
        self.success_message = self.success_message % (prospect.contact, f"{lp.titre}" if lp else "")
        return super().form_valid(form)

    def get_response_message(self):
        return self.success_message


class ProspectDeleteView(AjaxDeleteView):
    form_class = ProspectForm
    model = Prospect
    success_message = _("%s est supprimé de votre liste des prospects avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message % self.get_object())
        return super(ProspectDeleteView, self).delete(request, *args, **kwargs)


class ProspectDatatable(Datatable):
    actions = columns.TextColumn(_("Actions"), source=None, processor='get_entry_action')
    telephone = columns.TextColumn(_("Telephone"), source=None, processor='get_telephone')
    distance = columns.TextColumn(_("Distance"), source=None, processor='get_distance')
    contact_nom = columns.TextColumn(source=['contact__nom'])
    contact_prenom = columns.TextColumn(source=['contact__prenom'])
    date_creation = columns.DateTimeColumn(_("Date d'ajout"), source="date_creation")
    score = columns.IntegerColumn(_("Score"), sources=["contact__score"])
    cree_par = columns.IntegerColumn(_("Ajouté par"), sources=["cree_par"])

    class Meta:
        columns = ["contact", "score", "distance", "cree_par", "date_creation", "telephone", "actions"]
        hidden_columns = ["contact_nom", "contact_prenom"]
        search_fields = ["id", 'contact__nom', 'contact__prenom']
        structure_template = "partial/datatable-bootstrap-structure.html"
        # ordering = ['-distance']
        page_length = 20

    def get_distance(self, instance, **kwargs):
        return convert_distance(instance.distance) if hasattr(instance, "distance") else ""

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-prospects-actions.html",
                                {'prospect': instance, "user": self.view.request.user})

    def get_telephone(self, instance, **kwargs):
        return renderMobileStatus(instance)


class ProspectDatatableView(DatatableView):
    template_name = "commercial/prospect-list.html"
    model = Prospect
    datatable_class = ProspectDatatable

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.list_id = kwargs['list_id'] if 'list_id' in kwargs else None
        self.list_prospect = None
        if self.list_id:
            self.list_prospect = ListeProspect.objects.filter(id=self.list_id).first()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ProspectDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Listes des prospect")
        context['list_title'] = self.list_prospect.titre if self.list_prospect else ""
        context['com_sidebar_list_prospect'] = True
        return context

    def get_queryset(self):
        if self.request.user.has_perm("core.crm_can_manage_prospect_list"):
            prs = Prospect.objects.all()
        else:
            prs = Prospect.objects.filter(cree_par__user=self.request.user)

        if self.list_id:
            listeProspect = get_object_or_404(ListeProspect, id=self.list_id)
            prs = prs.filter(liste__id = self.list_id)
            if listeProspect.commune:
                ref_location = Point(float(listeProspect.commune.latitude), float(listeProspect.commune.longitude), srid=4326)
                prs = prs.annotate(
                    distance=Distance("contact__geo_coords", ref_location)
                ).order_by('distance')
        return prs


@login_required
@is_operator
def create_prospect_list(request):
    if request.is_ajax():
        qs, max_prospect = _filter_contacts(request.POST)

        specialite_q = request.POST.get("specialite_q", None)
        commune_depart = request.POST.get("commune_depart", None)
        with transaction.atomic():
            counter = 0
            lp = None
            for contact in qs:
                if counter == 0:
                    lp = ListeProspect()
                    if commune_depart:
                        lp.commune_id = commune_depart
                    if specialite_q:
                        lp.specialite_id = specialite_q
                    lp.cree_par = request.user.operateur
                    lp.save()

                if hasattr(contact, "prospect"):
                    if contact.prospect.cree_par.user == request.user:
                        contact.prospect.liste = lp
                        contact.prospect.save()
                        counter += 1
                else:
                    p = Prospect()
                    p.cree_par = request.user.operateur
                    p.contact = contact
                    p.liste = lp
                    p.save()

                    counter += 1

                if counter == max_prospect:
                    counter = 0

            return JsonResponse({"redirection_url": reverse('commercial-list-prospect')}, status=200, safe=False)
    return JsonResponse({}, status=400, safe=False)


class ProspectListDatatable(Datatable):
    actions = columns.TextColumn(_("Actions"), source=None, processor='get_entry_action')
    date_creation = columns.DateTimeColumn(_("Date de création"), source="date_creation")
    cree_par = columns.IntegerColumn(_("Ajouté par"), sources=["cree_par"])
    title = columns.TextColumn(_("N° Liste"), source="titre")
    commune_nom = columns.TextColumn(source="commune__nom")
    nb = columns.TextColumn(_("Nb prospect"), source=None, processor='get_entry_prospect')
    specialite_nom = columns.TextColumn(source="specialite__libelle")

    class Meta:
        columns = ["title", "cree_par", "date_creation", "commune", "specialite", "nb", "actions"]
        hidden_columns = ["commune_nom", "specialite_nom"]
        search_fields = ["id", "specialite__libelle", "commune__nom"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-date_creation']
        page_length = 20

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-prospects-actions.html",
                                {'listeProspect': instance, "user": self.view.request.user, "is_list": True})

    def get_entry_commune(self, instance, **kwargs):
        if instance.commune:
            return instance.commune.nom
        return ""

    def get_entry_specialite(self, instance, **kwargs):
        if instance.specialite:
            return instance.specialite
        return ""

    def get_entry_prospect(self, instance, **kwargs):
        return instance.prospect_set.count()


class ProspectListDatatableView(DatatableView):
    template_name = "commercial/prospect-list-v2.html"
    model = ListeProspect
    datatable_class = ProspectListDatatable

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ProspectListDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Listes des prospect")
        context['com_sidebar_list_prospect'] = True
        return context

    def get_queryset(self):
        if self.request.user.has_perm("core.crm_can_manage_prospect_list"):
            prs = ListeProspect.objects.all()
        else:
            prs = ListeProspect.objects.filter(cree_par__user=self.request.user)
        return prs


class ProspectListDeleteView(AjaxDeleteView):
    model = ListeProspect
    success_message = _("%s est supprimé de votre liste des prospects avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message % self.get_object())
        return super(ProspectListDeleteView, self).delete(request, *args, **kwargs)

##########################
# Prochaine Rencontre
##########################
class ProchaineRencontreCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = ProchaineRencontreForm
    model = ProchaineRencontre
    success_message = _("Prochaine Rencontre créée avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.action_id = kwargs['action_id'] if 'action_id' in kwargs else None
        if self.action_id:
            try:
                self.action = Action.objects.get(pk=self.action_id)
            except Action.DoesNotExist:
                pass
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(ProchaineRencontreCreateView, self).get_form_kwargs()
        if self.action:
            if is_active_tracking(self.action):
                kwargs.update({"type_choices": DetailAction.TYPE_CHOICES_CMR})
            if is_punctual_tracking(self.action):
                kwargs.update({"type_choices": DetailAction.TYPE_CHOICES_CMN})
            if is_tech_intervention(self.action):
                kwargs.update({"type_choices": DetailAction.TYPE_CHOICES_TEC})
        return kwargs

    def form_valid(self, form):
        rencontre = form.save(commit=False)
        da = DetailAction()
        da.type = form.cleaned_data["type"]
        da.action = self.action
        if rencontre.date_rencontre > self.action.date_fin:
            da.action.date_fin = rencontre.date_rencontre
            da.action.save()
        da.cree_par = self.operateur
        da.save()

        rencontre.detail_action = da
        rencontre.save()
        return super().form_valid(form)


class ProchaineRencontreUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = ProchaineRencontreForm
    model = ProchaineRencontre
    success_message = _("Prochaine Rencontre mise à jour avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.action_id = kwargs['action_id'] if 'action_id' in kwargs else None
        if self.action_id:
            try:
                self.action = Action.objects.get(pk=self.action_id)
            except Action.DoesNotExist:
                pass
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super(ProchaineRencontreUpdateView, self).get_initial()
        initial['type'] = self.get_object().detail_action.type
        return initial

    def get_form_kwargs(self):
        kwargs = super(ProchaineRencontreUpdateView, self).get_form_kwargs()
        if self.action:
            if is_active_tracking(self.action):
                kwargs.update({"type_choices": DetailAction.TYPE_CHOICES_CMR})
            if is_punctual_tracking(self.action):
                kwargs.update({"type_choices": DetailAction.TYPE_CHOICES_CMN})
            if is_tech_intervention(self.action):
                kwargs.update({"type_choices": DetailAction.TYPE_CHOICES_TEC})
        return kwargs

    def form_valid(self, form):
        rencontre = form.save(commit=False)
        da = rencontre.detail_action
        da.type = form.cleaned_data["type"]
        da.action = self.action
        if rencontre.date_rencontre > self.action.date_fin:
            da.action.date_fin = rencontre.date_rencontre
            da.action.save()
        da.cree_par = self.operateur
        da.save()

        rencontre.detail_action = da
        rencontre.save()
        return super().form_valid(form)


class TreatProchaineRencontreView(SuccessMessageMixin, AjaxUpdateView):
    form_class = TreatProchaineRencontreForm
    model = DetailAction
    success_message = _("Détail Action mise à jour avec succès")
    unauthorized_message = _("Vous ne pouvez pas mettre à jour ce détail")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if request.user != self.get_object().cree_par.user:
            return self.render_json_response({'status': 'error', 'message': self.unauthorized_message})
        self.action_id = kwargs['action_id'] if 'action_id' in kwargs else None
        if self.action_id:
            try:
                self.action = Action.objects.get(pk=self.action_id)
            except Action.DoesNotExist:
                pass
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        detail_action = form.save(commit=False)
        detail_action.save()
        return super(TreatProchaineRencontreView, self).form_valid(form)


#########################
# Cloture  Action
##########################
class ClotureActionFormCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = ClotureActionForm
    model = ProchaineRencontre
    success_message = _("La piste est clôturée avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.action_id = kwargs['action_id'] if 'action_id' in kwargs else None
        if self.action_id:
            try:
                self.action = Action.objects.get(pk=self.action_id)
            except Action.DoesNotExist:
                pass
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(ClotureActionFormCreateView, self).get_form_kwargs()
        kwargs['action'] = self.action
        kwargs['is_manager'] = self.request.user.has_perm("core.crm_can_manage_pistes")
        return kwargs

    def form_valid(self, form):
        cl = form.save(commit=False)
        da = DetailAction()
        da.decision = form.cleaned_data["decision"]
        da.decision_nb_jour = form.cleaned_data["decision_nb_jour"]
        da.action = self.action
        da.cree_par = self.operateur
        da.save()

        cl.detail_action = da
        cl.save()

        self.action.active = False
        self.action.save()

        form.treatDecision()

        return super().form_valid(form)


##########################
# Prolonger Piste
##########################
class ProlongerPisteFormCreateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = ProlongerPisteForm
    model = Action
    success_message = _("La piste est prolongée à la date %s")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        action = form.save(commit=False)
        self.success_message = self.success_message % (action.date_fin)
        return super().form_valid(form)


####################################
# Agenda Actions and detail Actions
####################################
class ActionَDetailView(View):
    def get(self, request, *args, **kwargs):
        context = {'action': self.action, 'title': _("Action detail")}
        if request.user.has_perm("core.crm_timeline_can_create_untreated_order"):
            initial = {
                "email": self.action.contact.email,
                "nom": self.action.contact.nom,
                "prenom": self.action.contact.prenom,
                "telephone": self.action.contact.mobile
            }
            context.update({
                "step1": DelegueStep1Form(initial=initial), "step2": DelegueStep2Form(), "step3": DelegueStep3Form()
            })
        return render(request, 'detail-action.html', context)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        self.action = get_object_or_404(Action, pk=kwargs['pk'])
        return super(ActionَDetailView, self).dispatch(*args, **kwargs)


class ActionUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = ActionUpdateForm
    model = Action
    success_message = _("Action mise à jour avec succès")
    unauthorized_message = _("Vous ne pouvez pas mettre à jour cette action")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.action = get_object_or_404(Action, pk=kwargs['pk'])
        if self.action.cree_par.user != self.request.user:
            return self.render_json_response({'status': 'error', 'message': self.unauthorized_message})
        return super().dispatch(request, *args, **kwargs)


class AjaxableResponseMixin:
    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self.request.is_ajax():
            return JsonResponse(form.errors, status=400)
        else:
            return response

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.is_ajax():
            data = {
                'status': "success",
            }
            return JsonResponse(data)
        else:
            return response


class ActionCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = ActionCreateForm
    model = Action
    success_message = _("Demande créée avec succès")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.contact_pk = kwargs['contact_pk'] if 'contact_pk' in kwargs else None
        self.contact = None
        if self.contact_pk:
            try:
                self.contact = Contact.objects.get(pk=self.contact_pk)
            except Action.DoesNotExist:
                pass
        self.type_action = kwargs['type_action'] if 'type_action' in kwargs else None
        self.oper_pk = kwargs['oper_pk'] if 'oper_pk' in kwargs else None
        self.dmnd_interv_pk = kwargs['dmnd_interv_pk'] if 'dmnd_interv_pk' in kwargs else None
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super(ActionCreateView, self).get_form(form_class)
        # form.fields['contact'].disabled = True
        return form

    def get_form_kwargs(self):
        kwargs = super(ActionCreateView, self).get_form_kwargs()
        if self.type_action:
            kwargs.update({"type_action": self.type_action})
        if self.contact:
            kwargs.update({"hide_contact": True})
            kwargs.update({"contact": self.contact})
        if self.operateur:
            if self.operateur.user.groups.filter(name=Role.COMMUNICATION.value):
                kwargs.update({"type_choices": ["3", "4", "5"]})
        if self.oper_pk:
            kwargs.update({"hide_attr": True})
        return kwargs

    def get_initial(self):
        context = {}
        context["date_debut"] = timezone.now().date()
        context["date_fin"] = timezone.now().date()
        return context

    def form_valid(self, form):
        action = form.save(commit=False)
        action.cree_par = self.operateur
        if self.contact:
            action.contact = self.contact

        if self.oper_pk:
            operateur = get_object_or_404(Operateur, pk=self.oper_pk)
            action.attribuee_a = operateur.user
        else:
            attribuee_a = form.cleaned_data['attribuee_a']
            if attribuee_a:
                action.attribuee_a = attribuee_a.user
            else:
                if is_tech_intervention(action):
                    groupe = Group.objects.get(name=Role.TECHNICIAN.value)
                elif is_punctual_tracking(action):
                    groupe = Group.objects.get(name=Role.COMMUNICATION.value)
                elif is_active_tracking(action):
                    groupe = Group.objects.get(name=Role.COMMERCIAL.value)
                elif is_formation(action):
                    # this will raise an exception in form validation : see form's clean method
                    pass
                elif is_commercial_request(action):
                    groupe = Group.objects.get(name=Role.COMMERCIAL.value)
                    action.active = False

                action.attribuee_a = groupe

        action.save()

        if self.dmnd_interv_pk:
            DemandeIntervention.objects.filter(pk=self.dmnd_interv_pk).update(action=action)

        if is_punctual_tracking(action):
            detail = DetailAction()
            detail.action = action
            detail.type = "L"
            detail.cree_par = action.cree_par
            detail.save()
        return super().form_valid(form)

    def get_response_message(self):
        link = reverse('action-detail', kwargs={'pk': self.object.id})
        return link


class DetailActionUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = DetailActionForm
    model = DetailAction
    success_message = _("Détail Action mise à jour avec succès")
    unauthorized_message = _("Vous ne pouvez pas mettre à jour ce détail")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if request.user != self.get_object().cree_par.user:
            return self.render_json_response({'status': 'error', 'message': self.unauthorized_message})
        self.action_id = kwargs['action_id'] if 'action_id' in kwargs else None
        if self.action_id:
            try:
                self.action = Action.objects.get(pk=self.action_id)
            except Action.DoesNotExist:
                pass
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(DetailActionUpdateView, self).get_form_kwargs()
        if self.action:
            if is_active_tracking(self.action):
                kwargs.update({"type_choices": DetailAction.TYPE_CHOICES_CMR})
            if is_punctual_tracking(self.action):
                kwargs.update({"type_choices": DetailAction.TYPE_CHOICES_CMN})
            if is_tech_intervention(self.action):
                kwargs.update({"type_choices": DetailAction.TYPE_CHOICES_TEC})
        return kwargs

    def form_valid(self, form):
        detail_action = form.save(commit=False)
        file = form.getFile()
        if file:
            try:
                daf = DetailActionFile.objects.get(pk=file)
                detail_action.pj = daf
            except Exception:
                pass
        detail_action.save()
        return super(DetailActionUpdateView, self).form_valid(form)


class DetailActionDeleteView(AjaxDeleteView):
    model = DetailAction
    success_message = _("detail supprimée avec succès")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def pre_delete(self):
        if hasattr(self.get_object(), "prochainerencontre"):
            self.get_object().prochainerencontre.delete()
        if hasattr(self.get_object(), "clotureaction"):
            self.get_object().clotureaction.delete()
        if hasattr(self.get_object(), "intervention"):
            self.get_object().intervention.delete()
        if self.get_object().audio:
            self.get_object().audio.delete()

    def delete(self, request, *args, **kwargs):
        messages.success(request, self.success_message)
        return super(DetailActionDeleteView, self).delete(request, *args, **kwargs)


def detailActionFileUpload(request):
    if request.is_ajax():
        if request.user.is_authenticated:
            form = DetailActionFileForm(request.POST, request.FILES)
            if form.is_valid():
                cp = form.save()
                return JsonResponse({'file_id': cp.pk}, status=200)
            else:
                return JsonResponse({'error': form.errors}, status=500)
        else:
            return JsonResponse({'error': _("Forbidden")}, status=403)


def detailActionAudioFileUpload(request):
    if request.is_ajax():
        if request.user.is_authenticated:
            form = DetailActionAudioFileForm(request.POST, request.FILES)
            if form.is_valid():
                cp = form.save()
                return JsonResponse({'id': cp.pk, 'url': cp.file.url}, status=200)
            else:
                return JsonResponse({'error': form.errors}, status=500)
        else:
            return JsonResponse({'error': _("Forbidden")}, status=403)


class InactivateActionView(SuccessMessageMixin, AjaxUpdateView):
    form_class = InactivateActionForm
    model = Action
    success_message = _("L'action est marquée comme résolue")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        action = form.save(commit=False)
        action.active = False
        action.save()
        return super().form_valid(form)


###########################
#
##########################
@login_required
@is_operator
def createAccount(request, action_id):
    action = get_object_or_404(Action, id=action_id)
    contact = action.contact
    extra_args = ""
    if has_no_role(action.contact):
        if not contact.email:
            messages.warning(request, _("Veuillez ajouter l'adresse e-mail de contact"))
            return redirect(reverse('action-detail', kwargs={"pk": action_id}))
        else:
            if User.objects.filter(email=contact.email).exists() or EmailAddress.objects.filter(
                    email=contact.email).exists():
                messages.warning(request, _("L'e-mail du contact est déjà utilisé."))
                return redirect(reverse('action-detail', kwargs={"pk": action_id}))

        # create user
        with transaction.atomic():
            user = User()

            group = Group.objects.get(name=Role.DOCTOR.value)

            user.first_name = contact.nom
            user.last_name = contact.prenom
            password = User.objects.make_random_password()
            contact.mdp_genere = password
            user.set_password(password)
            user.username = contact.email
            user.email = contact.email
            user.save()
            user.groups.add(group)

            mail = EmailAddress()
            mail.user = user
            mail.primary = True
            mail.verified = True
            mail.email = contact.email
            mail.save()

            contact.save()

            # Create doctor
            medecin = Medecin()
            medecin.user = user
            medecin.contact = contact
            # medecin carte
            cp = CarteProfessionnelle()
            cp.checked = True
            cp.save()

            medecin.carte = cp

            medecin.save()

            detail = DetailAction()
            detail.cree_par = request.user.operateur
            detail.type = "E"  # Phase Essai
            detail.action = action
            description = "Création de compte:\nNom d'utilisateur: %s \nMot de passe: %s "
            detail.description = description % (contact.email, password)
            detail.save()
            extra_args = "?scrl=detail_%s" % detail.id
            messages.success(request, _("Compte créé!."))
    return redirect(reverse('action-detail', kwargs={"pk": action_id}) + extra_args)
