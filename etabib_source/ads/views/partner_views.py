# -*- coding: utf-8 -*-
import json
from datetime import timedelta

from datatableview import Datatable, columns
from datatableview.views import DatatableView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q, Count, F, Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import DetailView
from el_pagination.decorators import page_template
from fm.views import AjaxCreateView, AjaxDeleteView, AjaxUpdateView

from appointements.models import DemandeRendezVous
from core.decorators import is_registered, is_partner
from ads.forms.partner_forms import PartnerRegistrationForm, ProductForm, ArticleImageUploadForm, \
    ArticleDocumentUploadForm, DrugForm, OtherProductForm, AnnonceFeedForm, AnnonceDisplayForm, AdsImageUploadForm, \
    CampagneImpForm, CampagneActivationForm, CampagneAnnulationForm, AdsVideoUploadForm, AnnonceVideoForm, \
    CampagneStopForm, PartenaireProfileForm, StandForm, CatalogueForm, LogoTrademarkUploadForm
from core.mixins import TemplateVersionMixin

CampagneStopForm, CatalogueForm, StandForm
from core.models import Produit, ArticleImage, ArticleDocument, Medic, Article, AutreProduit, Annonce, AnnonceFeed, \
    AnnonceDisplay, AnnonceImage, Campagne, CampagneImpression, AnnonceImpressionLog, AnnonceClickLog, \
    CampagneStatistique, PointsHistory, AnnonceVideo, Video, Catalogue, Stand, PartenaireMarque, PrecommandeArticle
from core.templatetags.partner_tags import renderProductType, renderAnnonceType, renderCampagneType, \
    renderCampagneStatus


@login_required
@is_partner
def dashboard(request):
    par_sidebar_dashboard = True
    title = _("Dashboard")
    untreated_appointments = DemandeRendezVous.objects.filter(
        destinataire=request.user,
        acceptee=False,
        annulee=False,
        refusee=False
    ).count()
    context = {
        'title': title,
        'par_sidebar_dashboard': par_sidebar_dashboard,
        "untreated_appointments": untreated_appointments,
    }
    return render(request, "partner/dashboard.html", context)


@login_required
@is_registered
def registerPartner(request):
    if request.method == 'POST':
        form = PartnerRegistrationForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('/partner/validate/')
    else:
        form = PartnerRegistrationForm(user=request.user)
    return render(request, "partner/register.html", {"form": form})


class ArticleDatatable(Datatable):
    type = columns.TextColumn(_("Type"), source=None, processor='get_entry_type')
    action = columns.TextColumn(_("Actions"), source=None, processor='get_entry_action')
    date_creation = columns.TextColumn(_("Date de création"), source=None, processor='get_entry_date_creation')

    class Meta:
        columns = ["libelle", "type", "date_creation"]
        search_fields = ['libelle']
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 20

    def get_entry_date_creation(self, instance, **kwargs):
        if instance.date_creation:
            return instance.date_creation.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-products-actions.html",
                                {'product': instance})

    def get_entry_type(self, instance, **kwargs):
        return renderProductType(instance)

    def get_entry_prix(self, instance, **kwargs):
        if isinstance(instance, Produit):
            return instance.prix
        elif isinstance(instance, Medic):
            return instance.prix


class ArticleDatatableView(DatatableView):
    template_name = "partner/products.html"
    model = Article
    datatable_class = ArticleDatatable

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        self.partenaire = request.user.partenaire
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ArticleDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Mes produits")
        context['par_sidebar_products'] = True
        return context

    def get_queryset(self):
        if self.partenaire:
            return Article.soft_objects.filter(partenaire=self.partenaire)


class ArticleDetailView(TemplateVersionMixin, DetailView):
    model = Article
    slug_field = "slug"
    slug_url_kwarg = 'slug'
    template_name = "partner/product_detail.html"
    context_object_name = 'product'

    def get_queryset(self):
        return Article.objects.filter(slug=self.kwargs['slug'], id=self.kwargs['pk'])

    @method_decorator(login_required)
    # @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ArticleDetailView, self).get_context_data(**kwargs)
        context['title'] = self.get_object().libelle
        context['images'] = ArticleImage.objects.filter(article=self.get_object())
        return context


class ArticleDeleteView(AjaxDeleteView):
    model = Article
    success_message = _("Produit supprimée avec succès")
    unauthorized_message = _("Vous ne pouvez pas supprimer ce produit")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        if request.user != self.get_object().partenaire.user:
            return self.render_json_response({'status': 'error', 'message': self.unauthorized_message})

        messages.success(self.request, self.success_message)
        return super(ArticleDeleteView, self).delete(request, *args, **kwargs)


##############################################
# 'Produit' views create, update,
##############################################
class ProductCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = ProductForm
    model = Produit
    success_message = _("Produit créé avec succès")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        self.partenaire = request.user.partenaire
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        produit = form.save(commit=False)
        produit.partenaire = self.partenaire
        produit.save()
        imgs = form.getImages()
        if imgs:
            for img in imgs:
                try:
                    pi = ArticleImage.objects.get(id=int(img))
                    pi.article = produit
                    pi.save()
                except Exception as e:
                    print(e)

        file1 = form.getFile(1)
        file2 = form.getFile(2)
        if file1:
            pi = ArticleDocument.objects.get(id=int(file1))
            produit.document_aut = pi
            produit.save()
        if file2:
            pi = ArticleDocument.objects.get(id=int(file2))
            produit.document_hom = pi
            produit.save()

        return super(ProductCreateView, self).form_valid(form)


class ProductUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = ProductForm
    model = Produit
    success_message = _("Produit mise à jour avec succès")
    unauthorized_message = _("Vous ne pouvez pas mettre à jour ce produit")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        if request.user != self.get_object().partenaire.user:
            return self.render_json_response({'status': 'error', 'message': self.unauthorized_message})
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        context = {}
        try:
            if self.get_object():
                pis = ArticleImage.objects.filter(article=self.get_object())
                if pis.count() > 0:
                    l = []
                    for pi in pis.all():
                        l.append(str(pi.id))
                    context['images'] = ",".join(l)
                if self.get_object().document_aut:
                    context['file1'] = self.get_object().document_aut.pk
                    context['file1_as_json'] = json.dumps(self.get_object().document_aut.to_json())
                if self.get_object().document_hom:
                    context['file2'] = self.get_object().document_hom.pk
                    context['file2_as_json'] = json.dumps(self.get_object().document_hom.to_json())
        except Exception as e:
            print(e)
        context['images_as_json'] = json.dumps([pi.to_json() for pi in pis.all()])
        return context

    def form_valid(self, form):
        produit = form.save(commit=False)
        produit.save()
        imgs = form.getImages()
        # delete deleted images
        ArticleImage.objects.filter(article=produit).exclude(id__in=imgs).delete()
        aisNew = ArticleImage.objects.filter(id__in=imgs)
        for ai in aisNew:
            ai.article = produit
            ai.save()

        file1 = form.getFile(1)
        file2 = form.getFile(2)
        if file1:
            pi = ArticleDocument.objects.get(id=int(file1))
            produit.document_aut = pi
            produit.save()
        if file2:
            pi = ArticleDocument.objects.get(id=int(file2))
            produit.document_hom = pi
            produit.save()

        return super(ProductUpdateView, self).form_valid(form)


def articleImageUpload(request):
    if request.is_ajax():
        form = ArticleImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            pi = form.save()
            return JsonResponse({'image_id': pi.pk}, status=200)
        else:
            return JsonResponse({'error': form.errors}, status=500)


def articleDocumentUpload(request):
    if request.is_ajax():
        form = ArticleDocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            pi = form.save()
            return JsonResponse({'file_id': pi.pk}, status=200)
        else:
            return JsonResponse({'error': form.errors}, status=500)


##############################################
# 'Medic' views create, update
##############################################
class DrugCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = DrugForm
    model = Medic
    success_message = _("Médicament/Parapharmacie créé avec succès")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        self.partenaire = request.user.partenaire
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        drug = form.save(commit=False)
        drug.partenaire = self.partenaire
        drug.save()
        imgs = form.getImages()
        if imgs:
            for img in imgs:
                try:
                    pi = ArticleImage.objects.get(id=int(img))
                    pi.article = drug
                    pi.save()
                except Exception as e:
                    print(e)

        file1 = form.getFile(1)
        file2 = form.getFile(2)
        if file1:
            pi = ArticleDocument.objects.get(id=int(file1))
            drug.document_aut_amm = pi
            drug.save()
        if file2:
            pi = ArticleDocument.objects.get(id=int(file2))
            drug.rcp = pi
            drug.save()

        return super(DrugCreateView, self).form_valid(form)


class DrugUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = DrugForm
    model = Medic
    success_message = _("Médicament/Parapharmacie mise à jour avec succès")
    unauthorized_message = _("Vous ne pouvez pas mettre à jour ce Médicament/Parapharmacie")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        if request.user != self.get_object().partenaire.user:
            return self.render_json_response({'status': 'error', 'message': self.unauthorized_message})
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        context = {}
        try:
            if self.get_object():
                pis = ArticleImage.objects.filter(article=self.get_object())
                if pis.count() > 0:
                    l = []
                    for pi in pis.all():
                        l.append(str(pi.id))
                    context['images'] = ",".join(l)
                if self.get_object().document_aut_amm:
                    context['file1'] = self.get_object().document_aut_amm.pk
                    context['file1_as_json'] = json.dumps(self.get_object().document_aut_amm.to_json())
                if self.get_object().rcp:
                    context['file2'] = self.get_object().rcp.pk
                    context['file2_as_json'] = json.dumps(self.get_object().rcp.to_json())
        except Exception as e:
            print(e)
        context['images_as_json'] = json.dumps([pi.to_json() for pi in pis.all()])
        return context

    def form_valid(self, form):
        drug = form.save(commit=False)
        drug.save()
        imgs = form.getImages()
        # delete deleted images
        ArticleImage.objects.filter(article=drug).exclude(id__in=imgs).delete()
        aisNew = ArticleImage.objects.filter(id__in=imgs)
        for ai in aisNew:
            ai.article = drug
            ai.save()

        file1 = form.getFile(1)
        file2 = form.getFile(2)
        if file1:
            pi = ArticleDocument.objects.get(id=int(file1))
            drug.document_aut_amm = pi
            drug.save()
        if file2:
            pi = ArticleDocument.objects.get(id=int(file2))
            drug.rcp = pi
            drug.save()

        return super(DrugUpdateView, self).form_valid(form)


