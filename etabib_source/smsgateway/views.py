from datatableview import Datatable, columns
from datatableview.views import DatatableView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from fm.views import AjaxCreateView, AjaxUpdateView, AjaxDeleteView
from post_office import mail
from post_office.models import Email
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_tracking.mixins import LoggingMixin

from core.decorators import is_operator
from core.models import Contact
from etabibWebsite import settings
from smsgateway import utils
from smsgateway.forms import SendSmsForm, SmsModelCreateForm, SmsCritereCreateForm, ListenvoiCreateForm, \
    SendSmsModelForm, AddContactToListModelForm, SmsConactProblemForm, EmailModelCreateForm, SendEmailModelForm, \
    SendEmailForm
from smsgateway.models import Sms, SmsModel, Critere, Listenvoi, EmailModel
from smsgateway.serializer import SmsSerializer, SmsStatusSerializer
from smsgateway.utils import smsmDailyQuotaExceeded


###########################
# API
###########################
class SmsSendView(LoggingMixin, generics.ListAPIView):
    serializer_class = SmsSerializer
    http_method_names = ['post', 'head']

    def get_queryset(self):
        if settings.SMS_PASSWORD.get("Password") == self.password:
            return Sms.objects.filter(status="1")
        return None

    def post(self, request, *args, **kwargs):
        self.password = self.request.POST.get("password")
        return self.list(request, *args, **kwargs)


class SmsStatusView(LoggingMixin, generics.GenericAPIView):
    serializer_class = SmsStatusSerializer
    http_method_names = ['post', 'head']

    def post(self, request):
        serializer = SmsStatusSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


