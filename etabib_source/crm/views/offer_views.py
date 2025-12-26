import json
import tempfile

import weasyprint
from datatableview import Datatable, columns
from datatableview.views import DatatableView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from el_pagination.decorators import page_template
from fm.views import AjaxUpdateView, AjaxDeleteView, AjaxCreateView
from num2words import num2words

from core.decorators import is_operator
from core.enums import OfferStatus
from core.models import Medecin, OffrePrepaye, Facture, Service, ServiceFedilite, Action, Contact, OffrePartenaire, \
    Virement, FactureCompany, FactureCompanyDetail, OffrePersonnalise_Service, DetailAction, Facture_OffrePrep_Licence
from core.templatetags.offer_tags import is_including_etabib_workspace
from core.utils import applyDiscount, get_nextautoincrement, has_value, getAvailableLicenses
from crm import utils
from crm.forms.operator_forms import OrderForm, CustomOrderForm, OrderPartnerForm, \
    VirementForm, InvoiceForm, LineItemFormset, InvoiceFormCancel, ServiceAssignForm
from crm.models import Commande
from etabibWebsite import settings
from etabibWebsite.settings import STATIC_ROOT


@login_required
@page_template('partial/list-offer-partial.html')
def listPrepaidOffer(request, template="commercial/list-offer.html", extra_context=None):
    title = _("Liste des offre prépayées")
    com_sidebar_offer = True
    com_sidebar_list_prep_offer = True
    offres = OffrePrepaye.objects.all()
    offers_active = [o for o in offres if o.status == OfferStatus.ACTIVE]
    offers_inactive = [o for o in offres if o.status == OfferStatus.INACTIVE]
    offers_expired = [o for o in offres if o.status == OfferStatus.EXPIRED]

    offres = offers_active + offers_inactive + offers_expired

    context = {
        'title': title,
        'com_sidebar_offer': com_sidebar_offer,
        'com_sidebar_list_prep_offer': com_sidebar_list_prep_offer,
        'offres': offres
    }
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context)


@login_required
@page_template('partial/list-offer-partial.html')
def listPartnerOffer(request, template="commercial/list-offer.html", extra_context=None):
    title = _("Liste des offre")
    com_sidebar_offer = True
    com_sidebar_list_partn_offer = True
    offres = OffrePartenaire.objects.all()
    offers_active = [o for o in offres if o.status == OfferStatus.ACTIVE]
    offers_inactive = [o for o in offres if o.status == OfferStatus.INACTIVE]
    offers_expired = [o for o in offres if o.status == OfferStatus.EXPIRED]

    offres = offers_active + offers_inactive + offers_expired

    context = {
        'title': title,
        'com_sidebar_offer': com_sidebar_offer,
        'com_sidebar_list_partn_offer': com_sidebar_list_partn_offer,
        'offres': offres
    }
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context)


@login_required
def detailOffer(request, pk, slug):
    offre = get_object_or_404(OffrePrepaye, pk=pk, slug=slug)
    title = _("Détail de l'offre: %s") % offre.libelle
    com_sidebar_offer = True
    return render(request, "commercial/detail-offer.html", locals(), using=request.template_version)


@login_required
def detailOfferPartner(request, pk, slug):
    offre = get_object_or_404(OffrePartenaire, pk=pk, slug=slug)
    title = _("Détail de l'offre: %s") % offre.libelle
    com_sidebar_offer = True
    return render(request, "commercial/detail-offer.html", locals())


@login_required
@is_operator
def createOrder(request, action_pk):
    com_sidebar_order = True
    commande = None
    title = _("Ajout d'une commande")
    action = get_object_or_404(Action, pk=action_pk)

    pre = request.GET.get("pre", None)
    if pre:
        commande = Commande.objects.filter(id=pre).first()

    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user, action=action)
        if form.is_valid():
            facture = form.save()
            if commande:
                commande.traitee = True
                commande.bon_commande = facture
                commande.save()
            messages.success(request, _('La commande %s créée avec succès') % (facture.id))
            return HttpResponseRedirect(reverse('detail-order', kwargs={'pk': facture.pk}))

    else:
        form = OrderForm(action=action)
    return render(request, "commercial/create-order.html", locals())


