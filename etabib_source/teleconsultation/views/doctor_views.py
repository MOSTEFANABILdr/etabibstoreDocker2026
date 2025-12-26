import re
from datetime import datetime

from PIL import Image
from allauth.account.models import EmailAddress
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from datatableview import Datatable, columns
from datatableview.views import DatatableView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib.messages.views import SuccessMessageMixin
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.db.models import Q, Case, When, Value, BooleanField
from django.http import HttpResponseRedirect, JsonResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from djmoney.money import Money
from el_pagination.decorators import page_template
from fm.views import AjaxUpdateView, AjaxCreateView
from fm.views import AjaxUpdateView
from post_office import mail
from django.utils.text import slugify

from core.decorators import is_doctor, has_access, v2_only
from core.enums import WebsocketCommand, EtabibService, Role
from core.mixins import TemplateVersionMixin
from core.models import Patient, EquipeSoins, Medecin, CarteID
from core.utils import generateJwtToken, hasEnoughMoney, generate_username
from etabibWebsite import settings
from teleconsultation.forms import ClaimUpdateForm, SearchPatientForm, AddPatientForm, \
    PatientSearchForm, CarteIDForm
from teleconsultation.models import Tdemand, Treclamation
from teleconsultation.templatetags.teleconsultation_tags import has_discount, apply_discount


@login_required
def teleconsultation(request, unique_id):
    context = {
        'title': _("Téléconsultation")
    }
    demand = get_object_or_404(Tdemand, unique_id=unique_id)
    context['demand'] = demand

    if not demand.is_free:
        # check if patient has enough money to do a teleconsultation
        context['patient_has_enough_money'] = hasEnoughMoney(demand.patient, demand.medecin)

    if demand.annulee:
        messages.warning(request, _("La demande de téléconsultation a été annulée"))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    if not demand.salle_discussion:
        demand.acceptee = True
        demand.createRoom()
        demand.save()

    # generate medecin jwt token
    jwtToken = generateJwtToken(request.user)
    if jwtToken:
        context['jwtToken'] = jwtToken

    channel_layer = get_channel_layer()

    if hasattr(request.user, 'medecin'):
        url = request.build_absolute_uri(
            reverse("patient-teleconsultation", args=[demand.unique_id])
        )
        # if settings.ENVIRONMENT != settings.Environment.DEV:
        #     url = url.replace("http://", "https://")
        print(f"DEBUG: Generated URL for patient: {url}")
        print(f"DEBUG: Environment: {settings.ENVIRONMENT}")
        if demand.from_patient:
            room_group_name = 'chat_%s' % demand.patient.user.pk
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'notification_message',
                    'data': {
                        'command': WebsocketCommand.TELECONSULTATION_DEMAND_ACCEPTED.value,
                        'url': url,
                        'doctor': demand.caller_name(request.user),
                        'room': demand.salle_discussion,
                    }
                }
            )
    else:
        url = request.build_absolute_uri(
            reverse("doctor-teleconsultation", args=[demand.unique_id])
        )
        # if settings.ENVIRONMENT != settings.Environment.DEV:
        #     url = url.replace("http://", "https://")
        if not demand.from_patient:
            room_group_name = 'chat_%s' % demand.medecin.user.pk
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'notification_message',
                    'data': {
                        'command': WebsocketCommand.TELECONSULTATION_DEMAND_ACCEPTED.value,
                        'url': url,
                        'doctor': demand.caller_name(request.user),
                        'room': demand.salle_discussion,
                    }
                }
            )

    return render(request, "patient/meeting.html", context)


