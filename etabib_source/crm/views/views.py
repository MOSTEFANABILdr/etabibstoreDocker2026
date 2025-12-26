from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import ListView
from fm.views import AjaxCreateView, AjaxDeleteView

from core.models import PinBoard, Eula
from crm.forms.operator_forms import PinBoardCreateForm


###################################
# Pin Board
###################################
class PinBoardListView(ListView):
    model = PinBoard
    template_name = "pin_board.html"
    context_object_name = 'notes'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sidebar_pin_board'] = True
        return context

    def get_queryset(self):
        queryset = PinBoard.objects.filter(cree_par=self.user).order_by("-id")
        return queryset


class PinBoardCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = PinBoardCreateForm
    model = PinBoard

    # success_message = _("note créée avec succès")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        pin_board = form.save(commit=False)
        pin_board.cree_par = self.user
        pin_board.save()
        return super().form_valid(form)


class PinBoardDeleteView(AjaxDeleteView):
    form_class = PinBoardCreateForm
    model = PinBoard
    success_message = _("note supprimée avec succès")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        # messages.success(self.request, self.success_message)
        return super(PinBoardDeleteView, self).delete(request, *args, **kwargs)


def eula(request):
    context = {}
    try:
        eula = Eula.objects.get(dernier=True)
        context['eula'] = eula
    except Eula.DoesNotExist:
        pass
    context['title'] = _("Eula")
    return render(request, "common/eula.html", context)



