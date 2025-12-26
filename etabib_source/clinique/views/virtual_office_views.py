import random
import re

from cities_light.models import Country, City
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from el_pagination import utils
from el_pagination.decorators import page_template
from fm.views import AjaxCreateView

from appointements.models import DemandeRendezVous, LettreOrientation
from clinique.forms import CliniqueVirtuelleImageForm, LocationForm, RendezVousCreateForm
from clinique.models import CliniqueVirtuelleImage, CliniqueVirtuelle
from core.decorators import is_doctor, v2_only, has_access
from core.enums import EtabibService
from core.models import Contact, Medecin, CarteID, Patient
from core.utils import checkJitsiRoomExists, generateJwtToken
from crm.models import Ville
from directory.utils import IGNOORED_DOCTOR_NAME_LIST
from etabibWebsite.settings import ECONGRE_JITSI_DOMAIN_NAME
from django.utils import timezone


@login_required
def upload_vcimage(request):
    if request.method == 'POST':
        form = CliniqueVirtuelleImageForm(request.POST, request.FILES)
        if form.is_valid():
            cvimg = form.save(commit=False)
            cvimg.user = request.user
            cvimg.save()
            return JsonResponse({"image_url": cvimg.image.url, "image_id": cvimg.id}, status=200)
        else:
            print(form.errors)
            return JsonResponse({'error': form.errors}, status=400)
    return JsonResponse({}, status=400)


@login_required
@v2_only
def remove_vcimage(request):
    if request.is_ajax():
        vimg_id = request.POST.get("id", None)
        vimg = get_object_or_404(CliniqueVirtuelleImage, id=vimg_id)
        if vimg.default or vimg.user != request.user:
            return JsonResponse({}, status=403)
        elif not vimg.default and vimg.user == request.user:
            vimg.delete()
            return JsonResponse({}, status=200)
    return JsonResponse({}, status=400)


@login_required
@is_doctor
@v2_only
@has_access(EtabibService.VIRTUAL_CLINIC)
def virtual_office(request):
    vimages = CliniqueVirtuelleImage.objects.filter(Q(user=request.user) | Q(default=True))
    obj, created = CliniqueVirtuelle.objects.update_or_create(
        user=request.user
    )
    context = {
        "clinique": obj,
        "vimages": vimages,
        "locationForm": LocationForm()
    }
    return render(request, "doctor/virtual-office.html", context=context, using=request.template_version)


@login_required
@is_doctor
@v2_only
@has_access(EtabibService.VIRTUAL_CLINIC)
def virtual_office_update(request):
    if request.is_ajax():
        vimg_id = request.POST.get("id", None)
        name = request.POST.get("name", None)
        value = request.POST.get("value", None)
        obj, created = CliniqueVirtuelle.objects.update_or_create(
            user=request.user
        )

        out = {}

        if vimg_id:
            vimg = get_object_or_404(CliniqueVirtuelleImage, id=vimg_id)
            obj.image = vimg
        elif name == "titre":
            obj.titre = value
        elif name == "description":
            obj.description = value
        elif name == "video":
            obj.video = value
            out = {
                "video_html": render_to_string(
                    "video.html",
                    context={"video": obj.video},
                    using=request.template_version) if obj.video else ""
            }
        elif name == "pays":
            obj.pays = Country.objects.get(id=value)
        elif name == "ville":
            obj.ville = City.objects.get(id=value)
        elif name == "facebook":
            obj.facebook = value
        elif name == "instagram":
            obj.instagram = value
        elif name == "pageweb":
            obj.pageweb = value
        elif name == "fixe":
            obj.fixe = value
        elif name == "mobile":
            obj.mobile = value
        elif name == "prestations":
            obj.prestations = value
        obj.save()
        return JsonResponse(out, status=200)
    return JsonResponse({}, status=400)


@login_required
@v2_only
@page_template('partial/virtual_offices_partial.html')
def virtual_offices_list(request, template="virtual_offices.html", extra_context=None):
    if request.method == "POST":
        q_q = request.POST.get("q_q", "")
        specialite_q_id = request.POST.get("specialite_q", "")
        city_q_id = request.POST.get("city_q", "")
    elif request.method == "GET":
        q_q = request.GET.get("q_q", "")
        specialite_q_id = request.GET.get("specialite_q", "")
        city_q_id = request.GET.get("city_q", "")

    cvs = CliniqueVirtuelle.objects.filter().exclude(
        Q(titre__exact='') | Q(titre__isnull=True) | Q(image__isnull=True)
    ).exclude(Q(titre__istartswith="Clinique du DR") & Q(image__default=True))
    if city_q_id:
        cvs = cvs.filter(Q(ville__ville__id=city_q_id) | Q(user__medecin__contact__ville__ville__id=city_q_id))
    if specialite_q_id:
        cvs = cvs.filter(user__medecin__contact__specialite__id=specialite_q_id)
    if q_q:
        cvs = cvs.filter(
            Q(titre__icontains=q_q) | Q(user__first_name__istartswith=q_q) |
            Q(user__last_name__istartswith=q_q) | Q(user__medecin__contact__specialite__libelle__icontains=q_q)
        )

    contacts = Contact.objects.filter(
        (
          Q(medecin__isnull=False) &
         ~Q(medecin__user__first_name__isnull=True, medecin__user__last_name__isnull=True) &
         ~Q(medecin__user__first_name__exact='', medecin__user__last_name__exact='') &
         ~Q(medecin__user__first_name__iregex=r'(' + '|'.join([re.escape(n) for n in IGNOORED_DOCTOR_NAME_LIST]) + ')') &
         ~Q(medecin__user__last_name__iregex=r'(' + '|'.join([re.escape(n) for n in IGNOORED_DOCTOR_NAME_LIST]) + ')') &
         ~Q(compte_test=True)
        ) | Q(source="16")
    ).distinct()

    if q_q:
        contacts = contacts.filter(
            Q(medecin__user__first_name__istartswith=q_q) | Q(medecin__user__last_name__istartswith=q_q) |
            Q(nom__icontains=q_q) | Q(prenom__icontains=q_q) |
            Q(specialite__libelle__icontains=q_q)
        )
    if specialite_q_id:
        contacts = contacts.filter(specialite__id=specialite_q_id)
    if city_q_id:
        ville = Ville.objects.filter(id=city_q_id).first()
        if ville:
            degrees = 15 / 111.325
            ref_location = Point(float(ville.latitude), float(ville.longitude), srid=4326)
            contacts = contacts.filter(
                geo_coords__distance_lte=(ref_location, degrees)
            ).annotate(
                distance=Distance("geo_coords", ref_location)
            ).order_by('distance')

    else:
        page = utils.get_page_number_from_request(request)
        try:
            # Note: the below code works just in MySql Database
            # randomize the the order of contacts
            if not request.session.get('random_seed', False) or page == 1:
                request.session['random_seed'] = random.randint(1, 10000)
            seed = request.session['random_seed']
            contacts = contacts.extra(select={'identifier': 'RAND(%s)' % seed}).order_by('identifier')
        except Exception:
            pass

    context = {
        "cliniquevirtuelles": cvs.order_by("id"),
        "contacts": contacts,
        "q_q": q_q,
        'extra_args': f"&q={q_q or ''}&specialite_q={specialite_q_id or ''}&city={city_q_id or ''}",
    }
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context, using=request.template_version)