class TeleconsultationJournalDatatable(Datatable):
    actions = columns.TextColumn(_("Actions"), source=None, processor='get_entry_action')
    patient_nom = columns.TextColumn(source=['patient__user__first_name'])
    patient_prenom = columns.TextColumn(source=['patient__user__last_name'])
    facturee = columns.TextColumn(_("Facturée"), source=None, processor='get_facturee_entry')
    status = columns.TextColumn(_("Etat"), source=None, processor='get_status_entry')
    date_demande = columns.TextColumn(_("Date"), source=None, processor='get_entry_date_demande')

    class Meta:
        columns = ["patient", "date_demande", "status", "facturee", "actions"]
        hidden_columns = ["patient_nom", "patient_prenom"]
        search_fields = ['patient__user__first_name', "patient__user__last_name"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 10

    def get_entry_date_demande(self, instance, **kwargs):
        if instance.date_demande:
            return instance.date_demande.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_status_entry(self, instance, **kwargs):
        if instance.acceptee:
            text = _("Acceptée")
            css_class = "success"
            return mark_safe('<span class="badge badge-%s">%s</span>' % (css_class, text))
        elif instance.annulee:
            text = _("Annulée")
            css_class = "danger"
            return mark_safe('<span class="badge badge-%s">%s</span>' % (css_class, text))
        else:
            return ""

    def get_facturee_entry(self, instance, **kwargs):
        out = "<ul class='list-unstyled'><li></li>{}<li>{}</li></ul>"
        if instance.facturee:
            text = _("OUI")
            tarif = instance.tarif - instance.gain
        else:
            text = _("NON")
            tarif = ""
        return out.format(text, tarif)

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-telec-dmnd-actions.html",
                                {'demand': instance, "user": self.view.request.user})


class TeleconsultationJournalDatatableView(DatatableView, TemplateVersionMixin):
    template_name = "doctor/teleconsultation_journal.html"
    model = Tdemand
    datatable_class = TeleconsultationJournalDatatable

    @method_decorator(login_required)
    @method_decorator(is_doctor)
    @method_decorator(has_access(EtabibService.ETABIB_CARE))
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(TeleconsultationJournalDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Journal")
        context['sidebar_journal'] = True
        return context

    def get_queryset(self):
        if self.user:
            return Tdemand.objects.filter(medecin__user=self.user)
        return Tdemand.objects.all()


@login_required
@is_doctor
def billTeleconsultation(request):
    """
    :param request:
    :return:
    """
    if request.is_ajax():
        room = request.POST.get('room', None)
        try:
            demand = Tdemand.objects.get(salle_discussion=room)
        except Tdemand.DoesNotExist:
            return JsonResponse({'error': "target data does not exist"}, status=404)
        if request.user.medecin == demand.medecin and demand.facturee is False:
            try:
                with transaction.atomic():
                    if not demand.is_free:
                        demand.facturee = True
                        # check if patient has a discount
                        tarif_normal = demand.medecin.tarif_consultation
                        hasDiscount, coupon = has_discount(demand.patient).values()
                        if hasDiscount:
                            tarif_reduit = apply_discount(demand.medecin.tarif_consultation, coupon)
                            demand.patient.solde = demand.patient.solde - tarif_reduit
                            demand.coupon = coupon
                        else:
                            demand.patient.solde = demand.patient.solde - tarif_normal
                        demand.patient.save()

                        demand.medecin.solde = demand.medecin.solde + tarif_normal - Money(
                            settings.ETABIB_ECONSULTATION_AMOUNT,
                            settings.ETABIB_ECONSULTATION_CURRENCY)
                        demand.medecin.save()

                        demand.tarif = tarif_normal
                        demand.gain = Money(settings.ETABIB_ECONSULTATION_AMOUNT,
                                            settings.ETABIB_ECONSULTATION_CURRENCY)
                        demand.save()
            except:
                import traceback
                print(traceback.format_exc())
                return JsonResponse({'error': "server error"}, status=500)

            context = {}
            return JsonResponse(context, status=200)
        else:
            return JsonResponse({'error': "not authorized"}, status=403)
    else:
        return JsonResponse({'error': "no content"}, status=405)


class ClaimَUpdateView(AjaxUpdateView):
    form_class = ClaimUpdateForm
    model = Treclamation

    @method_decorator(login_required)
    @method_decorator(is_doctor)
    def dispatch(self, request, *args, **kwargs):
        self.tdemand_pk = kwargs['tdemand_pk'] if 'tdemand_pk' in kwargs else None
        if self.tdemand_pk:
            try:
                self.tdemand = Tdemand.objects.get(pk=self.tdemand_pk)
            except Tdemand.DoesNotExist:
                raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(ClaimَUpdateView, self).get_form_kwargs()
        kwargs.update({"reponse_read_only": False})
        return kwargs

    def form_valid(self, form):
        return super(ClaimَUpdateView, self).form_valid(form)


@login_required
def teleconsultationSessions(request, demand_pk):
    demand = get_object_or_404(Tdemand, pk=demand_pk)
    context = {
        'demand': demand
    }
    return render(request, "doctor/teleconsultation_sessions.html", context)


@login_required
@page_template('contact_tiles_list.html')
@has_access(EtabibService.ETABIB_CARE)
def contacts(request, template="contact_template.html", extra_context=None):
    qs = Patient.objects.filter(
        Q(tdemand__medecin__user=request.user, tdemand__isnull=False) |
        Q(cree_par=request.user) |
        Q(equipe_soins__professionnel=request.user, equipe_soins__confirme=True)
    ).distinct()
    patient_id = request.POST.get("patient_id", None)
    if patient_id:
        qs = qs.filter(pk=patient_id)
    param_query = None
    param_gender = None
    if request.method == 'POST':
        form = SearchPatientForm(request.POST)
        if form.is_valid():
            param_query = form.cleaned_data['query']
            param_gender = form.cleaned_data['gender']
    else:
        form = SearchPatientForm()
        param_query = request.GET.get('query', None)
        param_gender = request.GET.get('gender', None)

    # apply filter
    if param_gender:
        if param_gender == "1":  # HOMME
            qs = qs.filter(sexe=Patient.GENDER_CHOICES[0][0])
        elif param_gender == "0":  # FEMME
            qs = qs.filter(sexe=Patient.GENDER_CHOICES[1][0])
        elif param_gender == "2":  # TOUT
            qs = qs
    if param_query:
        qs = qs.filter(Q(user__first_name__istartswith=param_query) | Q(user__last_name__istartswith=param_query))

    # Add an extra field "is_online" to the queryset to check if the patient is online or not
    qs = qs.annotate(
        is_online=Case(
            When(
                user__presence__isnull=True,
                then=Value(False)
            ), default=Value(True), output_field=BooleanField()
        )
    ).order_by("-is_online")
    context = {'sidebar_contact': True, 'title': _("Contacts"), 'patients': qs, 'form': form,
               'extra_args': "&query=%s&gender=%s" % (
                   param_query if param_query else "", param_gender if param_gender else ""),
               'AddPatientForm': AddPatientForm(), 'formpatient': PatientSearchForm()}

    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context, using=request.template_version)


