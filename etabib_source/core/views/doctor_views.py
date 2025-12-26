# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal

import basehash
import magic
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from cities_light.models import Country, City
from crispy_forms.utils import render_crispy_form
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Q
from django.http.response import JsonResponse, Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.context_processors import csrf
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import linebreaks
from django.utils.translation import gettext as _
from djmoney.money import Money
from el_pagination.decorators import page_template
from fm.views import AjaxUpdateView, AjaxCreateView
from guardian.decorators import permission_required
from num2words import num2words
from post_office import mail

from appointements.models import DemandeRendezVous
from core import tasks
from core.decorators import is_registered, is_doctor, is_not_verified_doctor
from core.enums import Role, WebsocketCommand, OfferStatus, NotificationVerb
from core.forms.doctor_forms import ProfessionalCardUploadForm, ProfileForm, BusyForm, CertifUploadForm, \
    AnnonceFeedBackForm, DoctorIdentityForm, OfferSponsorisedOrderForm, DemoRequestForm, \
    FirstLoginForm, FirstLoginP1Form, FirstLoginP2Form
from core.forms.forms import AvatarForm
from core.models import Medecin, PointsHistory, Contact, OffrePrepaye, \
    Facture, Documentation, AnnonceFeedBack, Annonce, EquipeSoins, Bank, Certificat
from core.templatetags.utils_tags import has_license, user_id_hash, offer_id_hash, coupon_id_hash
from core.utils import get_nextautoincrement, createCommand
from coupons.models import Coupon
from etabibWebsite import settings
from teleconsultation.models import Tdemand, Presence


@login_required
@is_doctor
def index(request):
    return render(request, "doctor/dashboard.html")


@login_required
@is_doctor
@page_template('partial/docs-partial.html')
def docummentation(request, template="doctor/docs.html", extra_context=None):
    title = _("Documentations")
    q = request.GET.get('q', None)
    if q:
        documents = Documentation.objects.filter(libelle__icontains=q)
    else:
        documents = Documentation.objects.all()

    context = {
        "title": title,
        'documents': documents,
        "sidebar_documentation": True
    }
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context)


@login_required
@is_doctor
@permission_required("core.care_can_view_profile", return_403=True)
def doctorProfile(request):
    title = _('My Profile')
    medecin = get_object_or_404(Medecin, user=request.user)
    contact = medecin.contact
    if request.method == 'POST':
        avatarForm = AvatarForm()  # this form is submitted with ajax request see: views.avatarUpload
        form = ProfileForm(request.POST, medecin=medecin)
        if form.is_valid():
            form.save()
            messages.success(request, _("Mise à jour du profil réussie"))
    else:
        avatarForm = AvatarForm()
        form = ProfileForm(initial={
            'infos': medecin.infos,
            'facebook': contact.facebook,
            'twitter': contact.twitter,
            'pageweb': contact.pageweb,
            'qualifications': contact.qualifications.all(),
            'specialite': contact.specialite,
            'experience': contact.experience,
            'rang': contact.rang,
            'country': contact.pays,
            'city': contact.ville,
            'gps': contact.gps,
            'specialite_certificat_file_id': contact.specialite_certificat.id if contact.specialite_certificat else "",
            'agrement_id': contact.agrement.id if contact.agrement else "",
            'qualifications_certificat_file_id': ",".join(
                ["%s" % sc.pk for sc in contact.qualifications_certificats.all()]
            ),
            'tarif_consultation': medecin.tarif_consultation,
            'ccp': medecin.ccp,
            'cle': medecin.cle
        })
    sidebar_profile = True
    licenses = []
    for fac in medecin.facture_set.all():
        if fac.offre_prepa:
            for fol in fac.fol_facture_set.all():
                licenses.append((fol, fac))

        elif fac.offre_perso:
            for ops in fac.offre_perso_services_set():
                if ops.service.creer_licence:
                    licenses.append((ops, fac))
    isprofil_complete = (contact.pays and contact.ville and contact.mobile_1 and contact.specialite)
    context = {
        "title": title,
        "sidebar_profile": sidebar_profile,
        "medecin": medecin,
        "licenses": licenses,
        "form": form,
        "avatarForm": avatarForm,
        "form_p1": None if isprofil_complete else FirstLoginForm(
            initial={
                'nom': contact.nom,
                'prenom': contact.prenom,
                'pays': contact.pays,
                'ville': contact.ville,
                'adresse': contact.adresse,
            }
        ),
        "form_p2": None if isprofil_complete else FirstLoginP1Form(
            initial={
                'qualifications': contact.qualifications.all(),
                'specialite': contact.specialite,
            }
        ),
        "form_p3": None if isprofil_complete else FirstLoginP2Form(
            initial={
                'mobile': contact.mobile,
                'fixe': contact.fixe,
                'mobile_1': contact.mobile_1,
                'mobile_2': contact.mobile_2,
                'facebook': contact.facebook,
            }
        ),
        "files_spec": [
            {
                "source": contact.specialite_certificat.pk,
                "options": {
                    "type": 'local',
                    "file": {
                        "name": contact.specialite_certificat.filename,
                        "size": contact.specialite_certificat.file.size,
                        "id": contact.specialite_certificat.id,
                        "url": contact.specialite_certificat.file.url if contact.specialite_certificat.file else "",
                        "type": magic.Magic(mime=True).from_file(
                            contact.specialite_certificat.file.path) if contact.specialite_certificat.file else ""
                    }
                }
            }
        ] if contact.specialite_certificat else [],
        "files_agrm": [
            {
                "source": contact.agrement.pk,
                "options": {
                    "type": 'local',
                    "file": {
                        "name": contact.agrement.filename,
                        "size": contact.agrement.file.size,
                        "id": contact.agrement.id,
                        "url": contact.agrement.file.url if contact.agrement.file else "",
                        "type": magic.Magic(mime=True).from_file(
                            contact.agrement.file.path) if contact.agrement.file else ""
                    }
                }
            }
        ] if contact.agrement else [],
        "files_qual": [
            {
                "source": qc.pk,
                "options": {
                    "type": 'local',
                    "file": {
                        "name": qc.filename,
                        "size": qc.file.size,
                        "id": qc.id,
                        "url": qc.file.url if qc.file else "",
                        "type": magic.Magic(mime=True).from_file(
                            qc.file.path) if qc.file else ""
                    }
                }
            } for qc in contact.qualifications_certificats.all()
        ],
        "file_qual_arr": [qc.pk for qc in contact.qualifications_certificats.all()]
    }
    return render(request, "doctor/profile.html", context, using=request.template_version)