@login_required
@is_operator
def createPartnerOrder(request, action_pk):
    com_sidebar_order = True
    title = _("Ajout d'une commande")
    action = get_object_or_404(Action, pk=action_pk)
    if request.method == 'POST':
        form = OrderPartnerForm(request.POST, user=request.user, action=action)
        if form.is_valid():
            facture = form.save()
            messages.success(request, _('La commande %s créée avec succès') % (facture.id))
            return HttpResponseRedirect(reverse('detail-order', kwargs={'pk': facture.pk}))

    else:
        form = OrderPartnerForm(action=action)
    return render(request, "commercial/create-order.html", locals())


@login_required
@is_operator
def createCustomOrder(request):
    com_sidebar_create_order = True
    com_sidebar_create_order_cust = True
    com_sidebar_order = True
    title = _("Ajout d'une commande personnalisée")

    if request.method == 'POST':
        form = CustomOrderForm(request.POST, user=request.user)
        if form.is_valid():
            print("is valid")
            facture = form.save()
            messages.success(request, _('La commande %s créée avec succès') % (facture.id))
            return HttpResponseRedirect(reverse('commercial-list-order'))
        else:
            print("is not valid")
    else:
        form = CustomOrderForm()
    return render(request, "commercial/create-order-perso.html", locals())


@login_required
def detailOrder(request, pk):
    context = {}
    if hasattr(request.user, 'medecin'):
        facture = get_object_or_404(Facture, pk=pk, medecin__user=request.user)
    else:
        facture = get_object_or_404(Facture, pk=pk)

    title = _("Détail de la commande: %s") % facture.id
    com_sidebar_order = True
    if facture.medecin:
        avantages = facture.offre_prepa.avantages if facture.offre_prepa else facture.offre_perso.avantages
        context["generated_password"] = facture.medecin.contact.mdp_genere
        context["avantages"] = avantages,
        context["offre_perso_services"] = facture.offre_perso_services_set()

    context.update({
        "title": title,
        "com_sidebar_order": com_sidebar_order,
        "facture": facture,
    })
    return render(request, "commercial/detail-order.html", context, using=request.template_version)


