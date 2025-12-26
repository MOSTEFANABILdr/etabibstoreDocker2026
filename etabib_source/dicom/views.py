from datatableview import Datatable, columns
from datatableview.views import DatatableView
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from fm.views import AjaxCreateView
from guardian.decorators import permission_required
from guardian.mixins import PermissionRequiredMixin

from core.decorators import is_doctor
from dicom.forms import PatientDicomForm
from dicom.models import Dicom_Patient


class Dicom(Datatable):
    patient = columns.TextColumn(_("Patient"), source=['patient'])
    dicom = columns.TextColumn(_("Dicom"), source=['dicom'])
    patient_nom = columns.TextColumn(source=['patient__user__first_name'])
    patient_prenom = columns.TextColumn(source=['patient__user__last_name'])

    class Meta:
        columns = ["patient", "dicom"]
        hidden_columns = ["patient_nom", "patient_prenom"]
        search_fields = ['patient__user__first_name', "patient__user__last_name"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 10


class DicomDatatableView(DatatableView):
    template_name = "dicom_list_file.html"
    model = Dicom_Patient
    datatable_class = Dicom

    @method_decorator(login_required)
    @method_decorator(is_doctor)
    @permission_required("core.can_view_test_dicom", return_403=True)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DicomDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Journal")
        context['sidebar_journal'] = True
        return context

    def get_queryset(self):
        return Dicom_Patient.objects.all()


class PatientCreatDicomView(SuccessMessageMixin, PermissionRequiredMixin, AjaxCreateView):
    form_class = PatientDicomForm
    permission_required = 'core.can_view_test_dicom'
    model = Dicom_Patient
    success_message = _("Fichier ajouter")