@login_required
@is_doctor
def update_profile(request, medecin_pk):
    if request.is_ajax():
        medecin = get_object_or_404(Medecin, id=medecin_pk)
        name = request.POST.get("name", None)
        value = request.POST.get("value", None)
        if name:
            if name == "nom":
                medecin.user.first_name = value
                medecin.contact.nom = value
            elif name == "prenom":
                medecin.user.last_name = value
                medecin.contact.prenom = value
            elif name == "sexe":
                medecin.contact.sexe = value
            elif name == "pays":
                medecin.contact.pays = Country.objects.get(id=value)
            elif name == "ville":
                medecin.contact.ville = City.objects.get(id=value)
            elif name == "adresse":
                medecin.contact.adresse = value
            elif name == "facebook":
                medecin.contact.facebook = value
            elif name == "twitter":
                medecin.contact.twitter = value
            elif name == "pageweb":
                medecin.contact.pageweb = value
            elif name == "infos":
                medecin.infos = value
            elif name == "mobile1":
                medecin.contact.mobile_1 = value
            elif name == "mobile2":
                medecin.contact.mobile_2 = value
            elif name == "fixe":
                medecin.contact.fixe = value
            elif name == "mobile":
                medecin.contact.mobile = value
            elif name == "consultation":
                if value:
                    medecin.tarif_consultation = Money(Decimal(value.replace(',', '.')), "DZD")
            elif name == "consultation_cabinet":
                if value:
                    medecin.tarif_cslt_cabinet = Money(Decimal(value.replace(',', '.')), "DZD")
            elif name == "consultation_domicile":
                if value:
                    medecin.tarif_cslt_domicile = Money(Decimal(value.replace(',', '.')), "DZD")
            elif name == "ccp":
                medecin.ccp = value
            elif name == "cle":
                medecin.cle = value
            elif name == "banque":
                medecin.bank = Bank.objects.get(id=value)
            elif name == "agence":
                medecin.bank_agence = value
            elif name == "rib":
                medecin.bank_rib = value
            elif name == "ncompte":
                medecin.bank_compte = value
            elif name == "specialite":
                medecin.contact.specialite_id = value
            elif name == "qualifications":
                values = request.POST.getlist("value[]", [])
                medecin.contact.qualifications.set(values)
            medecin.save()
            medecin.contact.save()
            medecin.user.save()
    return JsonResponse({}, status=200)


