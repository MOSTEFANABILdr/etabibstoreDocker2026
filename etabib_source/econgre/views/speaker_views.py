from datatableview import columns, Datatable
from datatableview.views import DatatableView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _

from core.decorators import is_speaker
from core.forms.forms import AvatarForm
from econgre.forms import SpeakerProfileForm
from econgre.models import Webinar, Speaker
from econgre.templatetags.congre_tags import renderStatus


@login_required
@is_speaker
def dashboard(request):
    context = {
        "title": _("Dashboard"),
        "sidebar_dashboard": True,
    }
    return render(request, "speaker/dashboard.html", context)


@login_required
@is_speaker
def profile(request):
    title = _('My Profile')
    speaker = get_object_or_404(Speaker, user=request.user)
    if request.method == 'POST':
        avatarForm = AvatarForm()  # this form is submitted with ajax request see: views.avatarUpload
        form = SpeakerProfileForm(instance=speaker, data=request.POST)
        if form.is_valid():
            form.save(commit=True)
            messages.success(request, _("Mise à jour du profil réussie"))
    else:
        avatarForm = AvatarForm()
        form = SpeakerProfileForm(
            initial={
                'nom': speaker.user.first_name,
                'prenom': speaker.user.last_name,
            },
            instance=speaker
        )
    sidebar_profile = True

    context = {
        "title": title,
        "sidebar_profile": sidebar_profile,
        "speaker": speaker,
        "form": form,
        "avatarForm": avatarForm,
    }
    return render(request, "speaker/profile.html", context)


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
    template_name = "speaker/webinars.html"
    model = Webinar
    datatable_class = WebinarDatatable

    @method_decorator(login_required)
    @method_decorator(is_speaker)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(WebinarDatatableView, self).get_context_data(**kwargs)
        context['sidebar_webinars'] = True
        return context

    def get_queryset(self):
        return Webinar.objects.filter(speakers__in=[self.user.speaker], archive=False).order_by(
            "date_debut", "heure_debut"
        )