@login_required
@v2_only
def virtual_office_detail(request, voffice_id=None):
    context = {}
    clinique = get_object_or_404(CliniqueVirtuelle, pk=voffice_id)
    if checkJitsiRoomExists(clinique.salle_discussion):
        context["clinique_status"] = 'online'
    else:
        context["clinique_status"] = 'offline'

    context["clinique"] = clinique
    context["sub_title"] = _('مكتب الإستقبال الإفتراضي')
    return render(request, "virtual_office_detail.html", context, using=request.template_version)


@login_required
@v2_only
def virtual_office_doctor_profile(request, contact_id):
    context = {}
    contact = get_object_or_404(Contact, pk=contact_id)

    if hasattr(contact, "medecin"):
        cliniques = CliniqueVirtuelle.objects.filter(user=contact.medecin.user)
        if cliniques.exists():
            context["clinique"] = cliniques.first()
    context["contact"] = contact
    context["form_rdv"] = RendezVousCreateForm()
    context["sub_title"] = _('أطباء و مهنيي العيادة')
    return render(request, "doctor_profile.html", context, using=request.template_version)


@login_required
@v2_only
def virtual_office_tarif(request, voffice_id=None):
    context = {}
    clinique = get_object_or_404(CliniqueVirtuelle, pk=voffice_id)
    context["clinique"] = clinique
    context["sub_title"] = _('الخدمات والتسعيرات')
    return render(request, "virtual_office_tarif.html", context, using=request.template_version)


@login_required
@is_doctor
@v2_only
@has_access(EtabibService.VIRTUAL_CLINIC)
def virtual_secretary(request, clinique_id=None):
    # Praticien
    context = {}
    clinique = get_object_or_404(CliniqueVirtuelle, pk=clinique_id)
    if clinique.user == request.user:
        # generate jwt token
        jwtToken = generateJwtToken(request.user)
        if jwtToken:
            context['jwtToken'] = jwtToken
    context.update({
        "clinique": clinique,
        "sidebar_clinique_virt": True
    })
    return render(request, "doctor/virtual-secretary.html", context=context, using=request.template_version)


@login_required
def v_secretary_visio(request):
    # Patient
    if request.is_ajax():
        clinique_id = request.POST.get('clinique_id', None)
        clinique = get_object_or_404(CliniqueVirtuelle, pk=clinique_id)
        if checkJitsiRoomExists(clinique.salle_discussion):
            url = "https://%s/%s#%s" % (
                ECONGRE_JITSI_DOMAIN_NAME,
                clinique.salle_discussion,
                f'userInfo.displayName="{request.user.patient.full_name}"'
            )
            return JsonResponse({'url': url}, status=200)
        else:
            return JsonResponse({'error': "Forbidden"}, status=400)


@login_required
def v_secretary_status(request):
    if request.is_ajax():
        clinique_id = request.POST.get('clinique_id', None)
        clinique = get_object_or_404(CliniqueVirtuelle, pk=clinique_id)
        if checkJitsiRoomExists(clinique.salle_discussion):
            return JsonResponse({}, status=200)
        else:
            return JsonResponse({'error': "Not found"}, status=204)
    return JsonResponse({}, status=400)


class RendezVousCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = RendezVousCreateForm
    model = DemandeRendezVous
    success_message = "Demande de Rendez-vous envoyée au Médecin avec succès!"

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.patient = request.user.patient
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            demande = form.save(commit=False)

            patient = Patient.objects.get(pk=self.patient.pk)

            # Get Medecin Id from the URL
            medecin_id = self.request.path.rsplit('/', 1)[-1]
            medecin = get_object_or_404(Medecin, pk=medecin_id)

            demande.destinataire = medecin.user
            demande.demandeur = patient.user
            demande.date_traitement = timezone.now()
            demande.skip_signal = True  # to skip signal from triggering
            demande.save()

            for file in self.request.FILES:
                ltr = LettreOrientation()
                ltr.lettre = self.request.FILES[file]
                ltr.demande = demande
                ltr.save()
                print(ltr.lettre)

        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(self.get_success_result())