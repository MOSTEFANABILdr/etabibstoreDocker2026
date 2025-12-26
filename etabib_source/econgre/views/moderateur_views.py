from datatableview import columns, Datatable
from datatableview.views import DatatableView
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _

from core.decorators import is_moderator
from econgre.models import Webinar
from econgre.templatetags.congre_tags import renderStatus


@login_required
@is_moderator
def dashboard(request):
    context = {
        "title": _("Dashboard"),
        "sidebar_dashboard": True,
    }
    return render(request, "moderator/dashboard.html", context)

################################
# Webinar views
################################
class WebinarDatatable(Datatable):
    date = columns.TextColumn(_("Date"), source=None, processor='get_entry_date')
    status = columns.TextColumn(_("Etat"), source=None, processor='get_entry_status')
    actions = columns.TextColumn("", source=None, processor='get_entry_action')

    class Meta:
        columns = ["nom", "date", "status", "actions"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 10

    def get_entry_date(self, instance, **kwargs):
        if instance.date_debut:
            return "%s de %s à %s" % (
                instance.date_debut.strftime("%Y-%m-%d"),
                instance.heure_debut.strftime("%H:%M"),
                instance.heure_fin.strftime("%H:%M"),
            )
        return ""

    def get_entry_status(self, instance, **kwargs):
        return renderStatus(instance)

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-webinar-actions.html",
                                {'webinar': instance, "user": self.view.request.user})


class WebinarDatatableView(DatatableView):
    template_name = "moderator/webinars.html"
    model = Webinar
    datatable_class = WebinarDatatable

    @method_decorator(login_required)
    @method_decorator(is_moderator)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(WebinarDatatableView, self).get_context_data(**kwargs)
        context['sidebar_webinars'] = True
        return context

    def get_queryset(self):
        return Webinar.objects.filter(moderateurs__in=[self.user.moderateur])