@login_required
@is_doctor
def delete_certificat(request):
    if request.is_ajax():
        id = request.POST.get("id", None)
        contact = request.user.medecin.contact
        if contact.specialite_certificat and id.isnumeric() and contact.specialite_certificat.id == int(id):
            contact.specialite_certificat = None
            contact.save()
        elif contact.qualifications_certificats.filter(id=id).exists():
            contact.qualifications_certificats.filter(id=id).delete()
        elif contact.agrement and id.isnumeric() and contact.agrement.id == int(id):
            contact.agrement = None
            contact.save()
        else:
            return JsonResponse({}, status=404)
        return JsonResponse({}, status=200)
    return JsonResponse({}, status=400)

@login_required
@is_doctor
@permission_required("core.care_can_view_dashboard", return_403=True)
@page_template('doctor/care-team-requests.html')
def dashboard(request, template="doctor/dashboard.html", extra_context=None):
    medecin = request.user.medecin
    sidebar_dashboard = True
    title = _("Dashboard")
    untreated_appointments = DemandeRendezVous.objects.filter(
        destinataire=medecin.user,
        acceptee=False,
        annulee=False,
        refusee=False
    ).count()
    today = timezone.now().date()
    today_first = datetime.datetime.combine(today, datetime.time.min)
    today_last = datetime.datetime.combine(today, datetime.time.max)
    today_appointments = DemandeRendezVous.objects.filter(
        destinataire=medecin.user,
        acceptee=True,
        date_rendez_vous__lte=today_last,
        date_rendez_vous__gte=today_first,
    ).count()
    care_team_requests = EquipeSoins.objects.filter(
        professionnel=request.user,
        confirme=False,
    )

    context = {
        "title": title,
        "sidebar_dashboard": sidebar_dashboard,
        "medecin": medecin,
        "untreated_appointments": untreated_appointments,
        "today_appointments": today_appointments,
        "care_team_requests": care_team_requests
    }
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context, using=request.template_version)


@login_required
@is_registered
def registerDoctor(request):
    if request.user.groups.count() == 0:
        with transaction.atomic():
            request.user.groups.add(Group.objects.get(name=Role.DOCTOR.value))
            contact = Contact()
            contact.save()

            medecin = Medecin()
            medecin.user = request.user
            medecin.contact = contact
            medecin.save()
    else:
        raise Http404
    return redirect(reverse("doctor-dashboard"))


@login_required
@is_not_verified_doctor
def doctorIdentity(request):
    context = {}
    if request.method == "POST":
        form = DoctorIdentityForm(request.POST, request.FILES, medecin=request.user.medecin)
        if form.is_valid():
            form.save()
            return redirect("doctor-dashboard")
    else:
        form = DoctorIdentityForm()
    context['form'] = form
    return render(request, "doctor/doctor-identity.html", context)


@login_required
@is_doctor
@page_template('partial/points-history-list.html')
def pointsHistory(request, template="doctor/points-history.html", extra_context=None):
    title = _("Historique des points")

    postes = request.user.medecin.postes.all()

    context = {
        "title": title,
    }

    phs = PointsHistory.objects.filter(Q(poste__in=postes) | Q(medecin__user=request.user)).order_by("-id")
    context.update({"pointsHist": phs})
    # mark all notification where actor == poste as read
    for poste in postes:
        qs = request.user.notifications.unread().filter(Q(actor_content_type=ContentType.objects.get_for_model(poste)
                                                          , actor_object_id=poste.id) |
                                                        Q(actor_content_type=ContentType.objects.get_for_model(
                                                            request.user.medecin)
                                                            , actor_object_id=request.user.medecin.id))
        qs.mark_all_as_read()

    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context, using=request.template_version)


def professionalCardUpload(request):
    if request.is_ajax():
        form = ProfessionalCardUploadForm(request.POST, request.FILES)
        if form.is_valid():
            cp = form.save()
            return JsonResponse({'file_id': cp.pk, "file_url": cp.image.url}, status=200)
        else:
            return JsonResponse({'error': form.errors}, status=500)


@login_required
def professionalCardRejected(request):
    if not request.user.groups.filter(name=Role.DOCTOR.value).exists():
        raise Http404
    if request.user.medecin.rejected == False:
        return redirect("doctor-dashboard")

    if request.method == 'POST':
        form = ProfessionalCardUploadForm(request.POST, request.FILES)
        if form.is_valid():
            cp = form.save()
            medecin = request.user.medecin
            carte = medecin.carte
            if carte:
                carte.delete()
            medecin.carte = cp
            medecin.save()
            return redirect("doctor-account-validation")
    else:
        form = ProfessionalCardUploadForm()

    context = {
        'form': form
    }
    return render(request, "doctor/card_rejected.html", context)


