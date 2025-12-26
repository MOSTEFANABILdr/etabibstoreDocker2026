from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from el_pagination.decorators import page_template
from guardian.decorators import permission_required

from econgre.models import Congre, Webinar, UserParticipationWebinar


@login_required
@permission_required("core.can_view_etabib_econgre", return_403=True)
@page_template('partial/congre-partial.html')
def congressList(request, template="doctor/congress-list.html", extra_context=None):
    title = _("List des Congrès")
    initial = {}
    q = request.GET.get('q')
    congres = Congre.objects.filter(publie=True, archive=False).order_by("-id")

    if q:
        congres = congres.filter(
            Q(nom__icontains=q) | Q(description__icontains=q)
        )
        initial["q"] = q
    context = {
        "title": title,
        'congres': congres,
        "todo": True,
        "sidebar_congress": True
    }
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context, using=request.template_version)


@login_required
def participateWebinar(request):
    if request.is_ajax():
        pk = request.POST.get('id', None)
        try:
            webinar = Webinar.objects.get(pk=pk)
            obj = UserParticipationWebinar()
            obj.user = request.user
            obj.webinar = webinar
            obj.save()

            return JsonResponse({}, status=200)
        except Webinar.DoesNotExist:
            return JsonResponse({'error': "target data does not exist"}, status=404)
    else:
        return JsonResponse({'error': "no content"}, status=405)
