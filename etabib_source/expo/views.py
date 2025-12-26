from itertools import chain

import basehash
from datatableview import Datatable, columns
from datatableview.views import DatatableView
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from fm.views import AjaxCreateView
from guardian.decorators import permission_required
from post_office import mail

from core.mixins import TemplateVersionMixin
from expo.forms import StandSearchForm, PrecommandeForm
from core.forms.forms import EtabibExpoSignupForm
from core.models import Stand, Article, Partenaire, Catalogue, Produit, AutreProduit
from core.utils import generateJwtToken, checkJitsiRoomExists
from etabibWebsite import settings


def signup(request):
    if request.method == 'POST':
        form = EtabibExpoSignupForm(request.POST)
        if form.is_valid():
            user, password = form.save()
            context = {}
            context["email"] = user.email
            mail.send(
                user.email,
                settings.DEFAULT_FROM_EMAIL,
                template='expo_registration',
                context={
                    'username': user.email,
                    'password': password,
                    'login_link': "{}://{}".format(request.scheme, request.get_host())
                },
            )
            return render(request, "account/informations_sent.html", context)
    else:
        form = EtabibExpoSignupForm()
    context = {}
    context['form'] = form
    return render(request, "expo/signup.html", context)


@login_required
def expos(request, extra_context=None):
    context = {}
    sidebar_expos = True
    active_stands = Stand.objects.exclude(publie=False).exclude((Q(slogan='') | Q(slogan__isnull=True)))
    empty_stand = Stand.objects.exclude(publie=False).exclude(~Q(slogan='') | Q(slogan__isnull=True))
    context['sidebar_expos'] = sidebar_expos
    context['stands'] = list(chain(active_stands, empty_stand))
    context['form'] = StandSearchForm(initial={'stand': None})
    return render(request, "expo/expo.html", context, using=request.template_version)


@login_required
def stand_detail(request, pk):
    sidebar_expos = True
    stand = get_object_or_404(Stand, id=pk)
    acticles = Article.soft_objects.filter(partenaire=stand.partner)
    ROOM_SIZE_API_URL = "https://%s/api/room-size?room=%s&domain=meet.jitsi" % (
        settings.ECONGRE_JITSI_DOMAIN_NAME, stand.salle_discussion
    )

    context = {
        "sidebar_expos": sidebar_expos,
        "stand": stand,
        "acticles": acticles,
        "ROOM_SIZE_API_URL": ROOM_SIZE_API_URL
    }
    return render(request, "expo/stand-detail.html", context, using=request.template_version)


@login_required
def campany_detail(request, pk):
    partenaire = get_object_or_404(Partenaire, id=pk)
    catalogues = Catalogue.objects.filter(cree_par=partenaire)
    context = {
        "sidebar_expos": True,
        "partenaire": partenaire,
        "catalogues": catalogues,
    }
    return render(request, "expo/company-detail.html", context, using=request.template_version)


class PrecommandeArticleCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = PrecommandeForm
    success_message = _("L'exposant à reçu votre Précommande!")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.article_pk = kwargs['article_pk'] if 'article_pk' in kwargs else None
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        cat = form.save(commit=False)
        cat.cree_par = self.user
        cat.article = Article.objects.get(id=self.article_pk)
        cat.save()
        return super(PrecommandeArticleCreateView, self).form_valid(form)


@login_required
@permission_required("core.can_get_expo_badge", return_403=True)
def badge(request, token=None):
    contact = None
    if hasattr(request.user, 'medecin'):
        contact = request.user.medecin.contact
    elif hasattr(request.user, 'professionnelsante'):
        contact = request.user.professionnelsante.contact

    hash_fn = basehash.base56(32)
    if token:
        try:
            user_id = hash_fn.unhash(token)
            valid = (user_id == request.user.id)
        except:
            valid = False
        return render(request, "expo/badge_validation.html", {"valid": valid})
    else:
        hsh = hash_fn.hash(request.user.id)
        badge_url = request.build_absolute_uri(
            reverse("expo-badge-verification", args=[hsh])
        )
        if settings.ENVIRONMENT != settings.Environment.DEV:
            badge_url = badge_url.replace("http://", "https://")
        context = {
            "badge_url": badge_url,
            "badge_sidebar": True,
            "contact": contact
        }
    return render(request, "expo/badge-generation.html", context)