@login_required
@is_operator
def loadInvoice(request):
    articles = []
    services_fedelite = []
    context = {}
    commercial = request.user.operateur

    if request.is_ajax():
        """
            Case 1: Print invoice from order detail
        """
        order_id = request.POST.get('order_id', None)
        order_type = request.POST.get('order_type', "1")
        if order_id:
            try:
                order = Facture.objects.get(pk=order_id)
                if order_type == "1":  # bon de commande
                    title = _("Bon de Commande")
                    numero = order.id
                elif order_type == "2":
                    title = _("Bon de livraison")
                    numero = order.id
                else:
                    title = _("Facture")
                    if hasattr(order, "infos"):
                        numero = order.infos.numero

                commercial = order.commercial.operateur if order.commercial else ""
                reduction_offre_status = None
                reduction_categorie = order.reduction_categorie
                reduction_type = order.reduction_type
                reduction = order.reduction
                negocie_ttc = order.negocie_ttc

                if order.medecin:
                    context.update({"contact": order.medecin.contact})
                if order.partenaire:
                    context.update({"contact": order.partenaire.contact})

                if order.offre_prepa:
                    context.update({"offre": order.offre_prepa})
                    quantite = order.fol_facture_set.count() if order.fol_facture_set else 0
                    total_ht = quantite * order.offre_prepa.prix
                    if order.coupon:
                        total_ht = applyDiscount(total_ht, order.coupon)

                    articles.append({
                        "article": order.offre_prepa.libelle,
                        "prix": order.offre_prepa.prix,
                        'quantite': quantite,
                        "total": total_ht
                    })

                    if order.offre_prepa.avantages:
                        for av in order.offre_prepa.avantages.all():
                            services_fedelite.append({
                                "libelle": av.libelle,
                            })
                elif order.offre_perso:
                    if order.offre_perso.avantages:
                        for av in order.offre_perso.avantages.all():
                            services_fedelite.append({
                                "libelle": av.libelle,
                            })
                    services = order.offre_perso.services

                    total_ht = 0
                    if services:
                        for service in services.all():
                            os = service.offre_perso_service_set.get(offre=order.offre_perso)
                            total_ht += os.quantite * service.tarif
                            articles.append({
                                "article": service.designation,
                                "prix": service.tarif,
                                'quantite': os.quantite,
                                "total": os.quantite * service.tarif
                            })
                    if order.coupon:
                        total_ht = applyDiscount(total_ht, order.coupon)

                elif order.offre_partenaire:
                    context.update({"offre": order.offre_prepa})
                    quantite = 1
                    total_ht = order.total

                    if order.coupon:
                        total_ht = applyDiscount(total_ht, order.coupon)

                    articles.append({
                        "article": order.offre_partenaire.libelle,
                        "prix": order.offre_partenaire.prix.amount,
                        'quantite': quantite,
                        "total": total_ht
                    })


            except Facture.DoesNotExist:
                raise Http404
        else:
            """
               Case 2: Print invoice from create order page
            """
            contact_id = request.POST.get('contact_id', None)
            offre_id = request.POST.get('offre_id', None)
            avantages = request.POST.get('avantages', None)
            quantite = request.POST.get('quantite', None)
            reduction_categorie = request.POST.get('reduction_categorie', None)
            reduction_type = request.POST.get('reduction_type', None)
            reduction = request.POST.get('reduction', None)
            negocie_ttc = json.loads(request.POST.get('negocie_ttc', None))
            reduction_offre_status = None

            contact = None
            partner_order = False
            if contact_id:
                try:
                    contact = Contact.objects.get(pk=contact_id)
                    context.update({"contact": contact})
                except Contact.DoesNotExist:
                    context.update({"contact": None})

            if offre_id:
                if contact:
                    if hasattr(contact, "partenaire"):
                        try:
                            offre = OffrePartenaire.objects.get(pk=offre_id)
                            context.update({"offre": offre})
                            partner_order = True
                        except OffrePrepaye.DoesNotExist:
                            context.update({"offre": None})
                    else:
                        try:
                            offre = OffrePrepaye.objects.get(pk=offre_id)
                            reduction_offre_status = offre.reduction_status(contact)
                            context.update({"offre": offre})
                        except OffrePrepaye.DoesNotExist:
                            context.update({"offre": None})

            total_ht = 0
            if quantite:
                if quantite.isdigit():
                    total_ht = int(quantite) * offre.prix

                    articles.append({
                        "article": offre.libelle,
                        "prix": offre.prix,
                        'quantite': quantite,
                        "total": total_ht
                    })

                else:  # is a list of strings separated with commas ex: service_id1,qte1,service_id2,qte2
                    array = iter(quantite.split(','))
                    for service_id, qte in zip(array, array):
                        try:
                            service = Service.objects.get(pk=service_id)
                            total_ht += int(qte) * service.tarif
                            articles.append({
                                "article": service.designation,
                                "prix": service.tarif,
                                'quantite': qte,
                                "total": int(qte) * service.tarif
                            })
                        except Service.DoesNotExist:
                            pass

            if partner_order:
                total_ht = offre.prix.amount
                articles.append({
                    "article": offre.libelle,
                    "prix": offre.prix,
                    'quantite': 1,
                    "total": total_ht
                })

            if avantages:  # a list of strings separated with commas ex: avantage_id1,avantage_id2,avantage_id3....
                array = avantages.split(",")
                for av_id in array:
                    try:
                        sf = ServiceFedilite.objects.get(pk=av_id)
                        services_fedelite.append({
                            "libelle": sf.libelle,
                        })
                    except ServiceFedilite.DoesNotExist:
                        pass

            if order_type == "1":  # bon de commande
                title = _("Bon de Commande")
                numero = get_nextautoincrement(Facture)
            if order_type == "2":  # bon de livraison
                title = _("Bon de livraison")
                numero = get_nextautoincrement(Facture)

        # Calculate reduction
        reduction_valeur = 0
        if reduction_type and has_value(Facture.REDUCTION_TYPE, reduction_type):
            if reduction_type == Facture.REDUCTION_TYPE[1][0]:
                # pourcentage
                reduction_valeur = "%.2f" % (float(total_ht) * float(reduction) / 100)
                context.update({"reduction": "{} %".format(reduction)})
                context.update({"total_reduction": float(total_ht) - float(reduction_valeur)})
            elif reduction_type == Facture.REDUCTION_TYPE[2][0]:
                # basé sur l'argent
                reduction_valeur = float(reduction)
                context.update({"reduction": "%s DA" % reduction})
                context.update({"total_reduction": float(total_ht) - float(reduction_valeur)})
        # if the offer has a reduction ignore all previous reductions
        if reduction_offre_status and reduction_offre_status['has_reduction']:
            reduction_valeur = (offre.prix - offre.prix_reduit) * int(quantite)
            context.update({"reduction": "%s DA" % reduction_valeur})
            context.update({"total_reduction": float(total_ht) - float(reduction_valeur)})

        # calculate tva
        tva = "%.2f" % ((total_ht - float(reduction_valeur)) * settings.TVA / 100)
        tva_text = "TVA {}%".format(settings.TVA)

        # calculate total
        if not negocie_ttc:
            total = "%.2f" % ((total_ht - float(reduction_valeur)) + float(tva))
        else:
            total = total_ht - float(reduction_valeur)

        context.update({"date": timezone.now().strftime("%m/%d/%Y")})
        context.update({"tva": tva})
        context.update({"tva_text": tva_text})
        context.update({"currency": "DA"})
        context.update({"items": articles})
        context.update({"loyalty_services": services_fedelite})
        context.update({"total_ht": total_ht})
        context.update({"total": total})
        context.update({"total2words": num2words(total, lang='fr') + " Dinars"})
        context.update({"invoice_number": numero})
        context.update({"invoice_title": title})
        context.update({"commercial": commercial})

    return render(request, "partial/invoice.html", context)


