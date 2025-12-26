from urllib.parse import urlencode

from datatableview import Datatable, columns
from datatableview.views import DatatableView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.http import JsonResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from el_pagination.decorators import page_template
from fm.views import AjaxCreateView, AjaxUpdateView

from core.decorators import is_patient
from core.mixins import TemplateVersionMixin
from core.models import Medecin, EquipeSoins
from core.utils import getListDoctorsUsingeTabibCare
from teleconsultation.forms import ClaimCreateForm, ClaimUpdateForm, SearchDoctorForm, UseCouponForm
from teleconsultation.models import Tdemand, Tfeedback, Treclamation


@login_required
@page_template('partial/teleconsultation_doctor_list_partial.html')
@is_patient
def doctorsList(request, template="patient/doctors_list.html", extra_context=None):
    param_query = None
    param_gender = None
    param_specialty = None
    if request.method == 'POST':
        form = SearchDoctorForm(request.POST)
        if form.is_valid():
            param_query = form.cleaned_data['query']
            param_gender = form.cleaned_data['gender']
            param_specialty = form.cleaned_data['specialty']
            param_care_team = form.cleaned_data['care_team']
    else:
        form = SearchDoctorForm()
        param_query = request.GET.get('query', None)
        param_gender = request.GET.get('gender', None)
        param_specialty = request.GET.get('specialty', None)
        param_care_team = request.GET.get('care_team', None)

    # Get List of doctors subscribed to eTabib Care
    filtred_list = getListDoctorsUsingeTabibCare(sexe=param_gender, q=param_query, specialty=param_specialty)
    if param_care_team:
        filtred_list = filtred_list.filter(
            user__equipesoins__patient=request.user.patient, user__equipesoins__confirme=True
        ).distinct()
    context = {
        'sidebar_consult': True,
        'title': _("Téléconsultation"),
        'medecins': filtred_list,
        'form': form,
        'extra_args': "&" + urlencode({
            "query": param_query if param_query else "",
            "gender": param_gender if param_gender else "",
            "specialty": param_specialty if param_specialty else "",
            "care_team": param_care_team if param_care_team else "",
        })
    }
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context, using=request.template_version)


class TeleconsultationJournalDatatable(Datatable):
    actions = columns.TextColumn(_("Actions"), source=None, processor='get_entry_action')
    medecin_nom = columns.TextColumn(source=['medecin__user__first_name'])
    medecin_prenom = columns.TextColumn(source=['medecin__user__last_name'])
    facturee = columns.TextColumn(_("Facturée"), source=None, processor='get_facturee_entry')
    date_demande = columns.TextColumn(_("Date"), source=None, processor='get_entry_date_demande')

    class Meta:
        columns = ["medecin", "date_demande", "facturee", "actions"]
        hidden_columns = ["medecin_nom", "medecin_prenom"]
        search_fields = ['medecin__user__first_name', "medecin__user__last_name"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 10

    def get_entry_date_demande(self, instance, **kwargs):
        if instance.date_demande:
            return instance.date_demande.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_facturee_entry(self, instance, **kwargs):
        out = "<ul class='list-unstyled'><li></li>{}<li>{}</li></ul>"
        if instance.facturee:
            text = _("OUI")
            tarif = instance.tarif
        else:
            text = _("NON")
            tarif = ""
        return out.format(text, tarif)

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-telec-dmnd-actions.html",
                                {'demand': instance, "user": self.view.request.user})