@login_required
def checkStandVisio(request):
    if request.is_ajax():
        stand_id = request.POST.get('stand_id', None)
        stand = get_object_or_404(Stand, pk=stand_id)
        if checkJitsiRoomExists(stand.salle_discussion):
            return JsonResponse({}, status=200)
        else:
            return JsonResponse({'error': "Not found"}, status=204)
    return JsonResponse({}, status=400)


@login_required
def standVisio(request, stand_id=None):
    context = {}
    if request.is_ajax():
        stand_id = request.POST.get('stand_id', None)
        stand = get_object_or_404(Stand, pk=stand_id)
        if checkJitsiRoomExists(stand.salle_discussion):
            return JsonResponse({'url': reverse(standVisio, args=[stand_id])}, status=200)
        else:
            return JsonResponse({'error': "Forbidden"}, status=400)
    else:
        stand = get_object_or_404(Stand, pk=stand_id)
        if stand.partner.user == request.user:
            # generate jwt token
            jwtToken = generateJwtToken(request.user)
            if jwtToken:
                context['jwtToken'] = jwtToken
        context.update({
            "stand": stand,
            "sidebar_viso": True
        })
        return render(request, "partner/meeting.html", context=context)


class ExposantDatatable(Datatable):
    exposant = columns.TextColumn(_("Exposant"), source=None, processor='get_exposant')

    class Meta:
        columns = ["exposant", ]
        structure_template = "partial/datatable-bootstrap-structure.html"
        search_fields = ['user__first_name', 'user__last_name']
        ordering = ['-id']
        page_length = 10

    def get_exposant(self, instance, **kwargs):
        return instance


class ExposantDatatableView(TemplateVersionMixin, DatatableView):
    template_name = "expo/list-exposants.html"
    model = Partenaire
    datatable_class = ExposantDatatable

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ExposantDatatableView, self).get_context_data(**kwargs)
        context["sidebar_expos"] = True
        return context

    def get_queryset(self):
        return Partenaire.objects.all()


class FirmeDatatable(Datatable):
    firme = columns.TextColumn(_("Firme"), source=None, processor='get_firme')
    exposant = columns.TextColumn(_("Exposant"), source=None, processor='get_exposant')

    class Meta:
        columns = ["firme", "exposant", ]
        structure_template = "partial/datatable-bootstrap-structure.html"
        search_fields = [
            'autreproduit__marque', 'produit__marque', 'partenaire__user__first_name', 'partenaire__user__last_name'
        ]
        page_length = 10

    def get_exposant(self, instance, **kwargs):
        return instance.partenaire

    def get_firme(self, instance, **kwargs):
        if isinstance(instance, Produit) or isinstance(instance, AutreProduit):
            return instance.marque
        return ""


class FirmeDatatableView(TemplateVersionMixin, DatatableView):
    template_name = "expo/list-firme.html"
    model = Article
    datatable_class = FirmeDatatable

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(FirmeDatatableView, self).get_context_data(**kwargs)
        context["sidebar_expos"] = True
        return context

    def inTuple(self, tuple, tuples):
        for t in tuples:
            if t[0] == tuple[0] and t[1] == tuple[1]:
                return True
        return False

    def get_queryset(self):
        articles = Article.soft_objects.filter(
            Q(produit__marque__isnull=False) | Q(autreproduit__marque__isnull=False)
        ).exclude(medic__isnull=False)
        tuples = ()
        ids = []
        for article in articles:
            if isinstance(article, Produit):
                t = (article.produit.marque, article.partenaire.id)
                if not self.inTuple(t, tuples):
                    tuples = tuples + ((article.produit.marque, article.partenaire.id),)
                    ids.append(article.id)
            elif isinstance(article, AutreProduit):
                t = (article.autreproduit.marque, article.partenaire.id)
                if not self.inTuple(t, tuples):
                    tuples = tuples + ((article.autreproduit.marque, article.partenaire.id),)
                    ids.append(article.id)
        qs = articles.filter(id__in=ids)
        return qs
