from datatableview import columns, Datatable
from datatableview.views import DatatableView
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.timesince import timeuntil
from django.utils.translation import ugettext_lazy as _

from appointements.enums import RdvStatus
from appointements.models import DemandeRendezVous
from appointements.templatetags.rdv_tags import renderStatus
from core.decorators import is_patient
from core.mixins import TemplateVersionMixin


class DemandeRendezVousDatatable(Datatable):
    destinataire = columns.TextColumn(_("Médecin"), source=['destinataire__get_full_name'])
    destinataire_nom = columns.TextColumn(source=['destinataire__first_name'])
    destinataire_prenom = columns.TextColumn(source=['destinataire__last_name'])
    status = columns.TextColumn(_("État"), source=None, processor='get_entry_status')
    type = columns.TextColumn(_("Lieu"), source=None, processor='get_entry_type')
    date_rendez_vous = columns.TextColumn(_("Date de rendez vous"), source=None, processor='get_entry_date_rendez_vous')
    action = columns.TextColumn(_("Actions"), source=None, processor='get_entry_action')

    class Meta:
        columns = ["destinataire", "type", "status", "date_rendez_vous", "action"]
        hidden_columns = ["destinataire_nom", "destinataire_prenom"]
        search_fields = ['destinataire__first_name', "destinataire__last_name"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 10

    def get_entry_date_rendez_vous(self, instance, **kwargs):
        str = "<p>{}</p><p><strong>Restant:</strong> {}</p>"
        if instance.date_rendez_vous:
            return str.format(
                instance.date_rendez_vous.strftime("%Y-%m-%d %H:%M:%S"),
                timeuntil(instance.date_rendez_vous, timezone.now()) if instance.status == RdvStatus.ACCEPTED else ""
            )
        return ""

    def get_entry_type(self, instance, **kwargs):
        if instance.type:
            return instance.get_type_display()
        return ""

    def get_entry_status(self, instance, **kwargs):
        return renderStatus(instance)

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-dmnd-rv-actions.html",
                                {
                                    'demande': instance,
                                    "user": self.view.request.user
                                })


class DemandeRendezVousDatatableView(TemplateVersionMixin, DatatableView):
    template_name = "patient/rdv_demands.html"
    model = DemandeRendezVous
    datatable_class = DemandeRendezVousDatatable

    @method_decorator(login_required)
    @method_decorator(is_patient)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DemandeRendezVousDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Demandes de rendez vous")
        context['sidebar_rdv'] = True
        return context

    def get_queryset(self):
        if self.user:
            return DemandeRendezVous.objects.filter(demandeur=self.user)
        return DemandeRendezVous.objects.all()


@login_required
@is_patient
def agenda(request):
    context = {

    }
    return render(request, "patient/agenda.html", context, using=request.template_version)