@login_required
@has_access(EtabibService.ETABIB_CARE)
def save_patient_form(request, form, template_name, using=None):
    data = dict()
    if request.method == 'POST':
        if form.is_valid():
            result = form.save()
            patient = result['patient']
            patient.cree_par = request.user
            patient.save()
            mail.send(
                patient.user.email,
                settings.DEFAULT_FROM_EMAIL,
                template='registration',
                context={
                    'username': patient.user.email,
                    'password': result['password'],
                    'login_link': "{}://{}".format(request.scheme, request.get_host())
                },
            )
            data['form_is_valid'] = True
            data['patient_id'] = patient.pk
            data['pwd'] = result['password']
        else:
            data['form_is_valid'] = False
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


@login_required
@has_access(EtabibService.ETABIB_CARE)
def patient_create(request):
    if request.method == 'POST':
        form = AddPatientForm(request.POST)
    else:
        form = AddPatientForm()
    return save_patient_form(request, form, 'includes/partial_patient_create.html')


@v2_only
@login_required
def patient_create_qr(request, pk):
    context = {}
    patient = get_object_or_404(Patient, pk=pk)
    if patient:
        context['patient'] = patient
    return render(request, "includes/partial_patient_qr.html", context, using=request.template_version)


def preprocess_and_save(url_face, url_back):
    # open
    image_face = Image.open(url_face)
    image_back = Image.open(url_back)

    # preprocess
    image_face = image_face.convert('L')
    image_back = image_back.convert('L')

    # save
    image_face.save(url_face)
    image_back.save(url_back)
    return image_face, image_back


