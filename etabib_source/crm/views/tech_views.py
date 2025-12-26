'''
Created on 9 janv. 2019

@author: ZAHI
'''
from datetime import datetime

from datatableview import Datatable, columns
from datatableview.views import DatatableView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from fm.views import AjaxCreateView, AjaxUpdateView, AjaxDeleteView

from core.decorators import is_operator
from core.enums import Role
from core.models import Action, Intervention, DetailAction, Screenshot, Probleme, Tache, DemandeIntervention
from core.utils import getEventColor, getEventIcon, getEventTitle
from crm.forms.operator_forms import InterventionForm, ScreenShotUploadForm, ProblemForm
from crm.views.task_views import TaskDatatableView


def index(request):
    return render(request, "administrator/demand-detail.html")


def screenShotUpload(request):
    if request.is_ajax():
        if request.user.is_authenticated:
            form = ScreenShotUploadForm(request.POST, request.FILES)
            if form.is_valid():
                cp = form.save()
                return JsonResponse({'file_id': cp.pk, "file_url": cp.image.url}, status=200)
            else:
                return JsonResponse({'error': form.errors}, status=500)
        else:
            return JsonResponse({'error': _("Forbidden")}, status=403)



def fetchEvents(request):
    if request.is_ajax():
        start = request.GET.get('start', False)
        end = request.GET.get('end', False)
        startDate = datetime.fromtimestamp(int(start))
        endDate = datetime.fromtimestamp(int(end))

        ct_user = ContentType.objects.get_for_model(request.user)
        groupe = Group.objects.get(name=Role.TECHNICIAN.value)
        ct_group = ContentType.objects.get_for_model(groupe)

        actions = Action.objects.filter((
                                                Q(date_debut__lte=endDate, date_debut__gte=startDate) |
                                                Q(date_fin__lte=endDate, date_fin__gte=startDate)
                                        ) &
                                        (
                                                Q(attribuee_a_type=ct_user, attribuee_a_id=request.user.id) |
                                                Q(attribuee_a_type=ct_group, attribuee_a_id=groupe.id)
                                        )
                                        ).distinct()
        datas = []
        if request.user.is_authenticated:
            for action in actions:
                data = {}
                data['title'] = getEventTitle(action)
                data['description'] = data['title']
                data['start'] = datetime.combine(action.date_debut, action.date_debut_time).isoformat()
                data['end'] = datetime.combine(action.date_fin, action.date_fin_time).isoformat()
                data['color'] = getEventColor(action)
                data['icon'] = getEventIcon(action)
                data['url'] = reverse('action-detail', kwargs={'pk': action.pk})
                datas.append(data)
            return JsonResponse(datas, safe=False)
        else:
            return JsonResponse({'error': _("Forbidden")}, status=403)


class InterventionCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = InterventionForm
    model = Intervention
    success_message = _("Intervention créée avec succès")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.action_pk = kwargs['action_pk'] if 'action_pk' in kwargs else None
        if self.action_pk:
            try:
                self.action = Action.objects.get(pk=self.action_pk)
            except Action.DoesNotExist:
                pass
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        context = {}
        return context

    def form_valid(self, form):
        intervention = form.save(commit=False)

        detail = DetailAction()
        detail.action = self.action
        detail.description = _("Intervention technique")
        detail.cree_par = self.operateur
        detail.save()

        intervention.detail_action = detail
        intervention.save()

        img = form.getScreen()
        if img:
            try:
                intervention.screenshots.clear()
                sc = Screenshot.objects.get(pk=img)
                intervention.screenshots.add(sc)
            except Screenshot.DoesNotExist as e:
                pass
        return super().form_valid(form)


class InterventionUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = InterventionForm
    model = Intervention
    success_message = _("Intervention mise à jour avec succès")
    unauthorized_message = _("Vous ne pouvez pas mettre à jour cette intervention")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.intevention = get_object_or_404(Intervention, pk=kwargs['pk'])
        if self.intevention.detail_action.cree_par.user != self.request.user:
            return self.render_json_response({'status': 'error', 'message': self.unauthorized_message})
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        intervention = form.save(commit=False)
        img = form.getScreen()
        if img:
            try:
                sc = Screenshot.objects.get(pk=img)
                intervention.screenshots.add(sc)
            except Screenshot.DoesNotExist as e:
                print("exception")
                print(e)
        return super().form_valid(form)


"""
    Problem datatable
"""


class ProblemDatatable(Datatable):
    actions = columns.TextColumn(_("Actions"), sources=None, processor='get_entry_action')
    resolu = columns.TextColumn(_("A une solution"), source=None, processor='get_entry_resolu')
    date_creation = columns.TextColumn(_("Date de création"), source=None, processor='get_entry_date_creation')

    class Meta:
        columns = ["libelle", "date_creation", "resolu", "actions"]
        search_fields = ["id", "libelle"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-date_creation']
        page_length = 20

    def get_entry_resolu(self, instance, **kwargs):
        if instance.solution:
            return "<i class='fa fa-check'></i>"
        else:
            return "<i class='fa fa-close'></i>"

    def get_entry_date_creation(self, instance, **kwargs):
        if instance.date_creation:
            return instance.date_creation.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-problems-actions.html", {'problem': instance})


"""
    Problems datatable View
"""


class ProblemDatatableView(DatatableView):
    template_name = "technician/problem-list.html"
    model = Probleme
    datatable_class = ProblemDatatable

    def get_context_data(self, **kwargs):
        context = super(ProblemDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Liste des problèmes & solutions")
        context["tech_sidebar_list_problem"] = True
        return context

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super(ProblemDatatableView, self).dispatch(request, *args, **kwargs)


class ProblemَCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = ProblemForm
    model = Probleme
    success_message = _("Problème/Solution créé avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        prblm = form.save(commit=False)
        prblm.cree_par = self.operateur
        prblm.save()
        img = form.getScreen()
        if img:
            try:
                sc = Screenshot.objects.get(pk=img)
                prblm.screenshot.add(sc)
            except Screenshot.DoesNotExist as e:
                pass
        return super(ProblemَCreateView, self).form_valid(form)


class ProblemUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = ProblemForm
    model = Probleme
    success_message = _("Problème/Solution mise à jour avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        prblm = form.save(commit=False)
        img = form.getScreen()
        if img:
            try:
                prblm.screenshot.clear()
                sc = Screenshot.objects.get(pk=img)
                prblm.screenshot.add(sc)
            except Screenshot.DoesNotExist as e:
                pass
        return super().form_valid(form)


class ProblemDeleteView(AjaxDeleteView):
    model = Probleme
    success_message = _("Problème/Solution supprimée avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(ProblemDeleteView, self).delete(request, *args, **kwargs)


@login_required
def demandeInterventionDetail(request, pk):
    context = {}
    try:
        di = DemandeIntervention.objects.get(pk=pk)
        context['item'] = di
    except DemandeIntervention.DoesNotExist:
        pass
    context['title'] = _("Détail de la demande d'assistance")
    return render(request, "common/intervention_detail.html", context)
