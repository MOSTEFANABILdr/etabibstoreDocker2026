from datatableview import Datatable, columns
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
from core.decorators import is_partner


class DemandeRendezVousDatatable(Datatable):
    actions = columns.TextColumn(_("Actions"), source=None, processor='get_entry_action')
    status = columns.TextColumn(_("Etat"), source=None, processor='get_entry_status')
    demandeur_nom = columns.TextColumn(source=['demandeur__first_name'])
    demandeur = columns.TextColumn(source=None, processor="get_demandeur")
    demandeur_prenom = columns.TextColumn(source=['demandeur__last_name'])
    description = columns.TextColumn(source=['description'])
    date_demande = columns.TextColumn(_("Date de la demande"), source=None, processor='get_entry_date_demande')
    date_rendez_vous = columns.TextColumn(_("Date de rendez-vous"), source=None, processor='get_entry_date_rendez_vous')

    class Meta:
        columns = ["demandeur", "description", "date_demande", "status", "date_rendez_vous", "actions"]
        hidden_columns = ["demandeur_nom", "demandeur_prenom"]
        search_fields = ['demandeur__first_name', "demandeur__last_name"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 10

    def get_entry_date_demande(self, instance, **kwargs):
        if instance.date_creation:
            return instance.date_creation.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_demandeur(self, instance, **kwargs):
        if instance.demandeur:
            return "%s (%s)" % (
                instance.demandeur.get_full_name(), instance.demandeur.email
            )
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

    def get_entry_status(self, instance, **kwargs):
        return renderStatus(instance)

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-dmnd-rv-actions.html", {'demande': instance,
                                                                           "user": self.view.request.user})


class DemandeRendezVousDatatableView(DatatableView):
    template_name = "doctor/rdv_demands.html"
    model = DemandeRendezVous
    datatable_class = DemandeRendezVousDatatable

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DemandeRendezVousDatatableView, self).get_context_data(**kwargs)
        context['sidebar_rdv'] = True
        return context

    def get_queryset(self):
        if self.user:
            return DemandeRendezVous.objects.filter(destinataire=self.user)
        return DemandeRendezVous.objects.all()


@login_required
@is_partner
def AppointmentEvents(request):
    conext = {
        'sidebar_appoinments': True
    }
    return render(request, "events.html", conext)