def text_processing_back(text_array):
    patient_dict = {}
    # Nom<<Prenom1<Prenom2<..
    line_nom = str(text_array[-1])
    line_nom = line_nom.replace('<', ' ').strip()
    line_nom = line_nom.replace('<', ' ')
    line_nom = re.sub(' +', ' ', line_nom)
    line_nom = line_nom.split(' ')

    if len(line_nom) == 2:
        patient_dict['nom'] = line_nom[0].replace('<', '')
        patient_dict['prenom'] = line_nom[1].replace('<', '')
    else:
        patient_dict['nom'] = line_nom[0].replace('<', ' ').strip()
    # Sexe homme:M femme:F
    try:
        patient_dict['sexe'] = '1'
        line_sexe = str(text_array[-2])
        if line_sexe == 'M':
            patient_dict['sexe'] = '1'
        elif line_sexe == 'F':
            patient_dict['sexe'] = '2'
    except IndexError as ie:
        print(f"Sexe error {ie}, {type(ie)}")

    # DateNaissance YYMMDD
    try:
        line_dn = str(text_array[-2])[0:6]
        year = int(line_dn[0:2])
        if 22 < year <= 99:
            year = '19'
        else:
            year = '20'
        patient_dict['date_naissance'] = f"{year}{line_dn[0:2]}-{line_dn[2:4]}-{line_dn[4:]}"
    except IndexError:
        patient_dict['date_naissance'] = None

    # Num Carte ID
    try:
        patient_dict['num_carte_id'] = str(text_array[-3])[5:14]
    except IndexError:
        patient_dict['num_carte_id'] = ''

    return patient_dict


def text_processing_face(text_array):
    patient_dict = {}
    # num id
    # patient_numid = look_for_format(text_array, size=9)
    # patient_dict['num_id'] = patient_numid

    # nat id
    patient_natid = look_for_format(text_array, size=18)
    patient_dict['nin'] = patient_natid

    return patient_dict


def look_for_format(text_array, size=0):
    for text in text_array:
        tmp = str(text).strip().replace('.', '').replace(':', '')
        if len(tmp) == size and tmp.isnumeric():
            return tmp
    return ''


@login_required
@is_doctor
@csrf_protect
def create_carte_id(request):
    if request.method == 'POST':
        if request.is_ajax():
            upload_filef = request.FILES['croppedImage']
            upload_fileb = request.FILES['croppedImage1']

            fs = FileSystemStorage()
            urlf = fs.save(upload_filef.name, upload_filef)
            urlb = fs.save(upload_fileb.name, upload_fileb)
            preprocess_and_save(fs.path(urlf), fs.path(urlb))

            # run OCR
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False)
            paddle_result = ocr.ocr(fs.path(urlb), cls=True)
            ocr_text_back = []
            for result in paddle_result:
                ocr_text_back.append(result[1][0])
            paddle_result = ocr.ocr(fs.path(urlf), cls=True)
            ocr_text_face = []
            for result in paddle_result:
                ocr_text_face.append(result[1][0])

            back_dict = text_processing_back(ocr_text_back)
            face_dict = text_processing_face(ocr_text_face)
            back_dict.update(face_dict)

            # Save carteID (removed)
            # carte_id = CarteID(image_avant=fs.path(url))
            # carte_id.save()
            # initial_dict['carte_id'] = carte_id.pk

            # Clean up
            if fs.exists(urlf):
                fs.delete(urlf)

            if fs.exists(urlb):
                fs.delete(urlb)

            form = AddPatientForm(initial=back_dict)
            data = {'html_form': render_to_string('includes/partial_patient_create.html', {'form': form}, request)}
            return JsonResponse(data, status=200)

    else:
        form_str = render_to_string('includes/partial_carteid_form.html', context={'form': CarteIDForm()})
        data = {'form_carte': form_str}
        return JsonResponse(data, status=200)

