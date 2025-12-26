# -*- coding: utf-8 -*-
import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http.response import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _
from el_pagination import utils
from el_pagination.decorators import page_template
from guardian.decorators import permission_required
from taggit.models import Tag

from api.views.ads_views import getAd
from core.decorators import has_access, is_doctor_or_professionnal
from core.enums import AdsDestination, AdTypeHelper, EtabibService
from core.forms.doctor_forms import AppCommentForm, AppRatingForm, AppInstallationForm, SearchForm
from core.models import Module, Commentaire, Poste
from core.templatetags.app_store_tags import getInstallationAction, \
    getInstallationText, getInstallationSuccessMessage
from etabibWebsite import settings
from store.forms import SearchV2Form


def eTabibStore(request):
    if request.template_version == "v1":
        return redirect("etabib-store-v1")
    else:
        return redirect("etabib-store-v2")


@login_required
@permission_required("core.can_view_etabib_store", return_403=True)
@page_template('partial/app-store-list.html')
def eTabibV1Store(request, template="doctor/app_store.html", extra_context=None):
    """
    :param request:
    :param template:
    :param extra_context:
    :return: list of 4 random apps from all categories and all tags
    """
    title = _("eTabib Store")
    sidebar_store = True
    lis = []

    # TODO: add recommended Applications
    # lis.append(("Recommanded", [], "#", False))

    page = utils.get_page_number_from_request(request)

    tags = Tag.objects.all()
    try:
        # Note: the below code works just in MySql Database
        # randomize the the order of tags
        if not request.session.get('random_seed', False) or page == 1:
            request.session['random_seed'] = random.randint(1, 10000)
        seed = request.session['random_seed']
        tags = tags.extra(select={'id': 'RAND(%s)' % seed}).order_by('id')
    except Exception:
        pass

    for tag in tags:
        apps = Module.objects.filter(tags__name__in=[tag]).order_by('?')[:4]
        if apps:
            lis.append((tag, apps, reverse('etabib-store-tag-apps', args=[tag.slug]), False))

    ##call API to get an ad
    annonce = getAd(request, AdsDestination.WEB, AdTypeHelper.DISPLAY, settings.ADS_IMAGE_SIZE_CHOICES[0][0])
    if annonce:
        lis.insert(1 if len(lis) > 0 else 0, ("Ads إعلانـات", [annonce], "#", True))

    context = {
        "title": title,
        'list': lis,
        "sidebar_store": sidebar_store,
        "form": SearchForm(),
    }
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context, using=request.template_version)


@login_required
@permission_required("core.can_view_etabib_store", return_403=True)
@page_template('partial/app-store-list.html')
def eTabibV2Store(request, template="doctor/app_store.html", extra_context=None):
    """
    :param request:
    :param template:
    :param extra_context:
    :return:
    """
    title = _("eTabib Store")

    # annonce = getAd(request, AdsDestination.WEB, AdTypeHelper.DISPLAY, settings.ADS_IMAGE_SIZE_CHOICES[0][0])
    # if annonce:
    #     lis.insert(1 if len(lis) > 0 else 0, ("Ads إعلانـات", [annonce], "#", True))

    if request.method == "POST":
        sq = request.POST.get("sq", "")
        category = request.POST.get("category", "")
        poste_id = request.POST.get("poste", "")
        sub_category = request.POST.getlist("sub_category", [])
    elif request.method == "GET":
        sq = request.GET.get("sq", "")
        category = request.GET.get("category", "")
        poste_id = request.POST.get("poste", "")
        sub_category = request.GET.get("sub_category", "")
        if sub_category:
            sub_category = sub_category.split(",")

    modules = Module.objects.all()

    if category:
        if category == "1":
            # My apps
            if poste_id:
                modules = Module.objects.filter(version__poste__id=poste_id)
            else:
                modules = Module.objects.filter(version__poste__medecin__user=request.user).distinct()

    if sq:
        modules = modules.filter(libelle__icontains=sq)
    if sub_category:
        modules = modules.filter(tags__id__in=sub_category)

    context = {
        "title": title,
        'products': modules,
        "products_count": modules.count(),
        "poste_id": poste_id,
        "searchform": SearchV2Form(
            initial={
                "sub_category": Tag.objects.filter(id__in=sub_category),
                "sq": sq,
                "category": category
            },
            user=request.user
        ),
        'extra_args': f"&sq={sq}&sub_category={','.join(sub_category)}&category={category}&poste={poste_id}",
    }
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context, using=request.template_version)