class OrderDatatable(Datatable):
    id = columns.TextColumn(_("N°"), sources=['id'])
    contact_nom = columns.TextColumn(source=['medecin__contact__nom', 'partenaire__contact__nom'])
    contact_prenom = columns.TextColumn(source=['medecin__contact__prenom', 'partenaire__contact__prenom'])
    contact = columns.TextColumn(_("Contact"), source=None, processor='get_entry_contact')
    offre = columns.TextColumn(_("Offre"), source=None, processor='get_entry_offre')
    commercial = columns.TextColumn(source=['commercial__get_full_name'])
    commercial_nom = columns.TextColumn(source=['commercial__first_name'])
    commercial_prenom = columns.TextColumn(source=['commercial__last_name'])
    use_epayment = columns.TextColumn(_("ePayment"), source=None, processor='get_use_epayment')
    is_payed = columns.TextColumn(_("Payé"), source=None, processor='get_entry_payed')
    quantite = columns.TextColumn(source=None, processor='get_entry_quantite')
    date_creation = columns.TextColumn(_("Date de création"), source=None, processor='get_entry_date_creation')
    actions = columns.TextColumn(_("Actions"), source=None, processor='get_entry_action')

    class Meta:
        columns = ["id", "contact", "offre", "quantite", "commercial", "use_epayment", "is_payed", "date_creation"]
        hidden_columns = ["contact_nom", "contact_prenom", "commercial_nom", "commercial_prenom"]
        search_fields = ["id", 'medecin__contact__nom', "medecin__contact__prenom", "partenaire__contact__nom",
                         "partenaire__contact__prenom"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 10

    def get_entry_date_creation(self, instance, **kwargs):
        if instance.date_creation:
            return instance.date_creation.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_entry_payed(self, instance, **kwargs):
        if instance.est_paye:
            return "<i class='fa fa-check green'></i>"
        else:
            return "<i class='fa fa-remove red'></i><br><p>Reste: %s</p>" % instance.rest_a_paye()

    def get_use_epayment(self, instance, **kwargs):
        if instance.ordre_paiement:
            return "<i class='fa fa-check green'></i>"
        return "<i class='fa fa-remove red'></i>"

    def get_entry_offre(self, instance, **kwargs):
        if instance.medecin:
            if instance.offre_perso:
                return 'Offre Personnalisée'
            else:
                if instance.offre_prepa:
                    return "<a href='{}'>{}</a>".format(
                        reverse('detail-offer', args=(instance.offre_prepa.id, instance.offre_prepa.slug)),
                        instance.offre_prepa.libelle)
        elif instance.partenaire:
            if instance.offre_partenaire:
                return "<a href='{}'>{}</a>".format(
                    reverse('detail-offer-partner',
                            args=(instance.offre_partenaire.id, instance.offre_partenaire.slug)),
                    instance.offre_partenaire.libelle
                )
        return ""

    def get_entry_contact(self, instance, **kwargs):
        if instance.medecin:
            contact = instance.medecin.contact
        elif instance.partenaire:
            contact = instance.partenaire.contact
        return "<a href='{}'>{}</a>".format(
            reverse('operator-detail-contact', args=(contact.id,)),
            contact)

    def get_entry_quantite(self, instance, **kwargs):
        if instance.fol_facture_set.all():
            return instance.fol_facture_set.count() if instance.fol_facture_set.count() > 0 else ""
        elif instance.fop_facture_set.all():
            return instance.fop_facture_set.count() if instance.fop_facture_set.count() > 0 else ""
        return ""

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-orders-actions.html",
                                {'order': instance, "user": self.view.request.user})