##############################################
# 'AutreProduitَ' views create, update
##############################################
class OtherProductَCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = OtherProductForm
    model = AutreProduit
    success_message = _("Autre produit créé avec succès")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        self.partenaire = request.user.partenaire
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        otpr = form.save(commit=False)
        otpr.partenaire = self.partenaire
        otpr.save()
        imgs = form.getImages()
        if imgs:
            for img in imgs:
                try:
                    pi = ArticleImage.objects.get(id=int(img))
                    pi.article = otpr
                    pi.save()
                except Exception as e:
                    print(e)

        return super(OtherProductَCreateView, self).form_valid(form)


class OtherProductUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = OtherProductForm
    model = AutreProduit
    success_message = _("Produit mise à jour avec succès")
    unauthorized_message = _("Vous ne pouvez pas mettre à jour ce Produit")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        if request.user != self.get_object().partenaire.user:
            return self.render_json_response({'status': 'error', 'message': self.unauthorized_message})
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        context = {}
        try:
            if self.get_object():
                pis = ArticleImage.objects.filter(article=self.get_object())
                if pis.count() > 0:
                    l = []
                    for pi in pis.all():
                        l.append(str(pi.id))
                    context['images'] = ",".join(l)
        except Exception as e:
            print(e)
        context['images_as_json'] = json.dumps([pi.to_json() for pi in pis.all()])
        return context

    def form_valid(self, form):
        otpr = form.save(commit=False)
        otpr.save()
        imgs = form.getImages()
        # delete deleted images
        ArticleImage.objects.filter(article=otpr).exclude(id__in=imgs).delete()
        aisNew = ArticleImage.objects.filter(id__in=imgs)
        for ai in aisNew:
            ai.article = otpr
            ai.save()
        return super(OtherProductUpdateView, self).form_valid(form)


############################################
# Annonce Views
############################################
class AnnonceDatatable(Datatable):
    type = columns.TextColumn(_("Type"), source=None, processor='get_entry_type')
    action = columns.TextColumn(_("Actions"), source=None, processor='get_entry_action')
    date_creation = columns.TextColumn(_("Date de création"), source=None, processor='get_entry_date_creation')

    class Meta:
        columns = ["libelle", "type", "date_creation"]
        search_fields = ['libelle']
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 20

    def get_entry_date_creation(self, instance, **kwargs):
        if instance.date_creation:
            return instance.date_creation.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-ads-actions.html",
                                {'ads': instance})

    def get_entry_type(self, instance, **kwargs):
        return renderAnnonceType(instance)


class AnnonceDatatableView(DatatableView):
    template_name = "partner/ads.html"
    model = Annonce
    datatable_class = AnnonceDatatable

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        self.partenaire = request.user.partenaire
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AnnonceDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Mes annonces")
        context['par_sidebar_ads'] = True
        return context

    def get_queryset(self):
        if self.partenaire:
            return Annonce.soft_objects.filter(partenaire=self.partenaire)


class AnnonceDeleteView(AjaxDeleteView):
    model = Annonce
    success_message = _("Annonce supprimée avec succès")
    unauthorized_message = _("Vous ne pouvez pas supprimer cette Annonce")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        if request.user != self.get_object().partenaire.user:
            return self.render_json_response({'status': 'error', 'message': self.unauthorized_message})

        if self.get_object().campagneimpression_set.count() > 0:
            return self.render_json_response(
                {
                    'status': 'error',
                    'message': "Vous ne pouvez pas supprimer cette annonce car elle est liée à une campagne"
                }
            )
        messages.success(self.request, self.success_message)
        return super(AnnonceDeleteView, self).delete(request, *args, **kwargs)


def adsImageUpload(request):
    if request.is_ajax():
        form = AdsImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            pi = form.save()
            return JsonResponse({'file_id': pi.pk, "file_url": pi.image.url}, status=200)
        else:
            return JsonResponse({'error': form.errors}, status=500)


def adsVideoUpload(request):
    if request.is_ajax():
        form = AdsVideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            pi = form.save()
            return JsonResponse({'file_id': pi.pk, "file_url": pi.fichier.url}, status=200)
        else:
            return JsonResponse({'error': form.errors}, status=500)


class AnnonceDetailView(DetailView):
    model = Annonce
    template_name = "partner/annonce_detail.html"
    context_object_name = 'annonce'
    query_pk_and_slug = True

    def get_queryset(self):
        return Annonce.objects.filter(id=self.kwargs['pk'])

    @method_decorator(login_required)
    # @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        # if request.user != self.get_object().partenaire.user:
        #     return HttpResponse('Unauthorized', status=401)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AnnonceDetailView, self).get_context_data(**kwargs)
        context['title'] = self.get_object().libelle
        return context


