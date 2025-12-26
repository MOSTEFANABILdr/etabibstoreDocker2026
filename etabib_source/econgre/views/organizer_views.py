import datetime
import itertools
import json
import traceback
import uuid

import requests
from dal import autocomplete
from datatableview import columns, Datatable
from datatableview.views import DatatableView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import DetailView
from fm.views import AjaxCreateView, AjaxUpdateView, AjaxDeleteView
from invitations.views import AcceptInvite, accept_invitation

from core.decorators import is_organizer
from core.forms.forms import AvatarForm
from core.mixins import TemplateVersionMixin
from core.models import Video
from core.templatetags.avatar_tags import avatar
from core.utils import generateJwtToken
from econgre.forms import CongressForm, WebinarForm, SendInvitationsForm, SpeakerForm, SponsorImageUploadForm, \
    CongreImageUploadForm, CancelCongressForm, PublishWebinarForm, ModerateurForm, WebinarVideoForm, \
    CancelWebinarVideoForm, WebinarUrlForm, OrganizerProfileForm
from econgre.models import Congre, Webinar, CongressInvitation, Speaker, Sponsor, \
    Moderateur, WebinarVideo, UserParticipationWebinar, WebinarUrl, Organisateur
from econgre.templatetags.congre_tags import renderStatus, renderType
from etabibWebsite import settings


@login_required
@is_organizer
def dashboard(request):
    context = {
        "title": _("Dashboard"),
        "sidebar_dashboard": True,
    }
    return render(request, "organizer/dashboard.html", context)


@login_required
@is_organizer
def profile(request):
    title = _('My Profile')
    organisateur = get_object_or_404(Organisateur, user=request.user)
    if request.method == 'POST':
        avatarForm = AvatarForm()  # this form is submitted with ajax request see: views.avatarUpload
        form = OrganizerProfileForm(instance=organisateur, data=request.POST)
        if form.is_valid():
            form.save(commit=True)
            messages.success(request, _("Mise à jour du profil réussie"))
    else:
        avatarForm = AvatarForm()
        form = OrganizerProfileForm(
            initial={
                'nom': organisateur.user.first_name,
                'prenom': organisateur.user.last_name,
            },
            instance=organisateur
        )
    sidebar_profile = True

    context = {
        "title": title,
        "sidebar_profile": sidebar_profile,
        "organisateur": organisateur,
        "form": form,
        "avatarForm": avatarForm,
    }
    return render(request, "organizer/profile.html", context)


################################
# Congre views
################################
class CongreDatatable(Datatable):
    date = columns.TextColumn(_("Période"), source=None, processor='get_entry_date')
    type = columns.TextColumn(_("Type"), source=None, processor='get_entry_type')
    status = columns.TextColumn(_("Etat"), source=None, processor='get_entry_status')
    actions = columns.TextColumn(_("Choisir votre action"), source=None, processor='get_entry_action')
    nom = columns.TextColumn(_("Titre du Congrès"), source="nom")

    class Meta:
        columns = ["nom", "type", "date", "status", "actions"]
        search_fields = ['nom']
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 10

    def get_entry_date(self, instance, **kwargs):
        out = ""
        if instance.date_debut:
            out = instance.date_debut.strftime("%Y-%m-%d %H:%M:%S")
        if instance.date_fin:
            out += "<br>à<br>" + instance.date_fin.strftime("%Y-%m-%d %H:%M:%S")
        return out

    def get_entry_status(self, instance, **kwargs):
        return renderStatus(instance)

    def get_entry_type(self, instance, **kwargs):
        return renderType(instance)

    def get_entry_action(self, instance, **kwargs):
        return render_to_string("partial/datatable-congress-actions.html",
                                {'congre': instance, "user": self.view.request.user})