class BusyView(SuccessMessageMixin, AjaxUpdateView):
    form_class = BusyForm
    model = Tdemand

    @method_decorator(login_required)
    @method_decorator(is_doctor)
    def dispatch(self, request, *args, **kwargs):
        # send rejected notification
        self.medecin = request.user.medecin
        cmd = WebsocketCommand.TELECONSULTATION_DEMAND_REJECTED.value
        channel_layer = get_channel_layer()
        room_group_name = 'chat_%s' % self.get_object().patient.user.pk

        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'notification_message',
                'data': {
                    'command': cmd,
                    'code': "BUSY",
                }
            }
        )
        # update demand
        Tdemand.objects.filter(pk=self.get_object().pk).update(annulee=True)

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        demand = form.save(commit=False)
        # setting doctor to busy stat
        Presence.objects.setBusy(self.medecin.user, True, form.getChosenTime())

        demand.annulee = True
        demand.save()
        return super(BusyView, self).form_valid(form)


@login_required
@is_doctor
def CertifUpload(request):
    if request.method == 'POST':
        try:
            form = CertifUploadForm(request.POST, request.FILES, user=request.user)
            if form.is_valid():
                cp = form.save()
                t = request.POST.get("t", None)
                if t == "1":
                    request.user.medecin.contact.specialite_certificat = cp
                    request.user.medecin.contact.save()
                elif t == "2":
                    request.user.medecin.contact.qualifications_certificats.add(cp)
                elif t == "3":
                    request.user.medecin.contact.agrement = cp
                    request.user.medecin.contact.save()
                return JsonResponse({'file_id': cp.pk, "file_url": cp.file.url, "filename": cp.filename}, status=200)
            else:
                return JsonResponse({'error': form.errors}, status=400)
        except Exception as e:
            print(e)


class AnnonceFeedBackView(SuccessMessageMixin, AjaxCreateView):
    form_class = AnnonceFeedBackForm
    model = AnnonceFeedBack

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        annonce_id = request.GET.get('annonce_id', None)
        try:
            hash_fn = basehash.base52(32)
            annonce_id = hash_fn.unhash(annonce_id)
            self.annonce = Annonce.objects.get(id=annonce_id)
        except:
            self.annonce = None

        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        afb = form.save(commit=False)
        if self.annonce:
            afb.user = self.user
            afb.annonce = self.annonce
            afb.save()
        return super(AnnonceFeedBackView, self).form_valid(form)


@login_required
@is_doctor
def offers(request):
    context = {}
    offers_active = [o for o in OffrePrepaye.objects.order_by("prix") if o.status == OfferStatus.ACTIVE]
    context['offers_active'] = offers_active
    return render(request, "doctor/offers.html", context, using=request.template_version)


@login_required
@is_doctor
def detailOffer(request, pk):
    offre = get_object_or_404(OffrePrepaye, pk=pk)
    return HttpResponse(linebreaks(offre.description))


@login_required
@is_doctor
def subscribe(request, offer_id, slug):
    articles = []
    services_fedelite = []
    context = {}
    offre = get_object_or_404(OffrePrepaye, id=offer_id, slug=slug)
    # if the offer has a price equal to zero
    if offre.prix == 0:
        # Check if the use has subscribed to the offer before
        if offre in request.user.medecin.current_offers:
            messages.error(request, _("Désolé, vous êtes déjà abonné à cette offre."))
            # return to previous page
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        else:
            # else create the command directly
            command = createCommand(offre, request.user.medecin)
            return redirect(reverse('detail-order', kwargs={'pk': command.id, }))

    context.update({"contact": request.user.medecin.contact})
    context.update({"offre": offre})
    total_ht = offre.prix
    total_hr_reduction = total_ht

    if offre.has_reduction(request.user):
        reduction = offre.prix - offre.prix_reduit
        context.update({"reduction": reduction})
        total_hr_reduction = total_ht - reduction
        context.update({"total_reduction": total_hr_reduction})
    articles.append({
        "article": offre.libelle,
        "prix": offre.prix,
        'quantite': 1,
        "total": offre.prix
    })
    for sf in offre.avantages.all():
        services_fedelite.append({
            "libelle": sf.libelle,
        })

    title = _("Bon de Commande")
    numero = get_nextautoincrement(Facture)

    # calculate tva
    tva = "%.2f" % (total_hr_reduction * settings.TVA / 100)
    # calculate total
    total = "%.2f" % (total_hr_reduction + (total_hr_reduction * settings.TVA / 100))

    context.update({"date": timezone.now().strftime("%m/%d/%Y")})
    context.update({"tva": tva})
    context.update({"tva_text": "TVA {}%".format(settings.TVA)})
    context.update({"currency": "DA"})
    context.update({"items": articles})
    context.update({"loyalty_services": services_fedelite})
    context.update({"total_ht": total_ht})
    context.update({"total": total})
    context.update({"total2words": num2words(total, lang='fr') + " Dinars"})
    context.update({"invoice_title": title})
    context.update({"invoice_number": numero})
    return render(request, "doctor/subscribe-offer.html", context, using=request.template_version)