##################
# Annonce Feed #
##################
class AnnonceFeedَCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = AnnonceFeedForm
    model = AnnonceFeed
    success_message = _("Annonce feed créé avec succès")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        self.partenaire = request.user.partenaire
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        adsFeed = form.save(commit=False)
        adsFeed.partenaire = self.partenaire
        adsFeed.save()
        return super(AnnonceFeedَCreateView, self).form_valid(form)


class AnnonceFeedUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = AnnonceFeedForm
    model = AnnonceFeed
    success_message = _("Annonce feed mise à jour avec succès")
    unauthorized_message = _("Vous ne pouvez pas mettre à jour cette Annonce feed")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        if request.user != self.get_object().partenaire.user:
            return self.render_json_response({'status': 'error', 'message': self.unauthorized_message})
        return super().dispatch(request, *args, **kwargs)


###################
# Annonce Display #
###################
class AnnonceDisplayَCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = AnnonceDisplayForm
    model = AnnonceDisplay
    success_message = _("Annonce display créé avec succès")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        self.partenaire = request.user.partenaire
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        adsDisp = form.save(commit=False)
        adsDisp.partenaire = self.partenaire
        adsDisp.save()
        im = form.getImage_200x360()
        if im:
            pi = AnnonceImage.objects.get(id=int(im))
            adsDisp.images.add(pi)
        im = form.getImage_728x360()
        if im:
            pi = AnnonceImage.objects.get(id=int(im))
            adsDisp.images.add(pi)
        im = form.getImage_450x416()
        if im:
            pi = AnnonceImage.objects.get(id=int(im))
            adsDisp.images.add(pi)
        im = form.getImage_1600x840()
        if im:
            pi = AnnonceImage.objects.get(id=int(im))
            adsDisp.images.add(pi)
        im = form.getImage_500x360()
        if im:
            pi = AnnonceImage.objects.get(id=int(im))
            adsDisp.images.add(pi)
        return super(AnnonceDisplayَCreateView, self).form_valid(form)


class AnnonceDisplayUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = AnnonceDisplayForm
    model = AnnonceDisplay
    success_message = _("Annonce DISPLAY mise à jour avec succès")
    unauthorized_message = _("Vous ne pouvez pas mettre à jour cette Annonce DISPLAY")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        if request.user != self.get_object().partenaire.user:
            return self.render_json_response({'status': 'error', 'message': self.unauthorized_message})
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        context = {}
        try:
            if self.get_object():
                if self.get_object().images.all():
                    for img in self.get_object().images.all():
                        if img.type == '2':
                            context['image_450x416'] = img.id
                            context['image_450x416_as_json'] = json.dumps(img.to_json())
                        elif img.type == '3':
                            context['image_200x360'] = img.id
                            context['image_200x360_as_json'] = json.dumps(img.to_json())
                        elif img.type == '4':
                            context['image_500x360'] = img.id
                            context['image_500x360_as_json'] = json.dumps(img.to_json())
                        elif img.type == '5':
                            context['image_728x360'] = img.id
                            context['image_728x360_as_json'] = json.dumps(img.to_json())
        except Exception as e:
            print(e)
        return context

    def form_valid(self, form):
        adsDisp = form.save(commit=False)
        adsDisp.save()
        adsDisp.images.clear()

        im = form.getImage_200x360()
        if im:
            pi = AnnonceImage.objects.get(id=int(im))
            adsDisp.images.add(pi)
        im = form.getImage_728x360()
        if im:
            pi = AnnonceImage.objects.get(id=int(im))
            adsDisp.images.add(pi)
        im = form.getImage_450x416()
        if im:
            pi = AnnonceImage.objects.get(id=int(im))
            adsDisp.images.add(pi)
        im = form.getImage_500x360()
        if im:
            pi = AnnonceImage.objects.get(id=int(im))
            adsDisp.images.add(pi)
        im = form.getImage_1600x840()
        if im:
            pi = AnnonceImage.objects.get(id=int(im))
            adsDisp.images.add(pi)
        return super(AnnonceDisplayUpdateView, self).form_valid(form)


###################
# Annonce Video #
###################
class AnnonceVideoَCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = AnnonceVideoForm
    model = AnnonceVideo
    success_message = _("Annonce video créé avec succès")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        self.partenaire = request.user.partenaire
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        annoncevideo = form.save(commit=False)
        video_id = form.cleaned_data['_video']
        video = get_object_or_404(Video, id=video_id)
        annoncevideo.video = video
        annoncevideo.partenaire = self.partenaire
        annoncevideo.save()
        return super(AnnonceVideoَCreateView, self).form_valid(form)


class AnnonceVideoUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = AnnonceVideoForm
    model = AnnonceVideo
    success_message = _("Annonce VIDEO mise à jour avec succès")
    unauthorized_message = _("Vous ne pouvez pas mettre à jour cette Annonce VIDEO")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        if request.user != self.get_object().partenaire.user:
            return self.render_json_response({'status': 'error', 'message': self.unauthorized_message})
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        context = {}
        try:
            if self.get_object():
                if self.get_object().fichier:
                    context['_video'] = self.get_object().fichier.id
        except Exception as e:
            print(e)
        return context

    def form_valid(self, form):
        annoncevideo = form.save(commit=False)
        video_id = form.cleaned_data['_video']
        video = get_object_or_404(Video, id=video_id)
        annoncevideo.video = video
        annoncevideo.save()
        return super(AnnonceVideoUpdateView, self).form_valid(form)


##################################
# Campagne views
##################################
class CampaignDatatable(Datatable):
    status = columns.TextColumn(_("Etat"), source=None, processor='get_entry_status')
    type = columns.TextColumn(_("Type"), source=None, processor='get_entry_type')
    reseaux = columns.TextColumn(_("Réseaux"), source=None, processor='get_entry_reseaux')
    action = columns.TextColumn(_("Actions"), source=None, processor='get_entry_action')
    date_creation = columns.TextColumn(_("Date de création"), source=None, processor='get_entry_date_creation')

    class Meta:
        columns = ["libelle", "type", "reseaux", "status", "date_creation"]
        search_fields = ['libelle']
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 20

    def get_entry_date_creation(self, instance, **kwargs):
        if instance.date_creation:
            return instance.date_creation.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_entry_reseaux(self, instance, **kwargs):
        if instance.reseaux:
            return str(instance.reseaux)
        return ""

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-campaign-actions.html",
                                {'campaign': instance})

    def get_entry_type(self, instance, **kwargs):
        return renderCampagneType(instance)

    def get_entry_status(self, instance, **kwargs):
        return renderCampagneStatus(instance)


class CampaignDatatableView(DatatableView):
    template_name = "partner/Campaigns.html"
    model = Campagne
    datatable_class = CampaignDatatable

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        self.partenaire = request.user.partenaire
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(CampaignDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Mes compagnes")
        context['par_sidebar_campaign'] = True
        return context

    def get_queryset(self):
        if self.partenaire:
            return Campagne.soft_objects.filter(partenaire=self.partenaire)


class CampagneDeleteView(AjaxDeleteView):
    model = Campagne
    success_message = _("Campagne supprimée avec succès")
    unauthorized_message = _("Vous ne pouvez pas supprimer cette Campagne")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        if request.user != self.get_object().partenaire.user:
            return self.render_json_response({'status': 'error', 'message': self.unauthorized_message})

        messages.success(self.request, self.success_message)
        return super(CampagneDeleteView, self).delete(request, *args, **kwargs)


class CampagneDetailView(DetailView):
    model = Campagne
    template_name = "partner/campaign_detail.html"
    context_object_name = 'campagne'

    def get_queryset(self):
        return Campagne.objects.filter(id=self.kwargs['pk'])

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(CampagneDetailView, self).get_context_data(**kwargs)
        context['title'] = self.get_object().libelle
        return context


#####################
# Campagne Impression
#####################
class CampagneImpَCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = CampagneImpForm
    model = CampagneImpression
    success_message = _("Campagne créé avec succès")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        self.partenaire = request.user.partenaire
        self.network = request.GET.get('network', None)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        cmp = form.save(commit=False)
        cmp.partenaire = self.partenaire
        cmp.reseaux = self.network
        cmp.save()
        return super(CampagneImpَCreateView, self).form_valid(form)


class CampagneImpUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = CampagneImpForm
    model = CampagneImpression
    success_message = _("Campagne mise à jour avec succès")
    unauthorized_message = _("Vous ne pouvez pas mettre à jour cette campagne")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        if request.user != self.get_object().partenaire.user:
            return self.render_json_response({'status': 'error', 'message': self.unauthorized_message})
        return super().dispatch(request, *args, **kwargs)


class CampagneImpActivateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = CampagneActivationForm
    model = CampagneImpression
    success_message = _("Campagne activée!.")
    unauthorized_message = _("Vous ne pouvez pas activer cette campagne")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        if request.user != self.get_object().partenaire.user:
            return self.render_json_response({'status': 'error', 'message': self.unauthorized_message})
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        comp = form.save(commit=False)
        comp.active = True
        comp.save()
        return super(CampagneImpActivateView, self).form_valid(form)


class CampagneImpCancelView(SuccessMessageMixin, AjaxUpdateView):
    form_class = CampagneAnnulationForm
    model = CampagneImpression
    success_message = _("Campagne annulée!")
    unauthorized_message = _("Vous ne pouvez pas annuler cette campagne")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        if request.user != self.get_object().partenaire.user:
            return self.render_json_response({'status': 'error', 'message': self.unauthorized_message})
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        comp = form.save(commit=False)
        comp.active = False
        comp.date_debut = None
        comp.date_fin = None
        comp.save()
        return super(CampagneImpCancelView, self).form_valid(form)


class CampagneImpStopView(SuccessMessageMixin, AjaxUpdateView):
    form_class = CampagneStopForm
    model = CampagneImpression
    success_message = _("Campagne arrêtée!")
    unauthorized_message = _("Vous ne pouvez pas arrêter cette campagne")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        if request.user != self.get_object().partenaire.user:
            return self.render_json_response({'status': 'error', 'message': self.unauthorized_message})
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        comp = form.save(commit=False)
        comp.active = False
        comp.date_debut = None
        comp.date_fin = None
        comp.save()
        return super(CampagneImpStopView, self).form_valid(form)


@login_required
@is_partner
@page_template('partial/points-history-list.html')
def pointsHistory(request, template="partner/points-history.html", extra_context=None):
    title = _("Historique des points")

    context = {
        "title": title,
    }

    phs = PointsHistory.objects.filter(Q(partenaire__user=request.user)).order_by("-id")
    context.update({"pointsHist": phs})
    # mark all notification where actor == partenaire as read
    qs = request.user.notifications.unread().filter(
        Q(
            actor_content_type=ContentType.objects.get_for_model(request.user.partenaire)
            , actor_object_id=request.user.partenaire.id
        )
    )
    qs.mark_all_as_read()

    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context)