class OrderDatatableView(DatatableView):
    template_name = "commercial/order-list.html"
    model = Facture
    datatable_class = OrderDatatable

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.medecin_id = kwargs['medecin_id'] if 'medecin_id' in kwargs else None
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(OrderDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Listes des commandes")
        context['com_sidebar_list_order'] = True
        context['com_sidebar_order'] = True
        if self.medecin_id:
            try:
                medecin = Medecin.objects.get(id=self.medecin_id)
                context['medecin'] = medecin
            except Medecin.DoesNotExist:
                pass
        return context

    def get_queryset(self):
        if self.medecin_id:
            return Facture.objects.filter(medecin__id=self.medecin_id)
        return Facture.objects.all()


class AssignServiceView(SuccessMessageMixin, AjaxCreateView):
    form_class = ServiceAssignForm
    model = OffrePersonnalise_Service
    success_message = _("Commande mise à jour avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class InvoiceDatatable(Datatable):
    id = columns.TextColumn(_("N°"), sources=['id'])
    first_last_name = columns.TextColumn(_("Nom prénom"), source=['first_last_name'])
    numero = columns.TextColumn(_("Numéro"), source=['numero'])
    numero_commande = columns.TextColumn(source=['numero_commande'])
    commercial = columns.TextColumn(source=['commercial__get_full_name'])
    commercial_nom = columns.TextColumn(source=['commercial__first_name'])
    commercial_prenom = columns.TextColumn(source=['commercial__last_name'])
    status = columns.TextColumn(sources=None, processor='get_entry_status')
    date_creation = columns.TextColumn(_("Date de création"), source=None, processor='get_entry_date_creation')
    actions = columns.TextColumn(_("Actions"), source=None, processor='get_entry_action')

    class Meta:
        columns = ["id", "first_last_name", "numero", "numero_commande", "commercial", "date_creation"]
        hidden_columns = ["commercial_nom", "commercial_prenom"]
        search_fields = ["id", 'first_last_name', "numero", "numero_commande", "commercial__first_name",
                         "commercial__last_name"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 10

    def get_entry_date_creation(self, instance, **kwargs):
        if instance.date_creation:
            return instance.date_creation.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_entry_status(self, instance, **kwargs):
        if instance.annuler:
            return _("Annuler")
        return ""

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-invoices-actions.html",
                                {'invoice': instance, "user": self.view.request.user})


class InvoiceDatatableView(DatatableView):
    template_name = "commercial/invoice-list.html"
    model = FactureCompany
    datatable_class = InvoiceDatatable

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(InvoiceDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Listes des Facture")
        context['com_sidebar_list_invoice'] = True
        context['com_sidebar_order'] = True
        return context

    def get_queryset(self):
        return FactureCompany.objects.all()


@login_required
@is_operator
def createInvoice(request, pk=None):
    if pk == '1':
        template = 'commercial/invoice-create.html'
    else:
        template = 'commercial/invoice-create-ttc.html'
    if request.method == 'GET':
        formset = LineItemFormset(request.GET or None)
        form = InvoiceForm(request.GET or None)

    elif request.method == 'POST':
        formset = LineItemFormset(request.POST)
        form = InvoiceForm(request.POST)

        if form.is_valid() and formset.is_valid():
            remises_et_rabais = form.cleaned_data.get('remises_et_rabais') or 0
            frais_de_livraison = form.cleaned_data.get('frais_de_livraison') or 0
            timbre = form.cleaned_data.get('timbre') or 0
            date_limite = form.data["date_limite_reglement"] or None

            invoice = FactureCompany.objects.create(
                first_last_name=form.data["first_last_name"],
                numero_commande=form.data["numero_commande"],
                adresse=form.data["adresse"],
                numeros_telephone=form.data["numeros_telephone"],
                numeros_fax=form.data["numeros_fax"],
                numero_registre_commerce=form.data["numero_registre_commerce"],
                numero_identification_fiscale=form.data["numero_identification_fiscale"],
                numero_identification_domaine=form.data["numero_identification_domaine"],
                adresse_electronique=form.data["adresse_electronique"],
                numero_article=form.data["numero_article"],
                numero_tin=form.data["numero_tin"],
                statut=form.data["statut"],
                date_limite_reglement=date_limite,
                mode_de_paiement=form.data["mode_de_paiement"],
                remises_et_rabais=remises_et_rabais,
                frais_de_livraison=frais_de_livraison,
                timbre=timbre,
            )
            for form in formset:
                designation = form.cleaned_data.get('designation')
                quantity = form.cleaned_data.get('quantity')
                montant = form.cleaned_data.get('montant')
                pourcentage_tva = form.cleaned_data.get('tva')
                if designation and quantity and montant and pourcentage_tva:
                    FactureCompanyDetail(
                        facturecompany=invoice,
                        designation=designation,
                        quantity=quantity,
                        montant=montant,
                        pourcentage_tva=pourcentage_tva,
                    ).save()
            invoice.commercial = request.user
            invoice.save()
            return redirect('invoice-detail', pk=invoice.pk)
    context = {
        "title": "Factures",
        "formset": formset,
        "form": form,
    }
    return render(request, template, context)


class InvoiceUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = InvoiceFormCancel
    model = FactureCompany
    success_message = _("Facture Annulée")

    def form_valid(self, form):
        facturecompany = form.save(commit=False)
        facturecompany.annuler = True
        facturecompany.save()
        return super(InvoiceUpdateView, self).form_valid(form)


@login_required
def detailInvoice(request, pk):
    com_sidebar_order = True
    title = _("Facture")
    print("facture")
    facture_company = FactureCompany.objects.get(pk=pk)
    context = {}

    context.update({
        "title": title,
        "com_sidebar_order": com_sidebar_order,
        "facture": facture_company,
    })
    return render(request, "commercial/invoice-detail.html", context)


@login_required
@is_operator
def invoice_as_pdf(request, pk=None):
    facture = FactureCompany.objects.get(pk=pk)
    logo1 = STATIC_ROOT + '/img/logo/ihsm.png'
    logo2 = STATIC_ROOT + '/img/logo/logdo.png'
    html_string = render_to_string('partial/invoice-print.html',
                                   {'facture': facture,
                                    'total2words': num2words(facture.total_with_tva_r_f_t, lang='fr') + " Dinars",
                                    'logo1': logo1,
                                    'logo2': logo2
                                    }
                                   )

    pg = weasyprint.CSS(
        string=(
            """
            @page {
                size: a4;
                margin: 1cm;
            }
            """
        )
    )

    stylesheets = [
        weasyprint.CSS(STATIC_ROOT + '/style.css'),
        weasyprint.CSS(STATIC_ROOT + '/css/facture.css'),
        weasyprint.CSS(STATIC_ROOT + '/css/bootstrap.min.css'),
        pg
    ]

    html = weasyprint.HTML(
        string=html_string, base_url=request.build_absolute_uri('/')
    ).render(stylesheets=stylesheets)
    result = html.write_pdf()

    # Creating http response
    response = HttpResponse(content_type='application/pdf;')
    response['Content-Disposition'] = 'inline; filename=ordonnance.pdf'
    response['Content-Transfer-Encoding'] = 'binary'
    with tempfile.NamedTemporaryFile(delete=True) as output:
        output.write(result)
        output.flush()
        output = open(output.name, 'rb')
        response.write(output.read())
    return response


class OrderUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = OrderForm
    model = Facture
    success_message = _("Commande mise à jour avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super(OrderUpdateView, self).get_initial()
        initial["reduction_categorie"] = self.object.reduction_categorie
        initial["reduction_type"] = self.object.reduction_type
        initial["reduction"] = self.object.reduction
        initial["negocie_ttc"] = self.object.negocie_ttc
        return initial


class OrderDeleteView(AjaxDeleteView):
    form_class = OrderForm
    model = Facture
    success_message = _("Commande supprimée avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        # Case: offre prepaye
        if self.get_object().offre_prepa:
            self.get_object().fol_facture_set.all().delete()
            if self.get_object().detail_action:
                self.get_object().detail_action.delete()
        # Case: offre postPaye
        elif self.get_object().offre_perso:
            services = self.get_object().offre_perso.services
            if services:
                for service in services.all():
                    os = service.offre_perso_service_set.get(offre=self.get_object().offre_perso)
                    os.delete()

            self.get_object().offre_perso.delete()
        # Case: offre_partenaire
        elif self.get_object().offre_partenaire:
            self.get_object().fop_facture_set.all().delete()
            if self.get_object().detail_action:
                self.get_object().detail_action.delete()
        messages.success(self.request, self.success_message)
        return super(OrderDeleteView, self).delete(request, *args, **kwargs)


"""
    Virement
"""


class VirementDatatable(Datatable):
    id = columns.TextColumn(_("N°"), sources=['id'])
    medecin_nom = columns.TextColumn(source=['facture__medecin__contact__nom'])
    medecin_prenom = columns.TextColumn(source=['facture__medecin__contact__prenom'])
    medecin = columns.TextColumn(_("Médecin"), source=None, processor='get_entry_medecin')
    image = columns.TextColumn(_("Image"), source=None, processor='get_entry_image')
    ajouter_par = columns.TextColumn(source=['ajouter_par__get_full_name'])
    methode = columns.TextColumn(_("Méthode de paiement"), source=['get_methode_paiement_display'])
    verifie = columns.TextColumn(_("Vérifié"), source=None, processor='get_entry_verified')
    montant = columns.TextColumn(source=["montant"], )
    date_creation = columns.TextColumn(_("Date de création"), source=None, processor='get_entry_date_creation')
    actions = columns.TextColumn(_("Actions"), source=None, processor='get_entry_action')

    class Meta:
        columns = ["id", "medecin", "ajouter_par", "montant", "methode", "date_creation", "verifie", "image", "actions"]
        hidden_columns = ["medecin_nom", "medecin_prenom"]
        search_fields = ["id", 'facture__medecin__contact__nom', 'facture__medecin__contact__prenom',
                         'ajouter_par__first_name', 'ajouter_par__last_name']
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 10

    def get_entry_date_creation(self, instance, **kwargs):
        if instance.date_creation:
            return instance.date_creation.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_entry_image(self, instance, **kwargs):
        if instance.image:
            return '<a class="image-link" data-lightbox="roadtrip" href="%s">%s</a>' % (
                instance.image.url, _("Afficher")
            )
        return ""

    def get_entry_medecin(self, instance, **kwargs):
        if instance.facture:
            return "<a href='{}'>{}</a>".format(
                reverse('operator-detail-contact', args=(instance.facture.medecin.contact.id,)),
                instance.facture.medecin.full_name)
        elif hasattr(instance.ajouter_par, 'medecin'):
            return "<a href='{}'>{}</a>".format(
                reverse('operator-detail-contact', args=(instance.ajouter_par.medecin.contact.id,)),
                instance.ajouter_par.medecin.full_name)

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-virements-actions.html",
                                {'virement': instance, "user": self.view.request.user})

    def get_entry_verified(self, instance, **kwargs):
        if instance.verifie:
            return "<i class='fa fa-check green'></i>"
        else:
            return "<i class='fa fa-remove red'></i>"


class VirementDatatableView(DatatableView):
    template_name = "commercial/virement-list.html"
    model = Virement
    datatable_class = VirementDatatable

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.medecin_id = kwargs['medecin_id'] if 'medecin_id' in kwargs else None
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(VirementDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Listes des commandes")
        context['com_sidebar_list_virement'] = True
        if self.medecin_id:
            try:
                medecin = Medecin.objects.get(id=self.medecin_id)
                context['medecin'] = medecin
            except Medecin.DoesNotExist:
                pass
        return context

    def get_queryset(self):
        if self.medecin_id:
            return Virement.objects.filter(medecin__id=self.medecin_id)
        return Virement.objects.all()


class VirementCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = VirementForm
    model = Virement
    success_message = _("Virement ajouté!")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.commercial = request.user
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        virement = form.save(commit=False)
        virement.ajouter_par = self.commercial
        virement.save()
        return super(VirementCreateView, self).form_valid(form)


class VirementUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = VirementForm
    model = Virement
    success_message = _("Virement mise à jour!")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.commercial = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super(VirementUpdateView, self).get_initial()
        if self.object.facture:
            initial["contact"] = self.object.facture.medecin.contact
        return initial


class VirementDeleteView(AjaxDeleteView):
    form_class = VirementForm
    model = Virement
    success_message = _("Virement supprimée!")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(VirementDeleteView, self).delete(request, *args, **kwargs)


@login_required
@is_operator
def createOrderDirectly(request, contact_pk, commande_pk, action_pk=None):
    with transaction.atomic():
        commande = Commande.objects.filter(id=commande_pk).first()
        if commande.offre == '0':
            offre = OffrePrepaye.objects.get(libelle="ONE")
        elif commande.offre == '1':
            offre = OffrePrepaye.objects.get(libelle="TWO")
        elif commande.offre == '2':
            offre = OffrePrepaye.objects.get(libelle="THREE")
        quantite = commande.quantite

        facture = Facture()
        facture.commercial = request.user
        contact = get_object_or_404(Contact, id=contact_pk)

        medecin = contact.medecin
        facture.medecin = medecin
        facture.total = utils.calculateTotal(quantite, offre)
        if action_pk:
            detail = DetailAction()
            detail.action = Action.objects.get(pk=action_pk)
            detail.description = _("Commande pour une offre prépayée")
            detail.cree_par = request.user.operateur
            detail.save()
            facture.detail_action = detail
        facture.save()

        virement = Virement()
        if commande.methode_paiement == '0':
            virement.methode_paiement = '1'
        elif commande.methode_paiement == '1':
            virement.methode_paiement = '7'
        elif commande.methode_paiement == '2':
            virement.methode_paiement = '2'
        virement.montant = commande.versement_initial
        virement.image = commande.image.image
        virement.ajouter_par = request.user
        virement.facture = facture
        virement.save()

        if is_including_etabib_workspace(offre):
            licences = getAvailableLicenses(quantite)
            for i in range(quantite):
                fol = Facture_OffrePrep_Licence()
                fol.facture = facture
                fol.offre = offre
                if licences:
                    fol.licence = licences[i]
                    fol.save()

        commande.traitee = True
        commande.bon_commande = facture
        commande.save()
        messages.add_message(request, messages.SUCCESS, 'La commande est validé.')
        return HttpResponseRedirect(reverse('detail-order', kwargs={'pk': facture.id, }))