@login_required
@permission_required("core.can_view_etabib_store", return_403=True)
@is_doctor_or_professionnal
@has_access(EtabibService.ETABIB_STORE)
@page_template('partial/app-store-my-partial.html')
def eTabibStoreMyApps(request, poste_id=None, template="doctor/app-store-my.html", extra_context=None):
    if request.template_version == "v2":
        return HttpResponseRedirect(reverse('etabib-store-v2') + "?category=1")

    title = _("My applications")
    poste = None
    if poste_id:
        poste = get_object_or_404(Poste, id=poste_id, medecin__user=request.user)
    else:
        postes = request.user.medecin.postes
        if postes.count() > 0:
            poste = postes.first()

    apps = []
    if poste:
        versions = poste.modules.all()
        for version in versions:
            apps.append(version.module)

    sidebar_store = True
    context = {
        "title": title,
        'apps': apps,
        "sidebar_store": sidebar_store
    }
    if poste:
        context.update({"poste": poste})

    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context)


@login_required
@permission_required("core.can_view_etabib_store", return_403=True)
@page_template('partial/app-store-my-partial.html')
def eTabibStoreTagApps(request, tag, template="doctor/app-store-category.html", extra_context=None):
    if request.template_version == "v2":
        t = get_object_or_404(Tag, slug=tag)
        return HttpResponseRedirect(reverse('etabib-store-v2') + f"?category=0&sub_category={t.id}")

    title = "{} {}".format(tag, _("Applications"))
    apps = Module.objects.filter(tags__slug__in=[tag])

    sidebar_store = True
    context = {
        "title": title,
        'apps': apps,
        'category': tag,
        "sidebar_store": sidebar_store
    }
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context)


@login_required
@permission_required("core.can_view_etabib_store", return_403=True)
@is_doctor_or_professionnal
@page_template('partial/comment_list.html')
def eTabibStoreItemDetail(request, pk, slug,
                          template="doctor/app_store_item_detail.html",
                          extra_context=None):
    app = get_object_or_404(Module, pk=pk, slug=slug)
    user_rating = app.note_medecin(request.user)
    is_published = app.is_published()

    sidebar_store = True
    context = {
        "title": app.libelle,
        "app": app,
        'comments': app.commentaires,
        'rating': user_rating,
        'is_published': is_published,
        "sidebar_store": sidebar_store,
        "similar_apps": Module.objects.filter(tags__in=app.tags.all()).exclude(id=pk).random(6)
    }
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context, using=request.template_version)


@login_required
@permission_required("core.can_view_etabib_store", return_403=True)
@is_doctor_or_professionnal
@has_access(EtabibService.ETABIB_STORE)
def getAppStatus(request):
    if request.is_ajax():
        poste_id = request.POST.get('poste_id', None)
        app_id = request.POST.get('app_id', None)
        try:
            poste = Poste.objects.get(pk=poste_id)
        except Poste.DoesNotExist:
            return JsonResponse({'error': "target data does not exist"}, status=404)
        try:
            app = Module.objects.get(pk=app_id)
        except Module.DoesNotExist:
            return JsonResponse({'error': "target data does not exist"}, status=404)
        if request.user.medecin == poste.medecin:
            context = {
                "app_status": getInstallationAction(app.etat(poste).value, app, poste, request.session),
                "body": getInstallationText(app.etat(poste).value, app, poste, request.session)
            }
            return JsonResponse(context, status=200)
        else:
            return JsonResponse({'error': "not authorized"}, status=403)
    else:
        return JsonResponse({'error': "no content"}, status=405)