@login_required
@is_partner
def campaignStats(request, pk):
    campagne = get_object_or_404(Campagne, pk=pk)
    if campagne.partenaire.user != request.user:
        raise Http404

    context = {}
    data = []
    date_imp = []
    date_clk = []
    cdate = None

    if campagne.date_debut and campagne.date_fin:
        if campagne.date_debut <= timezone.now() and campagne.date_fin >= timezone.now():
            cdate = timezone.now()
        elif campagne.date_debut <= timezone.now() and campagne.date_fin < timezone.now():
            cdate = campagne.date_fin
        if cdate:
            # get last 20 days statistics
            for i in range(20):
                item = {}
                d = cdate - timedelta(days=i)
                if d.date() < campagne.date_debut.date():
                    break
                item.update({'period': d.strftime("%Y-%m-%d")})
                impressions = AnnonceImpressionLog.objects.filter(
                    campagne=campagne,
                    date_impression__contains=d.date()
                ).count()
                item.update({'impressions': impressions})
                date_imp.append(impressions)

                clics = AnnonceClickLog.objects.filter(
                    campagne=campagne,
                    date_click__contains=d.date()
                ).count()
                item.update({'clics': clics})
                date_clk.append(clics)

                data.append(item)

    # statistic depend on speciality
    data_spec_all = []
    data_spec_imp = AnnonceImpressionLog.objects.filter(campagne=campagne).order_by(
        'user__medecin__contact__specialite').values(
        specialite=F('user__medecin__contact__specialite__libelle')).annotate(
        count=Count('specialite'))

    data_spec_clk = AnnonceClickLog.objects.filter(campagne=campagne).order_by(
        'user__medecin__contact__specialite').values(
        specialite=F('user__medecin__contact__specialite__libelle')).annotate(
        count=Count('specialite'))

    for dimp in data_spec_imp[:5]:
        d = {}
        d['specialite'] = dimp['specialite']
        d['imp_count'] = dimp['count']
        for dclk in data_spec_clk:
            if dclk['specialite'] == dimp['specialite']:
                d['clk_count'] = dclk['count']
                break

        data_spec_all.append(d)

    # statistic depends on zones
    data_zne_all = []
    data_zne_imp = AnnonceImpressionLog.objects.filter(campagne=campagne).order_by(
        'user__medecin__contact__ville').values(
        ville=F('user__medecin__contact__ville__name')).annotate(
        count=Count('ville'))

    data_zne_clk = AnnonceClickLog.objects.filter(campagne=campagne).order_by(
        'user__medecin__contact__ville').values(
        ville=F('user__medecin__contact__ville__name')).annotate(
        count=Count('ville'))

    for dimp in data_zne_imp[:5]:
        d = {}
        d['ville'] = dimp['ville']
        d['imp_count'] = dimp['count']
        for dclk in data_zne_clk:
            if dclk['ville'] == dimp['ville']:
                d['clk_count'] = dclk['count']
                break

        data_zne_all.append(d)

    # statistic depends on doctor's gender
    data_gdre_all = []
    data_gdre_imp = AnnonceImpressionLog.objects.filter(campagne=campagne).order_by(
        'user__medecin__contact__sexe').values(
        sexe=F('user__medecin__contact__sexe')).annotate(
        count=Count('sexe'))

    data_gdre_clk = AnnonceClickLog.objects.filter(campagne=campagne).order_by(
        'user__medecin__contact__sexe').values(
        sexe=F('user__medecin__contact__sexe')).annotate(
        count=Count('sexe'))

    for dimp in data_gdre_imp[:5]:
        d = {}
        d['sexe'] = dimp['sexe']
        d['imp_count'] = dimp['count']
        for dclk in data_gdre_clk:
            if dclk['sexe'] == dimp['sexe']:
                d['clk_count'] = dclk['count']
                break

        data_gdre_all.append(d)

    # statistics per ad
    if isinstance(campagne, CampagneImpression):
        adImpsOrd = AnnonceImpressionLog.objects.filter(campagne=campagne).order_by(
            'annonce__id').values(
            ad_id=F('annonce')).annotate(
            count=Count('ad_id')
        )
        data_per_ad = []
        for adImps in adImpsOrd:
            d = {}
            annonce = Annonce.objects.get(id=adImps['ad_id'])
            d['annonce'] = annonce
            d['campagne'] = campagne
            d['count_imp'] = adImps['count']
            d['count_clk'] = AnnonceClickLog.objects.filter(
                campagne=campagne, annonce=annonce
            ).count()
            data_per_ad.append(d)

        context['data_per_ad'] = data_per_ad

    context.update({
        'title': _("Statistiques") + ": " + campagne.libelle,
        'impressions': AnnonceImpressionLog.objects.filter(campagne=campagne).count(),
        'clics': AnnonceClickLog.objects.filter(campagne=campagne).count(),
        'cost': AnnonceClickLog.objects.filter(campagne=campagne).aggregate(
            total_cost=Coalesce(Sum('cout'), 0)
        )['total_cost'] +
                AnnonceImpressionLog.objects.filter(campagne=campagne).aggregate(
                    total_cost=Coalesce(Sum('cout'), 0)
                )['total_cost'],
        # TODO: filter by unique poste
        'data': data,
        'date_imp': date_imp,
        'date_clk': date_clk,
        'data_spec_all': data_spec_all,
        'data_zne_all': data_zne_all,
        'data_gdre_all': data_gdre_all,
    })
    return render(request, "partner/campaign_stats.html", context)