class TeleconsultationJournalDatatableView(DatatableView, TemplateVersionMixin):
    template_name = "doctor/teleconsultation_journal.html"
    model = Tdemand
    datatable_class = TeleconsultationJournalDatatable

    @method_decorator(login_required)
    @method_decorator(is_patient)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        self.uid = request.GET.get('uid', None)
        if self.uid:
            try:
                demand = Tdemand.objects.get(unique_id=self.uid)
                messages.success(request,
                                 _("%s a accepté votre demande de téléconsultation.") % demand.medecin.full_name)
            except Tdemand.DoesNotExist:
                pass
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(TeleconsultationJournalDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Demandes de téléconsultations")
        context['sidebar_journal'] = True
        return context

    def get_queryset(self):
        if self.user:
            return Tdemand.objects.filter(patient__user=self.user)
        return Tdemand.objects.all()


@login_required
@is_patient
def teleconsultationFeedback(request):
    """
    :param request:
    :return:
    """
    if request.is_ajax():
        room = request.POST.get('room', None)
        feedback = request.POST.get('feedback', None)
        try:
            demand = Tdemand.objects.get(salle_discussion=room)
        except Tdemand.DoesNotExist:
            return JsonResponse({'error': "target data does not exist"}, status=404)
        if request.user.patient == demand.patient:
            try:
                with transaction.atomic():
                    obj = Tfeedback()
                    obj.message = feedback
                    obj.user = request.user
                    obj.save()

                    demand.feedbacks.add(obj)
            except:
                return JsonResponse({'error': "server error"}, status=500)

            context = {}
            return JsonResponse(context, status=200)
        else:
            return JsonResponse({'error': "not authorized"}, status=403)
    else:
        return JsonResponse({'error': "no content"}, status=405)


class ClaimَCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = ClaimCreateForm
    model = Treclamation
    success_message = _("Merci de nous en avoir informé")

    @method_decorator(login_required)
    @method_decorator(is_patient)
    def dispatch(self, request, *args, **kwargs):
        self.tdemand_pk = kwargs['tdemand_pk'] if 'tdemand_pk' in kwargs else None
        if self.tdemand_pk:
            try:
                self.tdemand = Tdemand.objects.get(pk=self.tdemand_pk)
            except Tdemand.DoesNotExist:
                raise Http404
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        claim = form.save(commit=False)
        claim.tdemande = self.tdemand
        claim.save()
        return super(ClaimَCreateView, self).form_valid(form)


class ClaimَCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = ClaimCreateForm
    model = Treclamation
    success_message = _("Merci de nous en avoir informé")

    @method_decorator(login_required)
    @method_decorator(is_patient)
    def dispatch(self, request, *args, **kwargs):
        self.tdemand_pk = kwargs['tdemand_pk'] if 'tdemand_pk' in kwargs else None
        if self.tdemand_pk:
            try:
                self.tdemand = Tdemand.objects.get(pk=self.tdemand_pk)
            except Tdemand.DoesNotExist:
                raise Http404
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        claim = form.save(commit=False)
        claim.tdemande = self.tdemand
        claim.save()
        return super(ClaimَCreateView, self).form_valid(form)


class ClaimَUpdateView(AjaxUpdateView):
    form_class = ClaimUpdateForm
    model = Treclamation

    @method_decorator(login_required)
    @method_decorator(is_patient)
    def dispatch(self, request, *args, **kwargs):
        self.tdemand_pk = kwargs['tdemand_pk'] if 'tdemand_pk' in kwargs else None
        if self.tdemand_pk:
            try:
                self.tdemand = Tdemand.objects.get(pk=self.tdemand_pk)
            except Tdemand.DoesNotExist:
                raise Http404
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        return super(ClaimَUpdateView, self).form_valid(form)


class UseCouponView(SuccessMessageMixin, AjaxCreateView):
    form_class = UseCouponForm
    success_message = ""

    @method_decorator(login_required)
    @method_decorator(is_patient)
    def dispatch(self, request, *args, **kwargs):
        self.patient = request.user.patient
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(UseCouponView, self).get_form_kwargs()
        kwargs['patient'] = self.patient
        return kwargs

    def form_valid(self, form):
        form.save()
        success_message = _("Coupon valide!")
        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(self.get_success_result())


@login_required
@is_patient
def viewDoctorProfile(request, doctor_id):
    # TODO: might be a better idea to use (CreateView) instead
    # See https://github.com/caioariede/django-location-field/blob/master/example
    if request.is_ajax():
        medecin = Medecin.objects.get(pk=doctor_id)
        if medecin:
            return render(request, "doctor_view_profile.html", context={'medecin': medecin})

    raise Http404


@login_required
@is_patient
def addToCareTeam(request):
    if request.is_ajax():
        medecin_id = request.POST.get('medecin_id', None)
        medecin = get_object_or_404(Medecin, id=medecin_id)
        obj, created = EquipeSoins.objects.get_or_create(
            patient=request.user.patient,
            professionnel=medecin.user,
        )
        return JsonResponse({}, status=200)
    return JsonResponse({}, status=400)