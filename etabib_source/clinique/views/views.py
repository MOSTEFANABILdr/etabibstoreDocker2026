from django.http import HttpResponseRedirect
from fm.views import AjaxCreateView, AjaxUpdateView
from guardian.mixins import LoginRequiredMixin

from clinique.forms import ConsultationForm
from clinique.models import Consultation
from core.models import Patient


class ConsultationCreateView(LoginRequiredMixin, AjaxCreateView):
    form_class = ConsultationForm
    model = Consultation

    def get_form_kwargs(self):
        kwargs = super(ConsultationCreateView, self).get_form_kwargs()
        kwargs['hide_date_ajout'] = False
        return kwargs

    def form_valid(self, form):
        patient_pk = self.kwargs.get('patient_pk')
        consultation = form.save(commit=False)
        date_ajout = form.cleaned_data.get('date_ajout')

        consultation.operateur = self.request.user
        patient = Patient.objects.get(pk=patient_pk)
        consultation.patient = patient
        consultation.save()

        if date_ajout:
            consultation.date_creation = date_ajout
            consultation.save(update_fields=['date_creation'])

        form.save_m2m()
        if self.request.is_ajax():
            return self.render_json_response(self.get_success_result())
        return HttpResponseRedirect(self.get_success_url())


class ConsultationUpdateView(LoginRequiredMixin, AjaxUpdateView):
    form_class = ConsultationForm
    model = Consultation

    def get_initial(self):
        initial = super(ConsultationUpdateView, self).get_initial()
        self.patient = self.get_object().patient
        initial['date_ajout'] = self.get_object().date_creation
        return initial

    def form_valid(self, form):
        consultation = form.save(commit=False)
        date_ajout = form.cleaned_data.get('date_ajout')
        consultation.patient = self.patient
        if date_ajout:
            consultation.date_creation = date_ajout
            consultation.save(update_fields=['date_creation'])
        consultation.save()
        form.save_m2m()
        if self.request.is_ajax():
            return self.render_json_response(self.get_success_result())
        return HttpResponseRedirect(self.get_success_url())
