import random
import random
import re

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db.models import Q
from django.shortcuts import render
from django.utils import translation
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from el_pagination import utils
from el_pagination.decorators import page_template

from clinique.models import CliniqueVirtuelle
from core.forms.directory_forms import ContactGoogleSpecialiteAutocompleteForm, CityGoogleEmplacementAutocompleteForm
from core.models import Contact
from crm.models import Ville
from directory.utils import IGNOORED_DOCTOR_NAME_LIST


@xframe_options_exempt
@csrf_exempt
@page_template('index-directory-detail.html')
def directory_index(request, template="index-directory.html", extra_context=None):
    #set current language to arabic explicitly
    user_language = 'ar'
    translation.activate(user_language)
    request.session[translation.LANGUAGE_SESSION_KEY] = user_language

    q_q = None
    specialite_q_id = None
    city_q_id = None

    cvs = CliniqueVirtuelle.objects.filter().exclude(
        Q(titre__exact='') | Q(titre__isnull=True) | Q(image__isnull=True)
    ).exclude(Q(titre__istartswith="Clinique du DR") & Q(image__default=True))

    contacts = Contact.objects.filter(
        (
                Q(medecin__isnull=False) &
                ~Q(medecin__user__first_name__isnull=True, medecin__user__last_name__isnull=True) &
                ~Q(medecin__user__first_name__exact='', medecin__user__last_name__exact='') &
                ~Q(medecin__user__first_name__iregex=r'(' + '|'.join(
                    [re.escape(n) for n in IGNOORED_DOCTOR_NAME_LIST]) + ')') &
                ~Q(medecin__user__last_name__iregex=r'(' + '|'.join(
                    [re.escape(n) for n in IGNOORED_DOCTOR_NAME_LIST]) + ')') &
                ~Q(compte_test=True)
        ) | Q(source="16")
    ).distinct()

    if request.is_ajax():
        if request.method == 'POST':
            q_q = request.POST.get('first_last_name', None)
            city_q_id = request.POST.get('position', None)
            specialite_q_id = request.POST.get('specialite', None)
        if request.method == 'GET':
            q_q = request.GET.get('first_last_name', None)
            city_q_id = request.GET.get('position', None)
            specialite_q_id = request.GET.get('specialite', None)

    if city_q_id:
        cvs = cvs.filter(Q(ville__ville__id=city_q_id) | Q(user__medecin__contact__ville__ville__id=city_q_id))
    if specialite_q_id:
        cvs = cvs.filter(user__medecin__contact__specialite__id=specialite_q_id)
        contacts = contacts.filter(specialite__id=specialite_q_id)
    if q_q:
        cvs = cvs.filter(
            Q(titre__icontains=q_q) | Q(user__first_name__istartswith=q_q) |
            Q(user__last_name__istartswith=q_q) | Q(user__medecin__contact__specialite__libelle__icontains=q_q)
        )
        contacts = contacts.filter(
            Q(medecin__user__first_name__istartswith=q_q) | Q(medecin__user__last_name__istartswith=q_q) |
            Q(nom__icontains=q_q) | Q(prenom__icontains=q_q) |
            Q(specialite__libelle__icontains=q_q)
        )

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
        'form_specialite': ContactGoogleSpecialiteAutocompleteForm(),
        'form_position': CityGoogleEmplacementAutocompleteForm(),
        'extra_args': "&first_last_name=%s&specialite=%s&position=%s" % (
            q_q or "", specialite_q_id or "", city_q_id or "")
    }

    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context, using="v2")
