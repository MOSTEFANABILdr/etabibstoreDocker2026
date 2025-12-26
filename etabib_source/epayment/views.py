import traceback
from datetime import datetime

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from djmoney.money import Money
from fm.views import AjaxCreateView
from post_office import mail
from rest_framework.authtoken.models import Token

from core import tasks
from core.enums import Role
from core.models import OffrePrepaye, Facture, Facture_OffrePrep_Licence
from core.templatetags.offer_tags import is_including_etabib_workspace
from core.templatetags.role_tags import is_patient, is_doctor
from core.templatetags.utils_tags import offer_id_unhash, user_id_unhash, coupon_id_unhash
from core.utils import applyDiscount, applyTVA, getAvailableLicenses
from coupons.models import Coupon
from epayment.forms import EpaymentForm, SendTicketForm, DoctorVirementForm
from epayment.models import OrdreDePaiement
from etabibWebsite import settings
from etabibWebsite.settings import env


def epaymentPortal(request):
    template_name = 'epayment-portal.html'

    # GET PARAMETERS
    token = request.GET.get('token', None)
    user_id_hashed = request.GET.get('u', None)
    r = request.GET.get('r', None)
    offer_id_hashed = request.GET.get('o', None)
    coupon_id_hashed = request.GET.get('c', None)

    context = {}
    token_object = None
    huser = None
    offre = None
    coupon = None
    initial = {}
    if token:
        try:
            token_object = Token.objects.get(key=token)
            template_name = 'epayment-portal-token.html'
        except Token.DoesNotExist:
            pass

    if user_id_hashed:
        try:
            userId = user_id_unhash(user_id_hashed)
            huser = User.objects.get(id=userId)
        except User.DoesNotExist:
            pass

    if coupon_id_hashed:
        try:
            couponId = coupon_id_unhash(coupon_id_hashed)
            coupon = Coupon.objects.get(id=couponId)
            if coupon.is_redeemed or coupon.expired():
                coupon = None
        except Coupon.DoesNotExist:
            pass

    if offer_id_hashed:
        try:
            offreId = offer_id_unhash(offer_id_hashed)
            offre = OffrePrepaye.objects.get(id=offreId)
            if offre.has_reduction(huser):
                prix = offre.prix_reduit
            else:
                prix = offre.prix
            total = applyTVA(prix)
            if coupon:
                total = applyDiscount(total, coupon)
            initial["montant"] = total
            context['hide_montant_select'] = True
        except OffrePrepaye.DoesNotExist:
            pass

    if not huser and not token_object:
        raise Http404

    if r:
        if r == "NOT_ENOUGH_MONEY":
            messages.warning(request, _(
                "Désolé, vous n'avez pas assez d'argent pour faire une téléconsultation, veuillez recharger votre compte."))

    user = huser if huser else token_object.user

    if request.method == 'POST':
        form = EpaymentForm(request.POST, initial=initial)
        if form.is_valid():
            oNumber = datetime.now().microsecond
            url = settings.EPAYMENT_REGISTER_URL
            returnUrl = request.build_absolute_uri('/epayment/recharge/')
            if token_object:
                returnUrl = returnUrl + "?token=%s" % token
            elif huser:
                returnUrl = returnUrl + "?u=%s" % user_id_hashed
            if offre:
                returnUrl = returnUrl + "&o=%s" % offer_id_hashed
            if coupon:
                returnUrl = returnUrl + "&c=%s" % coupon_id_hashed
            param = {'userName': env('API_U'), 'password': env('API_P'), 'language': 'fr',
                     'currency': '012', 'orderNumber': oNumber, 'amount': form.montant_a_recharger,
                     'returnUrl': returnUrl}

            try:
                resp = requests.post(url, data=param)
                if resp.status_code == requests.codes.ok:
                    # Save OrderId
                    json_resp = resp.json()
                    order = OrdreDePaiement()
                    order.numero_ordre = oNumber
                    order.ordre_uuid = json_resp['orderId']
                    order.montant = int(form.montant_a_recharger) / 100  # reconvertir en dinars
                    order.user = user
                    order.save()

                    return HttpResponseRedirect(json_resp['formUrl'])
                else:
                    resp.raise_for_status()
            except Exception as e:
                print(e)
                messages.error(request, "Un problème est survenu lors de l'opération. Veuillez réessayer.")
        else:
            messages.error(request, form.errors)
    elif request.method == 'GET':
        if 'orderId' in request.GET:
            orderId = request.GET['orderId']
            ordre = get_object_or_404(OrdreDePaiement, ordre_uuid=orderId)

            if ordre.etat == OrdreDePaiement.ETATS_ORDRE[1][0]:
                if token_object:
                    prms = "?token=%s" % token
                elif huser:
                    prms = "?u=%s" % user_id_hashed
                if offre:
                    prms = prms + "&o=%s" % offer_id_hashed
                if coupon:
                    prms = prms + "&c=%s" % coupon_id_hashed

                return redirect(reverse('epayment-preview', kwargs={"ordre_uuid": orderId}) + prms)

            if not ordre.user == user:
                return redirect('index')

            url = settings.EPAYMENT_ORDER_STATU_URL
            param = {'userName': env('API_U'), 'password': env('API_P'),
                     'language': 'fr', 'orderId': orderId}
            try:
                resp = requests.post(url, data=param)
                json = resp.json()

                print('-------------------------------------------------------------------')
                print(json)
                print('-------------------------------------------------------------------')

                if json['orderStatus'] == 2 and json['errorCode'] == '0':
                    # Success
                    if offre:
                        # Case: Aboonement
                        with transaction.atomic():
                            facture = Facture()
                            facture.medecin = user.medecin
                            if offre.has_reduction(huser):
                                facture.reduction_categorie = facture.REDUCTION_CATEGORIE[1][0]
                                facture.reduction_type = facture.REDUCTION_TYPE[2][0]
                                facture.reduction = offre.prix - offre.prix_reduit

                            if coupon:
                                facture.total = applyDiscount(offre.prix, coupon)
                                facture.coupon = coupon
                                coupon.redeem(user=user)
                            else:
                                facture.total = offre.prix
                            facture.ordre_paiement = ordre
                            facture.save()
                            licences = None
                            if is_including_etabib_workspace(offre):
                                # Get list of available licences
                                licences = getAvailableLicenses(1)
                            fol = Facture_OffrePrep_Licence()
                            fol.facture = facture
                            fol.offre = offre
                            if licences:
                                fol.licence = licences[0]
                            fol.save()
                    else:
                        # Case: Rechargemet de compte
                        if is_patient(user):
                            if user.patient.solde is None:
                                user.patient.solde = Money(amount=ordre.montant, currency='DZD')
                            else:
                                user.patient.solde += Money(amount=ordre.montant, currency='DZD')
                            user.patient.save()

                        elif is_doctor(user):
                            if user.medecin.solde is None:
                                user.medecin.solde = Money(amount=ordre.montant, currency='DZD')
                            else:
                                user.medecin.solde += Money(amount=ordre.montant, currency='DZD')
                            user.medecin.save()

                    ordre.etat = OrdreDePaiement.ETATS_ORDRE[1][0]
                    ordre.numero_autorisation = json['authRefNum']
                    ordre.save()

                    if token_object:
                        prms = "?token=%s" % token
                    elif huser:
                        prms = "?u=%s" % user_id_hashed
                    if offre:
                        prms = prms + "&o=%s" % offer_id_hashed
                    if coupon:
                        prms = prms + "&c=%s" % coupon_id_hashed

                    messages.success(request, "Votre demande de paiement a été acceptée.")
                    return redirect(reverse('epayment-preview', kwargs={"ordre_uuid": orderId}) + prms)

                else:  # Failure
                    ordre.etat = OrdreDePaiement.ETATS_ORDRE[3][0]
                    ordre.save()
                    return render(request, template_name, {'form': EpaymentForm(),
                                                           'success': False, 'msg': json['actionCodeDescription']})
            except Exception as e:
                traceback.print_exc()
                messages.error(request, "Un problème est survenu lors de l'opération. Veuillez réessayer.")

    context['form'] = EpaymentForm(initial=initial)
    context['user'] = user
    return render(request, template_name, context, using=request.template_version)