class CongressDatatableView(DatatableView):
    template_name = "organizer/my_congress_list.html"
    model = Congre
    datatable_class = CongreDatatable

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(CongressDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Mes Congrès")
        context['sidebar_congress'] = True
        return context

    def get_queryset(self):
        if self.user:
            return Congre.objects.filter(organisateur__user=self.user, archive=False)
        return Congre.objects.all()


@login_required
def sponsorImageUpload(request):
    if request.is_ajax():
        form = SponsorImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            pi = form.save()
            return JsonResponse({'file_id': pi.pk, "file_url": pi.image.url}, status=200)
        else:
            return JsonResponse({'error': form.errors}, status=500)


@login_required
def congreImageUpload(request):
    if request.is_ajax():
        form = CongreImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            pi = form.save()
            return JsonResponse({'file_id': pi.pk, "file_url": pi.image.url}, status=200)
        else:
            return JsonResponse({'error': form.errors}, status=500)


class CreateCongressView(SuccessMessageMixin, AjaxCreateView):
    form_class = CongressForm
    model = Congre
    success_message = _("Congrès créé avec succès")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super(CreateCongressView, self).get_initial()
        # initial['emplacement'] = "36.779592342620816, 3.0566024780273438"
        return initial

    def form_valid(self, form):
        congre = form.save(commit=False)
        congre.organisateur = self.user.organisateur
        congre.save()
        form.save_m2m()
        return super(CreateCongressView, self).form_valid(form)


class UpdateCongressView(SuccessMessageMixin, AjaxUpdateView):
    form_class = CongressForm
    model = Congre
    success_message = _("Congrès mise à jour avec succès")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        context = super().get_initial()
        try:
            if self.get_object():
                if self.get_object().banner_prog:
                    context['banner_prog'] = self.get_object().banner_prog.id
                    context['banner_prog_as_json'] = json.dumps(self.get_object().banner_prog.to_json())
                if self.get_object().sponsor_gold_banniere:
                    context['sponsor_gold_banniere'] = self.get_object().sponsor_gold_banniere.id
                    context['sponsor_gold_banniere_as_json'] = json.dumps(
                        self.get_object().sponsor_gold_banniere.to_json())
                if self.get_object().sponsor_gold_logo:
                    context['sponsor_gold_logo'] = self.get_object().sponsor_gold_logo.id
                    context['sponsor_gold_logo_as_json'] = json.dumps(self.get_object().sponsor_gold_logo.to_json())
                if self.get_object().autre_sponsors.all():
                    l = []
                    for sp in self.get_object().autre_sponsors.all():
                        l.append(str(sp.id))
                    context['autre_sponsors'] = ",".join(l)
                    context['autre_sponsors_as_json'] = json.dumps(
                        [sp.to_json() for sp in self.get_object().autre_sponsors.all()])
        except Exception as e:
            traceback.print_exc()
        return context

    def form_valid(self, form):
        congre = form.save(commit=False)
        congre.save()
        form.save_m2m()
        return super(UpdateCongressView, self).form_valid(form)


class CongressDetailView(TemplateVersionMixin, DetailView):
    model = Congre
    template_name = "organizer/congress-detail.html"

    @method_decorator(login_required)
    # @permission_required("core.can_view_etabib_econgre", return_403=True)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from core.templatetags.role_tags import is_organizer as tis_organiser
        context = super().get_context_data(**kwargs)
        if tis_organiser(self.user):
            qset = self.get_object().webinar_set.filter(
                archive=False
            )
            context['webinars'] = list(
                itertools.chain(
                    qset.filter(date_debut=datetime.datetime.today()),
                    qset.filter(date_debut__gt=datetime.datetime.today()),
                    qset.filter(date_debut__lt=datetime.datetime.today())
                )
            )
        else:
            qset = self.get_object().webinar_set.filter(
                publie=True, archive=False
            )
            context['webinars'] = list(
                itertools.chain(
                    qset.filter(date_debut=datetime.datetime.today()),
                    qset.filter(date_debut__gt=datetime.datetime.today()),
                    qset.filter(date_debut__lt=datetime.datetime.today())
                )
            )
        out = []
        for wb in self.get_object().webinar_set.all():
            for sp in wb.speakers.all():
                if sp not in out:
                    out.append(sp)
        context['speakers'] = out
        context['sidebar_congress'] = True
        return context


class CancelCongressView(SuccessMessageMixin, AjaxUpdateView):
    form_class = CancelCongressForm
    model = Congre
    success_message = _("Congrès annulé!")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        congre = form.save(commit=False)
        congre.annule = True
        congre.save()
        return super(CancelCongressView, self).form_valid(form)


class ArchiveCongressView(SuccessMessageMixin, AjaxUpdateView):
    form_class = CancelCongressForm
    model = Congre
    success_message = _("Congrès archivé!")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        congre = form.save(commit=False)
        congre.archive = True
        congre.save()
        return super(ArchiveCongressView, self).form_valid(form)


class PublishCongressView(SuccessMessageMixin, AjaxUpdateView):
    form_class = CancelCongressForm
    model = Congre
    success_message = _("Congrès publié!")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        congre = form.save(commit=False)
        congre.publie = True
        congre.save()
        return super(PublishCongressView, self).form_valid(form)


#########################################
# Webinar views
#########################################
class UserParticipantDatatable(Datatable):
    dateinscription = columns.TextColumn(_("Date Inscription"), source=None, processor='get_entry_date')
    nom = columns.TextColumn(source="user__first_name")
    prenom = columns.TextColumn(source="user__last_name")
    user = columns.TextColumn(source="user__get_full_name")

    class Meta:
        columns = ["user", "dateinscription"]
        search_fields = ['user__first_name', 'user__last_name']
        hidden_columns = ['nom', 'prenom']
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 10

    def get_entry_date(self, instance, **kwargs):
        out = ""
        if instance.date_creation:
            out = instance.date_creation.strftime("%Y-%m-%d %H:%M:%S")
        return out


class CreateWebinarView(SuccessMessageMixin, AjaxCreateView):
    form_class = WebinarForm
    model = Webinar
    success_message = _("Webinar créé!")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        self.congre_pk = kwargs['congre_pk'] if 'congre_pk' in kwargs else None
        if self.congre_pk:
            try:
                self.congre = Congre.objects.get(pk=self.congre_pk)
            except Congre.DoesNotExist:
                return self.render_json_response({'status': 'error', 'message': '404'})
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(CreateWebinarView, self).get_form_kwargs()
        kwargs.update({'congre': self.congre})
        return kwargs

    def form_valid(self, form):
        webinar = form.save(commit=False)
        webinar.congre = self.congre
        webinar.salle_discussion = "%s" % uuid.uuid4().hex
        webinar.mot_de_passe = User.objects.make_random_password(length=8)
        if webinar.sponsor:
            webinar.sponsor.type = Sponsor.SPONSOR_IMAGE_CHOICES[0][0]
            webinar.sponsor.save()
        webinar.save()
        return super(CreateWebinarView, self).form_valid(form)


class UpdateWebiarView(SuccessMessageMixin, AjaxUpdateView):
    form_class = WebinarForm
    model = Webinar
    success_message = _("Webinar mise à jour!")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        if self.user not in (self.get_object().congre.organisateur.user, self.get_object().moderateurs.all()):
            return self.render_json_response({'status': 'error', 'message': '403 UNAUTHORIZED'})
        self.congre_pk = kwargs['congre_pk'] if 'congre_pk' in kwargs else None
        if self.congre_pk:
            try:
                self.congre = Congre.objects.get(pk=self.congre_pk)
            except Congre.DoesNotExist:
                return self.render_json_response({'status': 'error', 'message': '404'})
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        context = super(UpdateWebiarView, self).get_initial()
        try:
            if self.get_object():
                if self.get_object().sponsor:
                    context['sponsor'] = self.get_object().sponsor.id
                    context['sponsor_as_json'] = json.dumps(self.get_object().sponsor.to_json())
        except Exception as e:
            traceback.print_exc()
        return context

    def get_form_kwargs(self):
        kwargs = super(UpdateWebiarView, self).get_form_kwargs()
        kwargs.update({'congre': self.congre})
        return kwargs

    def form_valid(self, form):
        webinar = form.save(commit=False)
        if webinar.sponsor:
            webinar.sponsor.type = Sponsor.SPONSOR_IMAGE_CHOICES[0][0]
            webinar.sponsor.save()
        webinar.save()
        return super(UpdateWebiarView, self).form_valid(form)


class WebinarDetailView(TemplateVersionMixin, DetailView):
    model = Webinar
    template_name = "organizer/webinar.html"
    context_object_name = "webinar"

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # check if the webinar reached the limit of perticipants
        # To do that we have to call the web service hosted in our jitsi server
        nb_max_participants_reached = False
        #TODO: find a better way
        # ROOM_SIZE_API_URL = "https://%s/api/room-size?room=%s&domain=meet.jitsi" % (
        #     settings.ECONGRE_JITSI_DOMAIN_NAME, self.object.salle_discussion
        # )
        # try:
        #     response = requests.get(ROOM_SIZE_API_URL, verify=False)
        #     if response.status_code == 200:
        #         jsonResponse = response.json()
        #         if jsonResponse:
        #             participants = jsonResponse['participants']
        #             if participants >= self.object.nb_max_participant:
        #                 nb_max_participants_reached = True
        # except requests.exceptions.RequestException as e:
        #     pass
        if not nb_max_participants_reached:
            # send participants to jitsi server
            # the speaker starts by default video, audio on
            from core.templatetags.role_tags import is_speaker, is_organizer, is_moderator
            VIDEO_ON = False
            AUDIO_ON = False
            MODERATE_ON = False
            if is_speaker(self.user):
                VIDEO_ON = True
                AUDIO_ON = True
                MODERATE_ON = True
            elif is_organizer(self.user):
                MODERATE_ON = True
            elif is_moderator(self.user):
                MODERATE_ON = True

            if MODERATE_ON:
                # generate jwt token
                jwtToken = generateJwtToken(self.user)
                if jwtToken:
                    context['jwtToken'] = jwtToken
            context['VIDEO_ON'] = VIDEO_ON
            context['AUDIO_ON'] = AUDIO_ON
        else:
            # send participants to video streaming
            # self.template_name =
            print("send participants to video streaming")
        return context


class PublishWebiarView(SuccessMessageMixin, AjaxUpdateView):
    form_class = PublishWebinarForm
    model = Webinar
    success_message = _("Webinar publié!")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        webinar = form.save(commit=False)
        webinar.publie = True
        webinar.save()
        return super(PublishWebiarView, self).form_valid(form)


class ParticipantDatatableView(DatatableView):
    template_name = "organizer/participant_list.html"
    model = UserParticipationWebinar
    datatable_class = UserParticipantDatatable

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        self.webinar_pk = kwargs['webinar_pk']
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ParticipantDatatableView, self).get_context_data(**kwargs)
        context['title'] = _("Médecin participant")
        context['webinar'] = Webinar.objects.get(id=self.webinar_pk)
        context['sidebar_congress'] = True
        return context

    def get_queryset(self):
        return UserParticipationWebinar.objects.filter(webinar__id=self.webinar_pk)