def campaignStatsByAnnonce(request):
    if request.is_ajax():
        context = {}
        annonce_id = request.POST.get('ad_pk', None)
        campaign_id = request.POST.get('cm_pk', None)
        arg = request.POST.get('arg', None)
        try:
            annonce = Annonce.objects.get(pk=annonce_id)
            campagne = Campagne.objects.get(pk=campaign_id)

            data = []
            if arg == "1":
                # Per sexe
                data_gdre_imp = AnnonceImpressionLog.objects.filter(
                    campagne=campagne, annonce=annonce
                ).order_by(
                    'user__medecin__contact__sexe').values(
                    sexe=F('user__medecin__contact__sexe')).annotate(
                    count=Count('sexe'))

                data_gdre_clk = AnnonceClickLog.objects.filter(
                    campagne=campagne, annonce=annonce
                ).order_by(
                    'user__medecin__contact__sexe').values(
                    sexe=F('user__medecin__contact__sexe')).annotate(
                    count=Count('sexe'))

                for dimp in data_gdre_imp[:5]:
                    d = {}
                    d['arg'] = dimp['sexe']
                    d['imp_count'] = dimp['count']
                    for dclk in data_gdre_clk:
                        if dclk['sexe'] == dimp['sexe']:
                            d['clk_count'] = dclk['count']
                            break

                    data.append(d)
            elif arg == "2":
                # Per zones
                data_zne_clk = AnnonceClickLog.objects.filter(
                    campagne=campagne, annonce=annonce
                ).order_by(
                    'user__medecin__contact__ville').values(
                    ville=F('user__medecin__contact__ville__name')).annotate(
                    count=Count('ville'))

                data_zne_imp = AnnonceImpressionLog.objects.filter(
                    campagne=campagne, annonce=annonce
                ).order_by(
                    'user__medecin__contact__ville').values(
                    ville=F('user__medecin__contact__ville__name')).annotate(
                    count=Count('ville'))

                for dimp in data_zne_imp[:5]:
                    d = {}
                    d['arg'] = dimp['ville']
                    d['imp_count'] = dimp['count']
                    for dclk in data_zne_clk:
                        if dclk['ville'] == dimp['ville']:
                            d['clk_count'] = dclk['count']
                            break

                    data.append(d)

            elif arg == "3":
                # Per speciality
                data_spec_clk = AnnonceClickLog.objects.filter(
                    campagne=campagne, annonce=annonce
                ).order_by(
                    'user__medecin__contact__specialite').values(
                    specialite=F('user__medecin__contact__specialite__libelle')).annotate(
                    count=Count('specialite'))

                data_spec_imp = AnnonceImpressionLog.objects.filter(
                    campagne=campagne, annonce=annonce
                ).order_by(
                    'user__medecin__contact__specialite').values(
                    specialite=F('user__medecin__contact__specialite__libelle')).annotate(
                    count=Count('specialite'))

                for dimp in data_spec_imp[:5]:
                    d = {}
                    d['arg'] = dimp['specialite']
                    d['imp_count'] = dimp['count']
                    for dclk in data_spec_clk:
                        if dclk['specialite'] == dimp['specialite']:
                            d['clk_count'] = dclk['count']
                            break

                    data.append(d)
            context['data'] = data

        except Annonce.DoesNotExist or Campagne.DoesNotExist:
            return JsonResponse({'error': "target data does not exist"}, status=404)
        return JsonResponse(context, status=200)
    return JsonResponse({'error': "no content"}, status=405)


@login_required
@page_template('partner/partial/catalogue-partial.html')
def catalogueList(request, partner_id=None, template="partner/catalogue_list.html", extra_context=None):
    if hasattr(request.user, "partenaire"):
        catalogues = Catalogue.objects.filter(cree_par=request.user.partenaire)
    elif partner_id != None:
        catalogues = Catalogue.objects.filter(cree_par__id=partner_id)

    context = {
        'catalogues': catalogues,
        "sidebar_catalogue": True
    }
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context, using=request.template_version)


class CatalogueCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = CatalogueForm
    success_message = _("Catalogue ajouté!")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        self.utilisateur = request.user.partenaire
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        cat = form.save(commit=False)
        cat.cree_par = self.utilisateur
        cat.save()
        return super(CatalogueCreateView, self).form_valid(form)


class CatalogueUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = CatalogueForm
    model = Catalogue
    success_message = _("Produit mise à jour avec succès")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        self.utilisateur = request.user.partenaire
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        cat = form.save(commit=False)
        cat.cree_par = self.utilisateur
        cat.save()
        return super(CatalogueUpdateView, self).form_valid(form)

class CatalogueDeleteView(AjaxDeleteView):
    model = Catalogue
    success_message = _("Catalogue supprimée avec succès")

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        return super(CatalogueDeleteView, self).dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(CatalogueDeleteView, self).delete(request, *args, **kwargs)


@login_required
@is_partner
def myStand(request):
    title = _('My Stand')
    stand = Stand.objects.filter(partner=request.user.partenaire).first()
    if request.method == 'POST':
        form = StandForm(request.POST, request.FILES, partenaire=request.user.partenaire, instance=stand)
        if form.is_valid():
            stand = form.save()
            messages.success(request, _("Mise à jour du stand réussie"))
    else:
        if stand:
            form = StandForm(instance=stand, partenaire=request.user.partenaire)
        else:
            form = StandForm(partenaire=request.user.partenaire, instance=stand)
    sidebar_stand = True

    context = {
        "title": title,
        "sidebar_stand": sidebar_stand,
        "stand": stand,
        "stand_image_url": stand.banner.url if stand else "http://via.placeholder.com/1600x840",
        "stand_signaletique": stand.signaletique if stand else "Signalétique",
        "stand_slogan": stand.slogan if stand else "Slogan",
        "form": form,
    }
    return render(request, "partner/stand.html", context)


@login_required
@is_partner
def profile(request):
    partner = request.user.partenaire
    if request.method == 'POST':
        form = PartenaireProfileForm(request.POST, request.FILES, user=request.user, instance=partner)
        if form.is_valid():
            partner = form.save()
            images = json.loads(form.getimages())
            imgs = [img['id'] for img in images]
            PartenaireMarque.objects.filter(partenaire=partner).exclude(id__in=imgs).delete()
            messages.success(request, _("Profile mis à jour"))
        else:
            messages.error(request, _("Veuillez verifier les champs en rouge"))
            print(form.errors)
    else:
        form = PartenaireProfileForm(user=request.user, instance=partner)
    context = {
        "form": form,
        "par_sidebar_profile": True,
        "title": _("Mon Profile")
    }
    return render(request, "partner/profile.html", context)


@login_required
@is_partner
def logo_trademark_upload(request):
    partner = request.user.partenaire
    if request.is_ajax():
        form = LogoTrademarkUploadForm(request.POST, request.FILES, user=partner)
        if form.is_valid():
            pi = form.save()
            return JsonResponse(pi.to_json(), status=200)
        else:
            return JsonResponse({'error': form.errors}, status=500)


class PrecommandeArticleDatatable(Datatable):
    telephone = columns.TextColumn(_("Contact"), source=None, processor='get_entry_phone')
    date_creation = columns.TextColumn(_("Date de création"), source=None, processor='get_entry_date_creation')
    cree_par = columns.TextColumn(_("Commanditeur"), source=None, processor='get_entry_name')

    class Meta:
        columns = ["cree_par", "telephone", "article", "quantite", "date_creation"]
        search_fields = ['article__libelle']
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 10

    def get_entry_phone(self, instance, **kwargs):
        if hasattr(instance.cree_par, "medecin"):
            if instance.cree_par.medecin.contact.mobile:
                return instance.cree_par.medecin.contact.mobile
            elif instance.cree_par.medecin.contact.fixe:
                return instance.cree_par.medecin.contact.fixe
            elif instance.cree_par.email:
                return instance.cree_par.email
            elif instance.cree_par.medecin.contact.email:
                return instance.cree_par.medecin.contact.email
        return ""

    def get_entry_date_creation(self, instance, **kwargs):
        if instance.date_creation:
            return instance.date_creation.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_entry_name(self, instance, **kwargs):
        if instance.cree_par:
            return instance.cree_par.get_full_name()
        return ""


class PrecommandeDatatableView(DatatableView):
    template_name = "partner/commandes.html"
    model = PrecommandeArticle
    datatable_class = PrecommandeArticleDatatable

    @method_decorator(login_required)
    @method_decorator(is_partner)
    def dispatch(self, request, *args, **kwargs):
        self.partenaire = request.user.partenaire
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(PrecommandeDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Carnet des commandes")
        context['par_sidebar_commmande'] = True
        return context

    def get_queryset(self):
        if self.partenaire:
            return PrecommandeArticle.objects.filter(article__partenaire=self.partenaire)