def epaymentPreview(request, ordre_uuid):
    template_name = 'epayment-preview.html'
    opaiment = get_object_or_404(OrdreDePaiement, ordre_uuid=ordre_uuid, etat="Validé")
    context = {}
    context['opaiment'] = opaiment

    token = request.GET.get('token', None)
    user_id_hashed = request.GET.get('u', None)
    offer_id_hashed = request.GET.get('o', None)
    coupon_id_hashed = request.GET.get('c', None)
    # TODO:complete offre AND coupon

    token_object = None
    huser = None
    if token:
        try:
            token_object = Token.objects.get(key=token)
            template_name = 'epayment-portal-token.html'
        except Token.DoesNotExist:
            pass

    if user_id_hashed:
        try:
            userId = user_id_unhash(user_id_hashed)
            huser = User.objects.get(id=userId)
        except User.DoesNotExist:
            pass

    if not huser and not token_object:
        raise Http404

    user = huser if huser else token_object.user

    if request.method == "POST":
        form = SendTicketForm(request.POST)
        if form.is_valid():

            mail.send(
                form.cleaned_data['email'],
                settings.DEFAULT_FROM_EMAIL,
                template='send_ticket_template',
                context={
                    'opaiment': opaiment,
                },
            )
            messages.success(request, "Email envoyé.")
            pass
        else:
            messages.success(request, form.errors)
    else:
        form = SendTicketForm()
    context['form'] = form
    return render(request, template_name, context, using=request.template_version)


def epaymentMethod(request, user_hash=None, offer_hash=None, coupon_hash=None):
    template_name = 'epayment-method.html'
    context = {}
    if coupon_hash:
        url = ("%s?u=%s&o=%s&c=%s" % (
            reverse('epayment-method-coupon'), user_hash, offer_hash, coupon_hash
        ))
    else:
        url = ("%s?u=%s&o=%s" % (
            reverse('epayment-recharge'), user_hash, offer_hash
        ))
    context["url"] = url
    return render(request, template_name, context, using=request.template_version)


class VirementCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = DoctorVirementForm
    success_message = _("Virement ajouté!")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.utilisateur = request.user
        self.type = request.GET.get("type", None)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(VirementCreateView, self).get_form_kwargs()
        kwargs.update({"type": self.type})
        return kwargs

    def form_valid(self, form):
        virement = form.save(commit=False)
        virement.verifie = False
        virement.ajouter_par = self.utilisateur
        virement.save()
        users = User.objects.filter(groups__name=Role.COMMERCIAL.value)
        tasks.notify(
            virement,
            recipients=users,
            description="Un nouveaux virement est fait",
            url=reverse("commercial-list-virement")
        )
        return super(VirementCreateView, self).form_valid(form)