@login_required
@is_organizer
def PublishAllWebiars(request, congre_pk):
    congre = Congre.objects.get(id=congre_pk)
    wbs = Webinar.objects.filter(congre__id=congre_pk, congre__organisateur__user=request.user, publie=False)
    wbs.update(publie=True)
    messages.success(request, "Tous les webinaires sont publiés avec succès")
    return redirect('/econgre/organizer/congress/%s/%s/' % (congre.id, congre.slug))


class ArchiveWebiarView(SuccessMessageMixin, AjaxUpdateView):
    form_class = PublishWebinarForm
    model = Webinar
    success_message = _("Webinar archivé!")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        webinar = form.save(commit=False)
        webinar.archive = True
        webinar.save()
        return super(ArchiveWebiarView, self).form_valid(form)


###
# Invitations
###
class InvitationDatatable(Datatable):
    created = columns.TextColumn(_("Date d'envoi"), source=None, processor='get_entry_created')
    accepted = columns.TextColumn(_("Accepté"), source=None, processor='get_entry_accepted')

    class Meta:
        columns = ["email", "created", "accepted"]
        search_fields = ['email']
        structure_template = "partial/datatable-bootstrap-structure.html"
        ordering = ['-id']
        page_length = 10

    def get_entry_created(self, instance, **kwargs):
        if instance.created:
            return instance.created.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    def get_entry_accepted(self, instance, **kwargs):
        if instance.accepted:
            return "<i class='fa fa-check green'> </i>"


