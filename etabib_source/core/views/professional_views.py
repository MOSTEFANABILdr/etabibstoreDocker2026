# -*- coding: utf-8 -*-
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.template.defaultfilters import date
from django.utils import timezone
from django.utils.translation import gettext as _
from el_pagination.decorators import page_template
from guardian.decorators import permission_required

from core.decorators import is_professionnal
from core.forms.forms import AvatarForm
from core.forms.professionnal_forms import DciAtcForm, ProfileForm
from core.models import ProfessionnelSante
from drugs.models import DciAtc, Medicament, Stock, MapCnas, MedicamentCnasForme, CodeAtc, NomCommercial


@login_required
@is_professionnal
def dashboard(request):
    sidebar_dashboard = True
    title = _("Dashboard")

    context = {
        "title": title,
        "sidebar_dashboard": sidebar_dashboard,
    }
    return render(request, "professionnal/dashboard.html", context)


@login_required
@is_professionnal
def profile(request):
    title = _('My Profile')
    professionnelsante = get_object_or_404(ProfessionnelSante, user=request.user)
    if request.method == 'POST':
        avatarForm = AvatarForm()  # this form is submitted with ajax request see: views.avatarUpload
        form = ProfileForm(request.POST, professionnelsante=professionnelsante)
        if form.is_valid():
            form.save()
            messages.success(request, _("Mise à jour du profil réussie"))
    else:
        avatarForm = AvatarForm()
        form = ProfileForm(initial={
        })
    sidebar_profile = True

    context = {
        "title": title,
        "sidebar_profile": sidebar_profile,
        "form": form,
        "avatarForm": avatarForm,
    }
    return render(request, "professionnal/profile.html", context)


##########################
# Medicament
##########################
@login_required
@page_template('partial/drugs-partial.html')
@permission_required("core.can_view_drugs_list", return_403=True)
def drugsList(request, template="professionnal/drugs.html", extra_context=None):
    context = {}
    dci = None
    dci_id = None
    if request.is_ajax():
        if request.method == 'POST':
            #First call
            dci_id = request.POST.get('dci_id', None)
        if request.method == 'GET':
            # pagination call
            dci_id = request.GET.get('dci_id', None)
    if dci_id:
        dci = DciAtc.objects.get(id=dci_id)
        ncs = NomCommercial.objects.filter(medicament__dci_atc=dci).distinct()
        if ncs.exists():
            context['nom_commerciaux'] = ncs
            context['nc_count'] = ncs.count()
        else:
            context['nom_commerciaux'] = NomCommercial.objects.none()
            context['nc_count'] = 0
            #TODO: search by CodeAtc
            cdatc = CodeAtc.objects.filter(dciAtc=dci).distinct()
        #passing dci_id to pagination url
        context['extra_args'] = "&dci_id=%s" % dci_id
    context['form'] = DciAtcForm(initial={'dci': dci})
    context['sidebar_drugs'] = True
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context)


@login_required
@is_professionnal
@permission_required("core.can_view_drugs_list", return_403=True)
def drugs_detail(request):
    if request.is_ajax():
        context = {}
        medicament_id = request.POST.get('medicament_id', None)
        if medicament_id:
            medicament = Medicament.objects.get(id=medicament_id)
            stk = Stock.objects.filter(professionnel_sante=request.user.professionnelsante).filter(
                medicament=medicament).first()
            cns = MapCnas.objects.filter(medicament=medicament)
            if cns.exists():
                context['cnas'] = cns.first().medicamentcnas
                form = MedicamentCnasForme.objects.filter(code=int(cns.first().medicamentcnas.forme))
                if form.exists():
                    context['form_medic'] = form.first().libelle
            context['medicament'] = medicament
            context['stk'] = stk
    return render(request, "partial/drugs-detail.html", context)


@login_required
@is_professionnal
@permission_required("core.can_view_drugs_list", return_403=True)
def have_in_stock(request):
    if request.is_ajax():
        medicament_id = request.POST.get('medicament_id', None)
        if medicament_id:
            medicament = get_object_or_404(Medicament, id=medicament_id)
            stk = Stock.objects.filter(
                professionnel_sante=request.user.professionnelsante, medicament=medicament
            ).first()
            if stk:
                if stk.valide:
                    stk.valide = False
                    stk.date_update = timezone.now()
                    stk.save()
                else:
                    stk.valide = True
                    stk.date_update = timezone.now()
                    stk.save()
            else:
                stk = Stock()
                stk.professionnel_sante = request.user.professionnelsante
                stk.medicament = medicament
                stk.save()
            return JsonResponse({"date_update": date(stk.date_update, "Y-m-d H:i")}, status=200)
        else:
            return JsonResponse({}, status=404)
    return JsonResponse({}, status=400)