@login_required
@permission_required("core.can_view_etabib_store", return_403=True)
@is_doctor_or_professionnal
@has_access(EtabibService.ETABIB_STORE)
def addComment(request):
    if request.is_ajax():
        form = AppCommentForm(request.POST)
        if form.is_valid():
            c = form.save()
            html = render_to_string('partial/comment_item.html', {'comment': c, 'user': request.user})
            return JsonResponse({'comment_id': c.pk, "html": html}, status=200)
        else:
            return JsonResponse({'error': form.errors}, status=500)


@login_required
@permission_required("core.can_view_etabib_store", return_403=True)
@is_doctor_or_professionnal
@has_access(EtabibService.ETABIB_STORE)
def removeComment(request):
    if request.is_ajax():
        pk = request.POST.get('id', None)
        comment = get_object_or_404(Commentaire, pk=pk)
        comment.delete()
        return JsonResponse({"pk": pk}, status=200)


@login_required
@permission_required("core.can_view_etabib_store", return_403=True)
@is_doctor_or_professionnal
@has_access(EtabibService.ETABIB_STORE)
def addAppRating(request):
    if request.is_ajax():
        form = AppRatingForm(request.POST)
        if form.is_valid():
            c = form.save()
            return JsonResponse({'rating': c.valeur}, status=200)
        else:
            return JsonResponse({'error': form.errors}, status=500)


@login_required
@permission_required("core.can_view_etabib_store", return_403=True)
@has_access(EtabibService.ETABIB_WORKSPACE)
def installApplication(request):
    if request.is_ajax():
        form = AppInstallationForm(request.POST, session=request.session, user=request.user)
        if form.is_valid():
            app = Module.objects.get(id=form.cleaned_data['app_id'])
            poste = get_object_or_404(Poste, id=form.cleaned_data['poste_id'])
            status = form.save()
            action = getInstallationAction(status.value, app, poste, request.session)
            success_message = getInstallationSuccessMessage(status.value, app, poste, request.session)
            text = getInstallationText(status.value, app, poste, request.session)
            return JsonResponse({'action': action, 'success_message': success_message, 'body': text}, status=200)
        else:
            error_string = ' '.join([' '.join(x for x in l) for l in list(form.errors.values())])
            return JsonResponse({'error': error_string}, status=500)


@login_required
@permission_required("core.can_view_etabib_store", return_403=True)
@page_template('partial/app-store-my-partial.html')
def searchApp(request, template="doctor/app_store_search_page.html", extra_context=None):
    q = request.GET.get('q')
    tag = request.GET.get('tag')

    if request.template_version == "v2":
        return HttpResponseRedirect(reverse('etabib-store-v2') + f"?sq={q}&sub_category={tag}")

    context = {}
    initial = {}
    apps = Module.objects.all()
    if q:
        apps = apps.filter(libelle__icontains=q)
        initial["q"] = q
    if tag:
        apps = apps.filter(tags__in=[int(tag)])
        initial["tag"] = tag

    form = SearchForm(initial=initial)
    context["form"] = form
    context["apps"] = apps
    context['extra_args'] = "&q=%s&tag=%s" % (q if q else "", tag if tag else "")
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context)


@login_required
@permission_required("core.can_view_etabib_store", return_403=True)
@is_doctor_or_professionnal
@has_access(EtabibService.ETABIB_WORKSPACE)
def etabibWorkspace(request):
    context = {
        "sidebar_store": True
    }
    return redirect("https://drive.google.com/drive/folders/1opj6EChQucjFz2AlYkN4Z4NghRt2-lCZ")