class InvitationDatatableView(DatatableView):
    template_name = "organizer/invitations.html"
    model = CongressInvitation
    datatable_class = InvitationDatatable

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        self.congre_pk = kwargs['pk'] if 'pk' in kwargs else None
        if self.congre_pk:
            try:
                self.congre = Congre.objects.get(pk=self.congre_pk)
            except Congre.DoesNotExist:
                return self.render_json_response({'status': 'error', 'message': '404'})

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(InvitationDatatableView, self).get_context_data(**kwargs)
        bitems = []
        bitems.append({
            "nom": self.congre.nom,
            "url": reverse('organizer-congress-detail', args=[self.congre.id,])
        })
        bitems.append({
            "nom": "Invitations",
            "url": "#"
        })
        context['bradcome_items'] = bitems
        context['sidebar_congress'] = True
        context['congre'] = self.congre
        return context

    def get_queryset(self):
        return CongressInvitation.objects.filter(congre=self.congre)


class SendInvitationsView(SuccessMessageMixin, AjaxCreateView):
    form_class = SendInvitationsForm
    model = CongressInvitation
    success_message = _("Les invitations ont été envoyées avec succès")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        self.congre_pk = kwargs['congre_pk'] if 'congre_pk' in kwargs else None
        self.type = kwargs['type'] if 'type' in kwargs else None
        if self.congre_pk:
            try:
                self.congre = Congre.objects.get(pk=self.congre_pk)
            except Congre.DoesNotExist:
                return self.render_json_response({'status': 'error', 'message': '404'})
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(SendInvitationsView, self).get_form_kwargs()
        kwargs.update({'congre': self.congre})
        return kwargs

    def form_valid(self, form):
        cis = form.save(commit=False)
        for ci in cis:
            ci.congre = self.congre
            ci.inviter = self.user
            ci.key = get_random_string(64).lower()
            ci.type = self.type
            ci.save()
            if not ci.accepted:
                ci.send_invitation(self.request)
        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(self.get_success_result())