##########################
# Liste envoi Statique
##########################
class ListenvoiStatiqueDatatable(Datatable):
    mobilis = columns.TextColumn(_("Numero Mobilis"), source=None, processor='get_entry_mobilis')
    date = columns.TextColumn(_("Date Création"), source=None, processor='get_entry_date_creation')
    createur = columns.TextColumn(source="cree_par__full_name")
    actions = columns.TextColumn(_("Actions"), sources=None, processor='get_entry_action')

    class Meta:
        columns = ["libelle", "mobilis", "date", "createur"]
        search_fields = ["libelle"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-date_creation']
        page_length = 10

    def get_entry_date_creation(self, instance, **kwargs):
        if instance.date_creation:
            return instance.date_creation.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_entry_mobilis(self, instance, **kwargs):
        if instance.mobilis_number:
            return len(instance.mobilis_number)
        else:
            1

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-listeenvoi-actions.html", {'listenvoi': instance})


class ListEnvoiStatiqueDatatableView(DatatableView):
    template_name = "communication/listenvoi-statique-list.html"
    model = Listenvoi
    datatable_class = ListenvoiStatiqueDatatable

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.operateur = request.user.operateur
        return super(ListEnvoiStatiqueDatatableView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Listenvoi.objects.filter(cree_par=self.operateur)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sidebar_sms'] = True
        return context


class ListEnvoiStatiqueDetailDatatable(Datatable):
    nomcomplet = columns.TextColumn(_("Nom Prénom"), source=None, sources="full_name")
    actions = columns.TextColumn(_("Action"), source=None, processor='get_entry_action')

    class Meta:
        columns = ["nomcomplet", "actions"]
        search_fields = ["nom", "prenom"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-date_creation']
        page_length = 10

    def get_entry_action(self, instance, **kwargs):
        kwrgs = self.view.kwargs
        self.listenvoi_id = kwrgs['listenvoi_pk'] if 'listenvoi_pk' in kwrgs else None
        listenvoi = Listenvoi.objects.get(pk=self.listenvoi_id)
        return render_to_string("partial/datatable-update-listeenvoi-actions.html",
                                {'listenvoi': listenvoi, 'contact': instance})


class ListEnvoiStatiqueDetailDatatableView(DatatableView):
    template_name = "communication/listenvoi-statique-detail.html"
    model = Contact
    datatable_class = ListEnvoiStatiqueDetailDatatable

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.listenvoi_id = kwargs['listenvoi_pk'] if 'listenvoi_pk' in kwargs else None
        return super(ListEnvoiStatiqueDetailDatatableView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Listenvoi.objects.get(id=self.listenvoi_id).contacts.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sidebar_sms'] = True
        return context


@login_required
@is_operator
def listEnvoiStatiqueDeleteContact(request, listenvoi_pk, contact_pk):
    contact = Contact.objects.get(pk=contact_pk)
    Listenvoi.objects.get(pk=listenvoi_pk).contacts.remove(contact)
    return redirect(reverse("listenvoi-statique-detail", args=[listenvoi_pk]))


class ListEnvoiStatiqueCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = ListenvoiCreateForm
    model = Listenvoi
    success_message = _("Liste envoi créée avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        listenvoi = form.save(commit=False)
        listenvoi.cree_par = self.operateur
        listenvoi.save()
        return super().form_valid(form)


class ListEnvoiStatiqueUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = ListenvoiCreateForm
    model = Listenvoi
    success_message = _("Liste envoi créée avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        listenvoi = form.save(commit=False)
        listenvoi.cree_par = self.operateur
        listenvoi.save()
        return super().form_valid(form)


class ListEnvoiStatiqueSendSmsModelView(SuccessMessageMixin, AjaxCreateView):
    form_class = SendSmsModelForm
    success_message = _("Sms envoyer a la liste avec succes")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.listenvoi_id = kwargs['listenvoi_pk'] if 'listenvoi_pk' in kwargs else None
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        smsmodel = form.cleaned_data['smsmodel']
        sim = form.cleaned_data['sim']
        listeenvoi = Listenvoi.objects.get(pk=self.listenvoi_id)

        for contact in listeenvoi.contacts.all():
            if settings.SMS_ENABLED:
                if not smsmDailyQuotaExceeded():
                    utils.sendSms(contact=contact, sim=sim, smsmodel=smsmodel, operateur=self.operateur, priority=2)
                else:
                    messages.error(self.request, _("Daily quta exceeded"))
                    return self.render_json_response(self.get_success_result())
            else:
                messages.error(self.request, _("Sms messaging is not enabled"))
                return self.render_json_response(self.get_success_result())

        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(self.get_success_result())


class ListEnvoiStatiqueSendSmsView(SuccessMessageMixin, AjaxCreateView):
    form_class = SendSmsForm
    success_message = _("Sms envoyer a la liste avec succes")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.listenvoi_id = kwargs['listenvoi_pk'] if 'listenvoi_pk' in kwargs else None
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        message = form.cleaned_data['message']
        sim = form.cleaned_data['sim']
        listeenvoi = Listenvoi.objects.get(pk=self.listenvoi_id)

        for contact in listeenvoi.contacts.all():
            if settings.SMS_ENABLED:
                if not smsmDailyQuotaExceeded():
                    utils.sendSms(contact=contact, sim=sim, message=message, operateur=self.operateur, priority=2)
                else:
                    messages.error(self.request, _("Daily quta exceeded"))
                    return self.render_json_response(self.get_success_result())
            else:
                messages.error(self.request, _("Sms messaging is not enabled"))
                return self.render_json_response(self.get_success_result())

        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(self.get_success_result())


class SendSmsToContactView(SuccessMessageMixin, AjaxCreateView):
    form_class = SendSmsForm
    success_message = _("Sms envoyer au prospect avec succes")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.contact = kwargs['contact_pk'] if 'contact_pk' in kwargs else None
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        contact = Contact.objects.get(pk=self.contact)
        message = form.cleaned_data['message']
        sim = form.cleaned_data['sim']

        if utils.verify_number(contact):
            if settings.SMS_ENABLED:
                if not smsmDailyQuotaExceeded():
                    utils.sendSms(contact=contact, sim=sim, message=message, operateur=self.operateur, priority=2)
                else:
                    messages.error(self.request, _("Daily quta exceeded"))
                    return self.render_json_response(self.get_success_result())
            else:
                messages.error(self.request, _("Sms messaging is not enabled"))
                return self.render_json_response(self.get_success_result())

            success_message = self.get_success_message(form.cleaned_data)
            if success_message:
                messages.success(self.request, success_message)
        else:
            messages.error(self.request, "ce contant n'a pas un numéro valide")
        return self.render_json_response(self.get_success_result())


class ListEnvoiStatiqueSendEmailModelView(SuccessMessageMixin, AjaxCreateView):
    form_class = SendEmailModelForm
    success_message = _("Email envoyer a la liste avec succes")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.listenvoi_id = kwargs['listenvoi_pk'] if 'listenvoi_pk' in kwargs else None
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        emailmodel = form.cleaned_data['emailmodel']
        listeenvoi = Listenvoi.objects.get(pk=self.listenvoi_id)
        kwargs_list = []
        for contact in listeenvoi.contacts.all():
            user = None
            if hasattr(contact, "medecin"):
                user = contact.medecin.user
            elif hasattr(contact, "partenaire"):
                user = contact.partenaire.user
            elif hasattr(contact, "professionnelsante"):
                user = contact.professionnelsante.user
            if user and user.email:
                kwargs_list.append({
                    'sender': settings.DEFAULT_FROM_EMAIL,
                    'recipients': [user.email],
                    'subject': emailmodel.subject,
                    'message': emailmodel.message,
                    'html_message': emailmodel.message,
                    'priority': 'low'
                })
            elif contact.email:
                kwargs_list.append({
                    'sender': settings.DEFAULT_FROM_EMAIL,
                    'recipients': [contact.email],
                    'subject': emailmodel.subject,
                    'message': emailmodel.message,
                    'html_message': emailmodel.message,
                    'priority': 'low'
                })
        mail.send_many(kwargs_list)
        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(self.get_success_result())


class ListEnvoiStatiqueSendEmailView(SuccessMessageMixin, AjaxCreateView):
    form_class = SendEmailForm
    success_message = _("Email envoyer a la liste avec succes")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.listenvoi_id = kwargs['listenvoi_pk'] if 'listenvoi_pk' in kwargs else None
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        subject = form.cleaned_data['subject']
        message = form.cleaned_data['message']
        listeenvoi = Listenvoi.objects.get(pk=self.listenvoi_id)
        kwargs_list = []
        for contact in listeenvoi.contacts.all():
            if hasattr(contact, "medecin"):
                user = contact.medecin.user
                if user.email:
                    kwargs_list.append({
                        'sender': settings.DEFAULT_FROM_EMAIL,
                        'recipients': [user.email],
                        'subject': subject,
                        'message': message,
                        'html_message': message,
                        'priority': 'low'
                    })
                elif contact.email:
                    kwargs_list.append({
                        'sender': settings.DEFAULT_FROM_EMAIL,
                        'recipients': [contact.email],
                        'subject': subject,
                        'message': message,
                        'html_message': message,
                        'priority': 'low'
                    })
        mail.send_many(kwargs_list)
        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(self.get_success_result())


##########################
# SMS Model
##########################
class SmsModelDatatable(Datatable):
    libelle = columns.TextColumn(_("libelle"), sources="libelle")
    message = columns.TextColumn(_("message"), sources="message")
    actions = columns.TextColumn(_("Action"), source=None, processor='get_entry_action')

    class Meta:
        columns = ["libelle", "message", "actions"]
        search_fields = ["libelle", "message"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        page_length = 10

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-smsmodel-actions.html", {'sms': instance})


class SmsModelDatatableView(DatatableView):
    template_name = "communication/smsmodel-list.html"
    model = SmsModel
    datatable_class = SmsModelDatatable

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super(SmsModelDatatableView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return SmsModel.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sidebar_sms'] = True
        return context


class SmsModelCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = SmsModelCreateForm
    model = SmsModel
    success_message = _("Sms Model créée avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        return super().form_valid(form)


class SmsModelUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = SmsModelCreateForm
    model = SmsModel
    success_message = _("Sms Model Modifier avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super(SmsModelUpdateView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        smsmodel = form.save(commit=False)
        smsmodel.save
        return super().form_valid(form)


class SmsModelDeleteView(AjaxDeleteView):
    model = SmsModel
    success_message = _("SmsModel est supprimée avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super(SmsModelDeleteView, self).dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(SmsModelDeleteView, self).delete(request, *args, **kwargs)


##########################
# Historique Sms
##########################

class HistoriqueSmsDatatable(Datatable):
    sms = columns.TextColumn(_("Message"), source=None, processor='get_entry_message')
    status = columns.TextColumn(_("Status"), source=None, processor='get_entry_status')
    sim = columns.TextColumn(_("sim"), source=None, processor='get_entry_sim')
    date = columns.TextColumn(_("Date Création"), source=None, processor='get_entry_date_creation')

    class Meta:
        columns = ["sms", "status", "sim", "date"]
        search_fields = ["message", "status", "sim"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-date_creation']
        page_length = 10

    def get_entry_date_creation(self, instance, **kwargs):
        if instance.date_creation:
            return instance.date_creation.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_entry_message(self, instance, **kwargs):
        if instance.message:
            return instance.message
        elif instance.smsmodel:
            return instance.smsmodel.message

    def get_entry_sim(self, instance, **kwargs):
        print(instance.sim)
        if instance.sim == "1":
            return settings.SMS_PHONE.get("Sim1", "")
        elif instance.sim == "2":
            return settings.SMS_PHONE.get("Sim2", "")

    def get_entry_status(self, instance, **kwargs):
        if instance.status == "1":
            return "À ENVOYÉ"
        elif instance.status == "2":
            return "ENVOYÉ"
        elif instance.status == "3":
            return "LIVRÉ"


class HistoriqueSmsDatatableView(DatatableView):
    template_name = "communication/historique-sms.html"
    model = Sms
    datatable_class = HistoriqueSmsDatatable

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.contact_id = kwargs['contact_pk'] if 'contact_pk' in kwargs else None
        self.operateur = request.user.operateur
        return super(HistoriqueSmsDatatableView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Sms.objects.filter(contact=self.contact_id).order_by("-id")


##########################
# List Envoi Dynamique
##########################
class ListEnvoiDynamiqueDatatable(Datatable):
    libelle = columns.TextColumn(sources="libelle")
    ville = columns.TextColumn(sources=['ville__name'])
    pays = columns.TextColumn(sources=['pays__name'])
    specialite_libelle = columns.TextColumn(sources="specialite__libelle")
    specialite = columns.TextColumn(sources=None, processor="get_entry_specialite")
    offre = columns.TextColumn(sources="offre")
    nproblems = columns.TextColumn(_("Situation Contact "), sources=None, processor='get_entry_number')
    actions = columns.TextColumn(_("Actions"), sources=None, processor='get_entry_action')

    class Meta:
        columns = ["libelle", "ville", "pays", "specialite", "offre", "nproblems", "actions"]
        hidden_columns = ["specialite_libelle"]
        search_fields = ["libelle", "ville", "pays", "specialite"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        page_length = 10

    def get_entry_specialite(self, instance, **kwargs):
        if instance.specialite:
            return instance.specialite
        else:
            ""

    def get_entry_number(self, instance, **kwargs):
        if instance.number_problems:
            problems, good, mobilis, problemsmail, goodmail = instance.number_problems
            out = "<dl>"
            out += "<br><dd><span class=label-warning>Numéros incorrecte %s ,email incorrecte %s</span></dd>" % (
                len(problems), len(problemsmail))
            out += "<br><dd><span class=label-primary>Numéros correcte %s, email correcte %s</span></dd>" % (
                len(good), len(goodmail))
            out += "<br><dd><span class=label-success>Numéros Mobilis: %s</span></dd>" % len(mobilis)
            out += "</dl>"
            return out
        else:
            ""

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-smscritere-actions.html", {'smscritere': instance})


class ListEnvoiDynamiqueDatatableView(DatatableView):
    template_name = "commercial/listenvoi-dynamique-list.html"
    model = Critere
    datatable_class = ListEnvoiDynamiqueDatatable

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.contact_id = kwargs['contact_pk'] if 'contact_pk' in kwargs else None
        self.operateur = request.user.operateur
        return super(ListEnvoiDynamiqueDatatableView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Critere.objects.filter(cree_par=self.operateur)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sidebar_sms'] = True
        return context


class ListEnvoiDynamiqueCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = SmsCritereCreateForm
    model = Critere
    success_message = _("Critere Sms créée avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.operateur = request.user.operateur
        return super(ListEnvoiDynamiqueCreateView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        smscritere = form.save(commit=False)
        smscritere.cree_par = self.operateur
        smscritere.save
        return super().form_valid(form)


class ListEnvoiDynamiqueUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = SmsCritereCreateForm
    model = Critere
    success_message = _("Critere Sms créée avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.operateur = request.user.operateur
        return super(ListEnvoiDynamiqueUpdateView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        smscritere = form.save(commit=False)
        smscritere.cree_par = self.operateur
        smscritere.save
        return super().form_valid(form)


class ListEnvoiStatiqueAddContact(SuccessMessageMixin, AjaxCreateView):
    form_class = AddContactToListModelForm
    success_message = _("Ajoutée a liste sms avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.contact_id = kwargs['contact_pk'] if 'contact_pk' in kwargs else None
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        contact = Contact.objects.get(pk=self.contact_id)
        if contact.mobile:
            if utils.verify_number(contact):
                listenvoie = form.cleaned_data['listenvoie']
                ls = get_object_or_404(Listenvoi, pk=listenvoie.pk)
                ls.contacts.add(contact)
                success_message = self.get_success_message(form.cleaned_data)
                if success_message:
                    messages.success(self.request, success_message)
                else:
                    messages.error(self.request, "ce contant n'a pas un numéro valide")
            else:
                messages.error(self.request, "ce contant n'a pas un numéro valide")
        return self.render_json_response(self.get_success_result())


class ListEnvoiDynamiqueSendSmsModelView(SuccessMessageMixin, AjaxCreateView):
    form_class = SendSmsModelForm
    success_message = _("Sms envoyer a la liste avec succes")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.critere = kwargs['critere_pk'] if 'critere_pk' in kwargs else None
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        smsmodel = form.cleaned_data['smsmodel']
        sim = form.cleaned_data['sim']
        problems, good, mobilis, problemsmail, goodmail = Critere.objects.get(pk=self.critere).number_problems
        contacts = Contact.objects.filter(pk__in=good)
        for contact in contacts:
            if settings.SMS_ENABLED:
                if not smsmDailyQuotaExceeded():
                    utils.sendSms(contact=contact, sim=sim, smsmodel=smsmodel, critere=self.critere,
                                  operateur=self.operateur)
                else:
                    messages.error(self.request, _("Daily quta exceeded"))
                    return self.render_json_response(self.get_success_result())
            else:
                messages.error(self.request, _("Sms messaging is not enabled"))
                return self.render_json_response(self.get_success_result())

        success_message = self.get_success_message(form.cleaned_data)

        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(self.get_success_result())


class ListEnvoiDynamiqueSendSmsView(SuccessMessageMixin, AjaxCreateView):
    form_class = SendSmsForm
    success_message = _("Sms envoyer a la liste avec succes")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.critere = kwargs['critere_pk'] if 'critere_pk' in kwargs else None
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        message = form.cleaned_data['message']
        sim = form.cleaned_data['sim']

        problems, good, mobilis, problemsmail, goodmail = Critere.objects.get(pk=self.critere).number_problems
        contacts = Contact.objects.filter(pk__in=good)

        for contact in contacts:
            if settings.SMS_ENABLED:
                if not smsmDailyQuotaExceeded():
                    utils.sendSms(contact=contact, sim=sim, message=message, critere=self.critere,
                                  operateur=self.operateur)
                else:
                    messages.error(self.request, _("Daily quta exceeded"))
                    return self.render_json_response(self.get_success_result())
            else:
                messages.error(self.request, _("Sms messaging is not enabled"))
                return self.render_json_response(self.get_success_result())

        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(self.get_success_result())


class ListEnvoiDynamiqueMobileProblemeDatatable(Datatable):
    username = columns.TextColumn(_("Nom d'utilisateur"), sources=None, processor='get_entry_user')
    nomcomplet = columns.TextColumn(_("Nom Prénom"), source=None, sources="full_name")
    actions = columns.TextColumn(_("Actions"), sources=None, processor='get_entry_action')

    class Meta:
        columns = ["username", "nomcomplet"]
        search_fields = ["nom", "prenom"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        page_length = 10

    def get_entry_user(self, instance, **kwargs):
        if hasattr(instance, "medecin"):
            if instance.medecin.user.username:
                return instance.medecin.user.username

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-update-contact-actions.html", {'contact': instance})


class ListEnvoiDynamiqueMobileProblemeDatatableView(DatatableView):
    template_name = "communication/update-contact-problems.html"
    model = Contact
    datatable_class = ListEnvoiDynamiqueMobileProblemeDatatable

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.critere_id = kwargs['critere_pk'] if 'critere_pk' in kwargs else None
        return super(ListEnvoiDynamiqueMobileProblemeDatatableView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        problems, good, mobilis, problemsmail, goodmail = Critere.objects.get(pk=self.critere_id).number_problems
        return Contact.objects.filter(pk__in=problems)


class ListEnvoiDynamiqueProblemeFixView(SuccessMessageMixin, AjaxUpdateView):
    form_class = SmsConactProblemForm
    model = Contact
    success_message = _("Contact mise à jour avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super(ListEnvoiDynamiqueProblemeFixView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        return super().form_valid(form)


##########################
# Email Model
##########################
class EmailModelDatatable(Datatable):
    libelle = columns.TextColumn(_("libelle"), sources="libelle")
    subject = columns.TextColumn(_("Sujet"), sources="subject")
    message = columns.TextColumn(_("message"), sources="message")
    actions = columns.TextColumn(_("Action"), source=None, processor='get_entry_action')

    class Meta:
        columns = ["libelle", "subject", "message", "actions"]
        search_fields = ["libelle", "subject", "message"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        page_length = 10

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-emailmodel-actions.html", {'email': instance})


class EmailModelDatatableView(DatatableView):
    template_name = "communication/emailmodel-list.html"
    model = EmailModel
    datatable_class = EmailModelDatatable

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super(EmailModelDatatableView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return EmailModel.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sidebar_sms'] = True
        return context


class EmailModelCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = EmailModelCreateForm
    model = EmailModel
    success_message = _("Email Model créée avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        return super().form_valid(form)


class EmailModelUpdateView(SuccessMessageMixin, AjaxUpdateView):
    form_class = EmailModelCreateForm
    model = EmailModel
    success_message = _("Email Model créée avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super(EmailModelUpdateView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        emailmodel = form.save(commit=False)
        emailmodel.save
        return super().form_valid(form)


class EmailModelDeleteView(AjaxDeleteView):
    model = EmailModel
    success_message = _("Email Model est supprimée avec succès")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        return super(EmailModelDeleteView, self).dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(EmailModelDeleteView, self).delete(request, *args, **kwargs)


class SendEmailToContactView(SuccessMessageMixin, AjaxCreateView):
    form_class = SendEmailForm
    success_message = _("Email envoyer a la prospect avec succes")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.contact = kwargs['contact_pk'] if 'contact_pk' in kwargs else None
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        contact = Contact.objects.get(pk=self.contact)
        subject = form.cleaned_data['subject']
        message = form.cleaned_data['message']

        if hasattr(contact, "medecin"):
            user = contact.medecin.user
        elif hasattr(contact, "partenaire"):
            user = contact.partenaire.user
        elif hasattr(contact, "professionnelsante"):
            user = contact.professionnelsante.user
        if user and user.email:
            try:
                validate_email(user.email)
                mail.send(
                    user.email,
                    settings.DEFAULT_FROM_EMAIL,
                    subject=subject,
                    message=message,
                    html_message=message,
                    priority='low'
                )
                success_message = self.get_success_message(form.cleaned_data)
                if success_message:
                    messages.success(self.request, success_message)
            except ValidationError:
                messages.error(self.request, "ce contant n'a pas un Email valide")
        elif contact.email:
            try:
                validate_email(contact.email)
                mail.send(
                    contact.email,
                    settings.DEFAULT_FROM_EMAIL,
                    subject=subject,
                    message=message,
                    html_message=message,
                    priority='low'
                )
                success_message = self.get_success_message(form.cleaned_data)
                if success_message:
                    messages.success(self.request, success_message)
            except ValidationError:
                messages.error(self.request, "ce contant n'a pas un Email valide")

        return self.render_json_response(self.get_success_result())


class ListEnvoiDynamiqueSendEmailModelView(SuccessMessageMixin, AjaxCreateView):
    form_class = SendEmailModelForm
    success_message = _("Email envoyer a la liste avec succes")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.critere = kwargs['critere_pk'] if 'critere_pk' in kwargs else None
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        emailmodel = form.cleaned_data['emailmodel']
        problems, good, mobilis, problemsmail, goodmail = Critere.objects.get(pk=self.critere).number_problems
        contacts = Contact.objects.filter(pk__in=goodmail)
        kwargs_list = []
        for contact in contacts:
            if hasattr(contact, "medecin"):
                user = contact.medecin.user
            elif hasattr(contact, "partenaire"):
                user = contact.partenaire.user
            elif hasattr(contact, "professionnelsante"):
                user = contact.professionnelsante.user
            if user and user.email:
                kwargs_list.append({
                    'sender': settings.DEFAULT_FROM_EMAIL,
                    'recipients': [user.email],
                    'subject': emailmodel.subject,
                    'message': emailmodel.message,
                    'html_message': emailmodel.message,
                    'priority': 'low'
                })
            elif contact.email:
                kwargs_list.append({
                    'sender': settings.DEFAULT_FROM_EMAIL,
                    'recipients': [contact.email],
                    'subject': emailmodel.subject,
                    'message': emailmodel.message,
                    'html_message': emailmodel.message,
                    'priority': 'low'
                })
        mail.send_many(kwargs_list)

        success_message = self.get_success_message(form.cleaned_data)

        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(self.get_success_result())


class ListEnvoiDynamiqueSendEmailView(SuccessMessageMixin, AjaxCreateView):
    form_class = SendEmailForm
    success_message = _("Email envoyer a la liste avec succes")

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.critere = kwargs['critere_pk'] if 'critere_pk' in kwargs else None
        self.operateur = request.user.operateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        subject = form.cleaned_data['subject']
        message = form.cleaned_data['message']
        problems, good, mobilis, problemsmail, goodmail = Critere.objects.get(pk=self.critere).number_problems
        contacts = Contact.objects.filter(pk__in=goodmail)
        kwargs_list = []
        for contact in contacts:
            user = None
            if hasattr(contact, "medecin"):
                user = contact.medecin.user
            elif hasattr(contact, "partenaire"):
                user = contact.partenaire.user
            elif hasattr(contact, "professionnelsante"):
                user = contact.professionnelsante.user
            if user and user.email:
                kwargs_list.append({
                    'sender': settings.DEFAULT_FROM_EMAIL,
                    'recipients': [user.email],
                    'subject': subject,
                    'message': message,
                    'html_message': message,
                    'priority': 'low'
                })
            elif contact.email:
                kwargs_list.append({
                    'sender': settings.DEFAULT_FROM_EMAIL,
                    'recipients': [contact.email],
                    'subject': subject,
                    'message': message,
                    'html_message': message,
                    'priority': 'low'
                })
        mail.send_many(kwargs_list)

        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(self.get_success_result())


class ListCritereEmailProblemeDatatable(Datatable):
    username = columns.TextColumn(_("Nom d'utilisateur"), sources=None, processor='get_entry_user')
    nomcomplet = columns.TextColumn(_("Nom Prénom"), source=None, sources="full_name")
    actions = columns.TextColumn(_("Actions"), sources=None, processor='get_entry_action')

    class Meta:
        columns = ["username", "nomcomplet"]
        search_fields = ["nom", "prenom"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        page_length = 10

    def get_entry_user(self, instance, **kwargs):
        if hasattr(instance, "medecin"):
            if instance.medecin.user.username:
                return instance.medecin.user.username

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-update-contact-actions.html", {'contact': instance})


class ListEnvoiDynamiqueEmailProblemeDatatableView(DatatableView):
    template_name = "communication/update-contact-email-problems.html"
    model = Contact
    datatable_class = ListCritereEmailProblemeDatatable

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        self.critere_id = kwargs['critere_pk'] if 'critere_pk' in kwargs else None
        return super(ListEnvoiDynamiqueEmailProblemeDatatableView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        problems, good, mobilis, problemsmail, goodmail = Critere.objects.get(pk=self.critere_id).number_problems
        return Contact.objects.filter(pk__in=problemsmail)


##########################
# Historique Email
##########################

class HistoriqueEmailDatatable(Datatable):
    status = columns.TextColumn(_("Status"), sources=['get_status_display'])
    date = columns.TextColumn(_("Date"), sources=None, processor='get_entry_date')

    class Meta:
        columns = ["subject", "status", "date"]
        search_fields = ["subject"]
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 10

    def get_entry_date(self, instance, **kwargs):
        if instance.created:
            return instance.created.strftime("%Y-%m-%d %H:%M:%S")
        return ""


class HistoriqueEmailDatatableView(DatatableView):
    model = Email
    datatable_class = HistoriqueEmailDatatable

    @method_decorator(login_required)
    @method_decorator(is_operator)
    def dispatch(self, request, *args, **kwargs):
        contact_id = kwargs['contact_pk'] if 'contact_pk' in kwargs else None
        self.contact = get_object_or_404(Contact, id=contact_id)
        return super(HistoriqueEmailDatatableView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        user = None
        if hasattr(self.contact, "medecin"):
            user = self.contact.medecin.user
        elif hasattr(self.contact, "partenaire"):
            user = self.contact.partenaire.user
        elif hasattr(self.contact, "professionnelsante"):
            user = self.contact.professionnelsante.user

        if user and user.email:
            email = user.email
        else:
            email = self.contact.email
        if email:
            return Email.objects.filter(to__icontains=email).order_by("-id")
        else:
            return Email.objects.none()
