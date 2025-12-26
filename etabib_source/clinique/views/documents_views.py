from django.http import HttpResponseRedirect
from fm.views import AjaxCreateView, AjaxUpdateView, AjaxDeleteView
from guardian.mixins import LoginRequiredMixin

from clinique.forms import DocumentForm
from clinique.models import Document
from core.models import Patient


class DocumentCreateView(LoginRequiredMixin, AjaxCreateView):
    form_class = DocumentForm
    model = Document

    def form_valid(self, form):
        patient_pk = self.kwargs.get('patient_pk')
        document = form.save(commit=False)
        document.operateur = self.request.user
        patient = Patient.objects.get(pk=patient_pk)
        document.patient = patient
        document.save()
        date_ajout = form.cleaned_data.get('date_ajout')
        if date_ajout:
            document.date_creation = date_ajout
            document.save(update_fields=['date_creation'])
        form.save_m2m()
        if self.request.is_ajax():
            return self.render_json_response(self.get_success_result())
        return HttpResponseRedirect(self.get_success_url())


class DocumentUpdateView(LoginRequiredMixin, AjaxUpdateView):
    form_class = DocumentForm
    model = Document

    def get_initial(self):
        initial = super(DocumentUpdateView, self).get_initial()
        initial['date_ajout'] = self.get_object().date_creation
        return initial

    def form_valid(self, form):
        document = form.save(commit=False)
        date_ajout = form.cleaned_data.get('date_ajout')
        if date_ajout:
            document.date_creation = date_ajout
            document.save(update_fields=['date_creation'])
        document.save()
        form.save_m2m()
        if self.request.is_ajax():
            return self.render_json_response(self.get_success_result())
        return HttpResponseRedirect(self.get_success_url())


class DocumentDeleteView(LoginRequiredMixin, AjaxDeleteView):
    model = Document