class AcceptInvitation(AcceptInvite):

    def post(self, *args, **kwargs):
        from invitations.adapters import get_invitations_adapter
        from invitations.app_settings import app_settings
        self.object = invitation = self.get_object()

        # Compatibility with older versions: return an HTTP 410 GONE if there
        # is an error. # Error conditions are: no key, expired key or
        # previously accepted key.
        if app_settings.GONE_ON_ACCEPT_ERROR and \
                (not invitation or
                 (invitation and (invitation.accepted or
                                  invitation.key_expired()))):
            return HttpResponse(status=410)

        # No invitation was found.
        if not invitation:
            # Newer behavior: show an error message and redirect.
            get_invitations_adapter().add_message(
                self.request,
                messages.ERROR,
                'invitations/messages/invite_invalid.txt')
            return redirect(app_settings.LOGIN_REDIRECT)

        # The invitation was previously accepted, redirect to the login
        # view.
        if invitation.accepted:
            get_invitations_adapter().add_message(
                self.request,
                messages.ERROR,
                'invitations/messages/invite_already_accepted.txt',
                {'email': invitation.email})
            # Redirect to login since there's hopefully an account already.
            return redirect(app_settings.LOGIN_REDIRECT)

        # The key was expired.
        if invitation.key_expired():
            get_invitations_adapter().add_message(
                self.request,
                messages.ERROR,
                'invitations/messages/invite_expired.txt',
                {'email': invitation.email})
            # Redirect to sign-up since they might be able to register anyway.
            return redirect('{}?type={}'.format(reverse(self.get_signup_redirect())), invitation.type)
        # The invitation is valid.
        # Mark it as accepted now if INVITATIONS_ACCEPT_INVITE_AFTER_FINAL_SIGNUP is False.
        if not app_settings.ACCEPT_INVITE_AFTER_SIGNUP and not settings.INVITATIONS_ACCEPT_INVITE_AFTER_FINAL_SIGNUP:
            accept_invitation(invitation=invitation,
                              request=self.request,
                              signal_sender=self.__class__)

        get_invitations_adapter().stash_verified_email(
            self.request, invitation.email)

        return redirect('{}?type={}'.format(reverse(self.get_signup_redirect()), invitation.type))


####################
# Speakers
####################
class SpeakerAutocomplete(autocomplete.Select2QuerySetView):
    def get_result_label(self, item):
        return "%s %s" % (avatar(item.user, width='40px', height='40px', ), item)

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Speaker.objects.none()
        qs = Speaker.objects.all()
        if self.q:
            qs = qs.filter(Q(user__first_name__istartswith=self.q) | Q(user__last_name__istartswith=self.q))
        return qs


class CreateSpeakerView(SuccessMessageMixin, AjaxCreateView):
    form_class = SpeakerForm
    model = Speaker
    success_message = _("Intervenant crée!")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        self.webinar_pk = kwargs['webinar_pk'] if 'webinar_pk' in kwargs else None
        if self.webinar_pk:
            try:
                self.webinar = Webinar.objects.get(pk=self.webinar_pk)
            except Webinar.DoesNotExist:
                return self.render_json_response({'status': 'error', 'message': '404'})
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(CreateSpeakerView, self).get_form_kwargs()
        kwargs.update({'webinar': self.webinar})
        return kwargs

    def form_valid(self, form):
        speaker = form.save(commit=True)
        speaker.save()
        self.webinar.speakers.add(speaker)
        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(self.get_success_result())


