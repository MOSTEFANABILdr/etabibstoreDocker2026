# -*- coding: utf-8 -*-

from datatableview import columns
from datatableview.datatables import Datatable
from datatableview.views import DatatableView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from fm.views import AjaxCreateView, AjaxUpdateView, AjaxDeleteView
from guardian.decorators import permission_required

from core.models import Tache
from crm.forms.operator_forms import TaskForm


#############################################
# Task datatable
#############################################
class TaskDatatable(Datatable):
    nom = columns.TextColumn(sources=['contact__nom'])
    prenom = columns.TextColumn(sources=['contact__prenom'])
    contact = columns.TextColumn(_("Contact"), source=None, processor='get_entry_contact')
    date_creation = columns.TextColumn(_("Date de création"), source=None, processor='get_entry_date_creation')
    actions = columns.TextColumn(_("Terminée"), sources=None, processor='get_entry_action')

    class Meta:
        columns = ["message", "contact", "date_creation", "actions"]
        search_fields = ["message", "contact__nom", "contact__prenom"]
        hidden_columns = ["nom", "prenom"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['date_creation']
        page_length = 5

    def get_entry_date_creation(self, instance, **kwargs):
        if instance.date_creation:
            return instance.date_creation.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_entry_action(self, instance, **kwargs):
        return '<input class="checkbox task-list" type="checkbox" value="%s"></td>' % instance.id

    def get_entry_contact(self, instance, **kwargs):
        return "<a href='{}'>{}</a>".format(
            reverse('operator-detail-contact', args=(instance.contact.id,)), instance.contact.full_name
        ) if instance.contact else ""


class TaskDatatableView(DatatableView):
    model = Tache
    datatable_class = TaskDatatable

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super(TaskDatatableView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Tache.objects.filter(attribuee_a__user=self.user, termine=False)


@login_required
def markTaskAsDone(request):
    if request.is_ajax():
        task_id = request.POST.get('task_id', None)
        try:
            tache = Tache.objects.get(id=task_id)
            tache.termine = True
            tache.save()
            return JsonResponse({}, status=200)
        except Tache.DoesNotExist:
            return JsonResponse({}, status=404)
    else:
        return JsonResponse({'status': "Not an ajax request"}, status=500)


class TaskAdmDatatable(Datatable):
    actions = columns.TextColumn(_("Actions"), sources=None, processor='get_entry_action')
    termine = columns.TextColumn(_("Terminée"), sources=None, processor='get_entry_termine')
    date_creation = columns.TextColumn(_("Date de création"), source=None, processor='get_entry_date_creation')

    class Meta:
        columns = ["id", "attribuee_a", "message", "date_creation", "contact", "termine", "actions"]
        search_fields = ["id"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 20

    def get_entry_termine(self, instance, **kwargs):
        if instance.termine:
            return "<i class='fa fa-check'></i>"
        else:
            return "<i class='fa fa-close'></i>"

    def get_entry_date_creation(self, instance, **kwargs):
        if instance.date_creation:
            return instance.date_creation.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-tasks-actions.html", {'task': instance})


class TaskDatatableAdmView(DatatableView):
    template_name = "administrator/task-list.html"
    model = Tache
    datatable_class = TaskAdmDatatable

    def get_context_data(self, **kwargs):
        context = super(TaskDatatableAdmView, self).get_context_data(**kwargs)
        context['title'] = _("Liste des tâches")
        context["sidebar_list_task"] = True
        return context

    @method_decorator(login_required)
    @method_decorator(permission_required("core.manage_tasks", raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super(TaskDatatableAdmView, self).dispatch(request, *args, **kwargs)


class TaskَCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = TaskForm
    model = Tache
    success_message = _("Tache est créée avec succès")

    @method_decorator(login_required)
    @method_decorator(permission_required("core.manage_tasks", raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        tsk = form.save(commit=False)
        tsk.cree_par = self.operateur
        tsk.save()
        return super(TaskَCreateView, self).form_valid(form)


class TaskUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = TaskForm
    model = Tache
    success_message = _("Tache mise à jour avec succès")

    @method_decorator(login_required)
    @method_decorator(permission_required("core.manage_tasks", raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        tsk = form.save(commit=False)
        tsk.save
        return super().form_valid(form)


class TaskDeleteView(AjaxDeleteView):
    model = Tache
    success_message = _("Tache est supprimée avec succès")

    @method_decorator(login_required)
    @method_decorator(permission_required("core.manage_tasks", raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(TaskDeleteView, self).delete(request, *args, **kwargs)