@login_required
@is_doctor
def orderOffer(request, offer_id, coupon_id=None):
    offer = get_object_or_404(OffrePrepaye, id=offer_id)
    if coupon_id:
        coupon = get_object_or_404(Coupon, id=coupon_id)
        if not coupon.is_redeemed and not coupon.expired():
            return redirect(
                reverse('epayment-method',
                        args=[user_id_hash(request.user), offer_id_hash(offer), coupon_id_hash(coupon)]),
            )
        else:
            messages.error(request, _("Le coupon utilisé n'est plus valide!"))
            # return to previous page
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    else:
        return redirect(
            reverse('epayment-method', args=[user_id_hash(request.user), offer_id_hash(offer)]),
        )


class OfferSponsorisedOrderView(SuccessMessageMixin, AjaxCreateView):
    form_class = OfferSponsorisedOrderForm

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        self.request = request
        return super().dispatch(request, *args, **kwargs)

    def get_response_message(self):
        link = reverse('detail-order',
                       kwargs={
                           'pk': self.facture.id,
                       })
        return link

    def form_valid(self, form):
        self.facture = form.save(user=self.user)
        messages.success(self.request,
                         _("Coupon valide! une offre de type %s est attribué à votre compte.") % self.facture.offre_prepa)
        return self.render_json_response(self.get_success_result())


@login_required
@is_doctor
def treatCareTeamRequest(request):
    if request.is_ajax():
        id = request.POST.get('id', None)
        accepte = request.POST.get('accepte', None)
        accepte = True if accepte == "1" else False
        esoins = get_object_or_404(EquipeSoins, id=id, professionnel=request.user)
        if accepte:
            esoins.confirme = True
            esoins.date_confirmation = timezone.now()
            esoins.save()
            tasks.notify(esoins, recipients=[esoins.patient.user],
                         verb=NotificationVerb.DEMAND_ADD_TO_CARE_TEAM_ACCEPTED.value)
        else:
            EquipeSoins.objects.filter(id=id).delete()
        return JsonResponse({"patient": esoins.patient.full_name, "accepte": accepte}, status=200)
    return JsonResponse({}, status=400)


class DemoRequestView(SuccessMessageMixin, AjaxUpdateView):
    form_class = DemoRequestForm
    model = Contact
    success_message = _("Demande envoyé")

    @method_decorator(login_required)
    @method_decorator(is_doctor)
    def dispatch(self, request, *args, **kwargs):
        self.medecin = request.user.medecin
        if has_license(request.user):
            return self.render_json_response({'status': 'error', 'message': _("503 Service Indisponible")})
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        contact = form.save(commit=False)
        commentaire = form.cleaned_data['commentaire']
        self.medecin.user.first_name = contact.nom
        self.medecin.user.last_name = contact.prenom
        self.medecin.user.save()

        message = "Demande de rendez de test en ligne envoyée par: %s, nom d'utilisateur: %s, pourquoi?: %s" % (
            self.medecin.user.get_full_name(),
            self.medecin.user.username,
            commentaire
        )
        mail.send(
            "contact@ibnhamza.com",
            settings.DEFAULT_FROM_EMAIL,
            subject="Demande de rendez de test en ligne",
            message=message,
            html_message=message,
            priority='medium'
        )

        return super(DemoRequestView, self).form_valid(form)

@login_required
@is_doctor
def profile_update(request):
    if request.is_ajax():
        if 'nom' in request.POST:  # form_p1
            form = FirstLoginForm(request.POST, contact=request.user.medecin.contact)
        elif 'specialite' in request.POST:  # form_p2
            form = FirstLoginP1Form(request.POST, contact=request.user.medecin.contact)
        elif 'mobile' in request.POST:  # form_p3
            form = FirstLoginP2Form(request.POST, contact=request.user.medecin.contact)

        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            ctx = {}
            ctx.update(csrf(request))
            form_html = render_crispy_form(form, context=ctx)
            return JsonResponse({'success': False, 'form_html': form_html})