class CancelSpeakerView(SuccessMessageMixin, AjaxUpdateView):
    form_class = PublishWebinarForm
    model = Webinar
    success_message = _("Modérateur retiré!")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        self.speaker_pk = kwargs['speaker_pk'] if 'speaker_pk' in kwargs else None
        if self.speaker_pk:
            try:
                self.speaker = Speaker.objects.get(pk=self.speaker_pk)
            except Speaker.DoesNotExist:
                return self.render_json_response({'status': 'error', 'message': '404'})

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        webinar = form.save(commit=False)
        webinar.speakers.remove(self.speaker)
        webinar.save()
        return super(CancelSpeakerView, self).form_valid(form)


####################
# Moderateurs
####################
class ModerateurAutocomplete(autocomplete.Select2QuerySetView):
    def get_result_label(self, item):
        return "%s %s" % (avatar(item.user, width='40px', height='40px', ), item)

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Moderateur.objects.none()
        qs = Moderateur.objects.all()
        if self.q:
            qs = qs.filter(Q(user__first_name__istartswith=self.q) | Q(user__last_name__istartswith=self.q))
        return qs


class CreateModerateurView(SuccessMessageMixin, AjaxCreateView):
    form_class = ModerateurForm
    model = Moderateur
    success_message = _("Moderateur crée!")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        self.webinar_pk = kwargs['webinar_pk'] if 'webinar_pk' in kwargs else None
        if self.webinar_pk:
            try:
                self.webinar = Webinar.objects.get(pk=self.webinar_pk)
            except Webinar.DoesNotExist:
                return self.render_json_response({'status': 'error', 'message': '404'})
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(CreateModerateurView, self).get_form_kwargs()
        kwargs.update({'webinar': self.webinar})
        return kwargs

    def form_valid(self, form):
        moderateur = form.save(commit=True)
        moderateur.save()
        self.webinar.moderateurs.add(moderateur)
        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return self.render_json_response(self.get_success_result())


class CancelModerateurView(SuccessMessageMixin, AjaxUpdateView):
    form_class = PublishWebinarForm
    model = Webinar
    success_message = _("Modérateur retiré!")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        self.moderateur_pk = kwargs['moderateur_pk'] if 'moderateur_pk' in kwargs else None
        if self.moderateur_pk:
            try:
                self.moderateur = Moderateur.objects.get(pk=self.moderateur_pk)
            except Moderateur.DoesNotExist:
                return self.render_json_response({'status': 'error', 'message': '404'})

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        webinar = form.save(commit=False)
        webinar.moderateurs.remove(self.moderateur)
        webinar.save()
        return super(CancelModerateurView, self).form_valid(form)


###########################################
# Video
###########################################
class WebinarVideoَCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = WebinarVideoForm
    model = WebinarVideo
    success_message = _("video créée!")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        self.organisateur = request.user.organisateur
        self.webinar_pk = kwargs['webinar_pk'] if 'webinar_pk' in kwargs else None
        self.webinar = get_object_or_404(Webinar, id=self.webinar_pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        wvideo = form.save(commit=False)
        video_id = form.cleaned_data['_video']
        video = get_object_or_404(Video, id=video_id)
        wvideo.video = video
        wvideo.webinar = self.webinar
        wvideo.save()
        return super(WebinarVideoَCreateView, self).form_valid(form)


class WebinarVideoCancelView(SuccessMessageMixin, AjaxUpdateView):
    form_class = CancelWebinarVideoForm
    model = WebinarVideo
    success_message = _("video supprimée!")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        self.organisateur = request.user.organisateur
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        congrevideo = form.save(commit=False)
        congrevideo.active = False
        congrevideo.save()
        return super(WebinarVideoCancelView, self).form_valid(form)


###########################################
# Url
###########################################
class WebinarUrlCreateView(SuccessMessageMixin, AjaxCreateView):
    form_class = WebinarUrlForm
    model = WebinarUrl
    success_message = _("Lien ajouté!")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        self.organisateur = request.user.organisateur
        self.webinar_pk = kwargs['webinar_pk'] if 'webinar_pk' in kwargs else None
        self.webinar = get_object_or_404(Webinar, id=self.webinar_pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        wurl = form.save(commit=False)
        wurl.webinar = self.webinar
        wurl.save()
        return super(WebinarUrlCreateView, self).form_valid(form)


class WebinarUrlCancelView(SuccessMessageMixin, AjaxDeleteView):
    model = WebinarUrl
    success_message = _("Lien supprimé!")

    @method_decorator(login_required)
    @method_decorator(is_organizer)
    def dispatch(self, request, *args, **kwargs):
        self.organisateur = request.user.organisateur
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(WebinarUrlCancelView, self).delete(request, *args, **kwargs)
