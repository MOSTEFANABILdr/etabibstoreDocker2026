from datetime import datetime, time, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from core.decorators import is_operator
from core.models import Facture, Action, Contact, Tache, DetailAction
from core.utils import get_first_day, get_last_day, get_last_months, \
    calculateIncreasePercent
from crm.views.agenda_views import ExpiredEventDatatableView
from crm.views.task_views import TaskDatatableView


@login_required
@is_operator
def dashboard(request):
    context = {'operator_sidebar_dashboard': True}
    if request.user.has_perm("core.crm_can_view_comn_dashboard"):
        context["communication_dashboard"] = communication_dashboard(request)
    if request.user.has_perm("core.crm_can_view_comm_dashboard"):
        context["commercial_dashboard"] =  commercial_dashboard(request)
    if request.user.has_perm("core.crm_can_view_tech_dashboard"):
        context["tech_dashboard"] = tech_dashboard(request)
    return render(request, "operator/dashboard.html", context)


@login_required
@is_operator
def communication_dashboard(request):
    """
    communication assistant dashboard
    :param request:
    :return:
    """
    context = {}
    title = _("Dashboard")

    view1 = ExpiredEventDatatableView()
    datatable = view1.get_datatable(url=reverse("communication-expired-events"))
    context['datatable1'] = datatable

    view2 = TaskDatatableView()
    view2.user = request.user
    datatable = view2.get_datatable(url=reverse("task-list"))
    context['datatable2'] = datatable

    context['title'] = title
    context['tasks_count'] = Tache.objects.filter(attribuee_a__user=request.user, termine=False).count()
    context['actions_count'] = Action.objects.filter(
        Q(type__in=["2"]) & Q(active=True) & Q(date_fin__lt=timezone.now().date())
    ).distinct().count()
    return render_to_string("communication/dashboard.html", context, request)


@login_required
@is_operator
def commercial_dashboard(request):
    context = {}
    tasks = Tache.objects.filter(attribuee_a__user=request.user, termine=False)
    # set All user notifications to read when sender = Tache
    qs = request.user.notifications.unread().filter(actor_content_type__model='Tache')
    if qs.exists():
        qs.mark_all_as_read()
    # Mysql issue: date__month not workinng
    fday = get_first_day(timezone.now())
    ldat = get_last_day(timezone.now())
    contacts_created_this_month = Contact.objects.filter(
        cree_par__user=request.user,
        date_creation__gte=fday,
        date_creation__lte=ldat).count()

    events_created_this_month = Action.objects.filter(
        cree_par__user=request.user,
        date_creation__gte=fday,
        date_creation__lte=ldat).count() + \
                                DetailAction.objects.filter(
                                    cree_par__user=request.user,
                                    date_creation__gte=fday,
                                    date_creation__lte=ldat).count()

    total_income_this_month = Facture.objects.filter(
        commercial=request.user,
        date_creation__gte=fday,
        date_creation__lte=ldat
    ).aggregate(Sum('total')).get('total__sum', 0.00)

    last5months = get_last_months(timezone.now(), 5)  # include this month
    contacts_created_last_5_months = []
    events_created_last_5_months = []
    total_income_last_5_months = []
    for d in last5months:
        fday = get_first_day(d)
        ldat = get_last_day(d)
        c = Contact.objects.filter(cree_par__user=request.user,
                                   date_creation__gte=fday,
                                   date_creation__lte=ldat).count()
        contacts_created_last_5_months.append(int(c))

        c = Action.objects.filter(cree_par__user=request.user,
                                  date_creation__gte=fday,
                                  date_creation__lte=ldat).count() + \
            DetailAction.objects.filter(cree_par__user=request.user,
                                        date_creation__gte=fday,
                                        date_creation__lte=ldat).count()
        events_created_last_5_months.append(int(c))

        c = Facture.objects.filter(
            commercial=request.user,
            date_creation__gte=fday,
            date_creation__lte=ldat
        ).aggregate(Sum('total')).get('total__sum', 0.00)
        total_income_last_5_months.append(int(c) if c else 0)

    last2months = get_last_months(timezone.now(), 2)  # include this month

    increase_percent_contact = []
    increase_percent_event = []
    increase_percent_income = []
    for i, month in enumerate(last2months):
        fday = get_first_day(month)
        ldat = get_last_day(month)
        c = Contact.objects.filter(cree_par__user=request.user,
                                   date_creation__gte=fday,
                                   date_creation__lte=ldat).count()
        increase_percent_income.append(c)

        c = Action.objects.filter(cree_par__user=request.user,
                                  date_creation__gte=fday,
                                  date_creation__lte=ldat).count() + \
            DetailAction.objects.filter(cree_par__user=request.user,
                                        date_creation__gte=fday,
                                        date_creation__lte=ldat).count()
        increase_percent_event.append(c)

        c = Facture.objects.filter(
            commercial=request.user,
            date_creation__gte=fday,
            date_creation__lte=ldat
        ).aggregate(Sum('total')).get('total__sum', 0.00)
        increase_percent_income.append(int(c) if c else 0)

    # goals
    personal_goal = 0
    ihsm_goal = 4
    today = timezone.now()
    min_today_time = datetime.combine(today, time.min)
    max_today_time = datetime.combine(today, time.max)
    c = Action.objects.filter(cree_par__user=request.user,
                              date_creation__lte=max_today_time,
                              date_creation__gte=min_today_time).count() + \
        DetailAction.objects.filter(cree_par__user=request.user,
                                    date_creation__lte=max_today_time,
                                    date_creation__gte=min_today_time).count()

    # list of piste à clôturer
    pistes = Action.objects.filter(type="1",
                                   date_fin__lte=timezone.now().date() + timedelta(days=2),
                                   active=True,
                                   cree_par__user=request.user).distinct()

    context['tasks'] = tasks
    context['cctm'] = contacts_created_this_month
    context['ectm'] = events_created_this_month
    context['titm'] = total_income_this_month
    context['cc5lm'] = contacts_created_last_5_months
    context['ec5lm'] = events_created_last_5_months
    context['ti5lm'] = total_income_last_5_months
    context['ipc'] = calculateIncreasePercent(increase_percent_contact)
    context['ipe'] = calculateIncreasePercent(increase_percent_event)
    context['ipi'] = calculateIncreasePercent(increase_percent_income)
    context['sg'] = [c * 100 / ihsm_goal, 100 - (c * 100 / 4)]
    context['pg'] = [0, 0]
    context['pistes'] = pistes
    return render_to_string("commercial/dashboard.html", context, request)


@login_required
@is_operator
def tech_dashboard(request):
    title = _("Dashboard")
    context = {}

    view = TaskDatatableView()
    view.user = request.user
    datatable = view.get_datatable(url=reverse("task-list"))
    context['datatable'] = datatable

    context['title'] = title
    context['tasks_count'] = Tache.objects.filter(attribuee_a__user=request.user, termine=False).count()

    return render_to_string("technician/dashboard.html", context, request)
