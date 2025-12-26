import hashlib

import basehash
from allauth.account.forms import LoginForm
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import update_session_auth_hash, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import JsonResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.template import RequestContext
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.generic import TemplateView
from el_pagination.decorators import page_template
from fm.views import AjaxCreateView
from guardian.mixins import LoginRequiredMixin
from post_office import mail

from core.decorators import is_registered, is_not_verified_professionnal, is_operator, v2_only
from core.enums import Role, WebsocketCommand, AdsStatsType
from core.forms.forms import AvatarForm, SignupForm, \
    ChangePasswordForm, ProfessionalIdentityForm, SignupFormWorkspace
from core.mixins import TemplateVersionMixin
from core.models import Module, Contact, Campagne, Annonce, CampagneImpression, AnnonceClickLog, UserAgreement, \
    ProfessionnelSante, Profile, Patient, AuthBackend
from core.rocketchat import createOrLoginRcUser, joinRcGroups, setRcUserPreferences
from core.templatetags.utils_tags import offer_id_unhash
from core.utils import getUserNotification
from etabibWebsite import settings


@csrf_protect
def index(request):
    loginform = LoginForm()
    apps = Module.objects.order_by('?')[:8]
    csrfContext = RequestContext(request)
    csrfContext['loginform'] = loginform
    csrfContext['apps'] = apps
    return render(request, "index.html", csrfContext)


def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user, password = form.save()
            context = {}
            context["email"] = user.email
            mail.send(
                user.email,
                settings.DEFAULT_FROM_EMAIL,
                template='registration',
                context={
                    'username': user.email,
                    'password': password,
                    'login_link': "{}://{}".format(request.scheme, request.get_host())
                },
            )
            return render(request, "account/informations_sent.html", context)
    else:
        form = SignupForm()
    context = {}
    context['form'] = form
    return render(request, "account/signup.html", context)


@v2_only
@xframe_options_exempt
@csrf_exempt
def signupWorkspace(request):
    if request.method == 'POST':
        form = SignupFormWorkspace(request.POST, request.FILES)
        if form.is_valid():
            context = {}
            user, password = form.save()
            context["email"] = user.email
            mail.send(
                user.email,
                settings.DEFAULT_FROM_EMAIL,
                template='registration',
                context={
                    'username': user.email,
                    'password': password,
                    'login_link': "{}://{}".format(request.scheme, request.get_host())
                },
            )
            return render(request, "account/informations_sent_workspace.html", context, using="v2")
    else:
        form = SignupFormWorkspace()
    context = {}
    context['form'] = form
    return render(request, "account/signup_workspace.html", context, using=request.template_version)


@login_required
@page_template('partial/notifications-list.html')
def notificationsList(request, template="doctor/notifications.html", extra_context=None):
    title = _('Notifications list')
    notifications = request.user.notifications.all().filter(deleted=False).order_by("-id")
    context = {
        "title": title,
        "notifications": notifications,
        "notifications_count": notifications.unread().count()
    }
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context, using=request.template_version)


@login_required
def markAllNotificationsAsRead(request):
    if request.is_ajax():
        request.user.notifications.unread().mark_all_as_read()
        notifications_count = request.user.notifications.unread().count()
        notify_count, notify_list_html = getUserNotification(request.user)
        # send notification through channels
        channel_layer = get_channel_layer()
        room_group_name = 'chat_%s' % request.user.pk
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'notification_message',
                'data': {
                    'command': WebsocketCommand.FETCH_NOTIFICATIONS.value,
                    'notify_list_html': notify_list_html,
                    'notify_count': notify_count
                }
            }
        )
        return JsonResponse({'status': "All notifications marked as read",
                             "notifications_count": "%s %s" % (notifications_count, _("unread"))},
                            status=200)
    else:
        return JsonResponse({'status': "Not an ajax request"}, status=500)


@login_required
def markAllNotificationsAsUnread(request):
    if request.is_ajax():
        request.user.notifications.all().mark_all_as_unread()
        notifications_count = request.user.notifications.unread().count()
        notify_count, notify_list_html = getUserNotification(request.user)
        # send notification through channels
        channel_layer = get_channel_layer()
        room_group_name = 'chat_%s' % request.user.pk
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'notification_message',
                'data': {
                    'command': WebsocketCommand.FETCH_NOTIFICATIONS.value,
                    'notify_count': notify_count,
                    'notify_list_html': notify_list_html
                }
            }
        )
        return JsonResponse(
            {'status': "All notifications marked as unread",
             "notifications_count": "%s %s" % (notifications_count, _("unread"))}, status=200)
    else:
        return JsonResponse({'status': "Not an ajax request"}, status=500)


@login_required
def deleteNotification(request):
    if request.is_ajax():
        pk = request.POST.get('notif_id', None)
        request.user.notifications.all().filter(id=pk).update(deleted=True)  # soft delete
        notifications_count = request.user.notifications.unread().count()
        notify_count, notify_list_html = getUserNotification(request.user)
        # send notification through channels
        channel_layer = get_channel_layer()
        room_group_name = 'chat_%s' % request.user.pk
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'notification_message',
                'data': {
                    'command': WebsocketCommand.FETCH_NOTIFICATIONS.value,
                    'notify_count': notify_count,
                    'notify_list_html': notify_list_html
                }
            }
        )
        return JsonResponse(
            {'status': "notification deleted", "notifications_count": "%s %s" % (notifications_count, _("unread"))},
            status=200)
    else:
        return JsonResponse({'status': "Not an ajax request"}, status=500)


@login_required
@is_registered
def register(request):
    return render(request, "common/register.html")


@login_required
@is_registered
def registerProfessionnelSante(request):
    with transaction.atomic():
        contact = Contact()
        contact.save()

        pro = ProfessionnelSante()
        pro.user = request.user
        pro.contact = contact
        pro.save()
        pro.user.groups.add(Group.objects.get(name=Role.VISITOR.value))
    return redirect("professional-identity")


@login_required
@is_not_verified_professionnal
def professionalIdentity(request):
    context = {}
    if request.method == "POST":
        form = ProfessionalIdentityForm(request.POST, request.FILES, professionnelsante=request.user.professionnelsante)
        if form.is_valid():
            form.save()
            return redirect("professional-account-validation")
    else:
        form = ProfessionalIdentityForm(initial={
            "nom": request.user.first_name,
            "prenom": request.user.last_name,
            "mobile": request.user.professionnelsante.contact.mobile,
        })
    context['form'] = form
    return render(request, "common/professional-identity.html", context, using=request.template_version)


class ValidationTelplateView(LoginRequiredMixin, TemplateVersionMixin, TemplateView):
    pass


@login_required
def avatarUpload(request):
    if request.is_ajax():
        form = AvatarForm(request.POST, request.FILES)
        if form.is_valid():
            avatar = form.save()
            if hasattr(request.user, 'avatar'):
                request.user.avatar.image = avatar.image
                request.user.avatar.save()
            else:
                avatar.user = request.user
                avatar.save()
            form.cropImage(avatar)
            return JsonResponse({}, status=200)
        else:
            return JsonResponse({'error': form.errors}, status=400)


@login_required
def annonceClick(request, annonce_id, campagne_id, reseau):
    try:
        hash_campgane = basehash.base36(32)
        campagne_pk = hash_campgane.unhash(campagne_id)
        hash_annonce = basehash.base52(32)
        annonce_pk = hash_annonce.unhash(annonce_id)

        campagne = Campagne.objects.get(id=campagne_pk)
        annonce = Annonce.objects.get(id=annonce_pk)
        if isinstance(campagne, CampagneImpression):
            if annonce not in campagne.annonces.all():
                raise Http404

            acl = AnnonceClickLog()
            acl.campagne = campagne
            acl.annonce = annonce
            acl.date_click = timezone.now()
            acl.user = request.user
            acl.reseau = reseau
            acl.save()
            campagne.partenaire.consumePoints(
                AdsStatsType.CLICK,
                acl
            )
            if annonce.external_link:
                return redirect(annonce.external_link)
            if annonce.article:
                return redirect("partner-detail-product", pk=annonce.article.pk, slug=annonce.article.slug)
            else:
                return redirect("partner-detail-ads", pk=annonce.pk, slug=annonce.slug)
    except Exception as e:
        print(e)
        raise Http404


@login_required
def agreeTermsOfService(request):
    if request.is_ajax():
        pk = request.POST.get('id', None)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return JsonResponse({'error': "target data does not exist"}, status=404)
        if request.user == user:
            context = {
            }
            if UserAgreement.objects.filter(user=user).exists():
                return JsonResponse(context, status=200)
            else:
                ua = UserAgreement()
                ua.user = user
                ua.save()
                return JsonResponse(context, status=200)
        else:
            return JsonResponse({'error': "not authorized"}, status=403)
    else:
        return JsonResponse({'error': "no content"}, status=405)


class ChangePawssordView(SuccessMessageMixin, AjaxCreateView):
    form_class = ChangePasswordForm
    success_message = _("mot de passe changé!")

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.utilisateur = request.user
        self.req = request
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(ChangePawssordView, self).get_form_kwargs()
        kwargs.update({"user": self.utilisateur})
        return kwargs

    def form_valid(self, form):
        user = form.save(commit=False)
        user.save()
        update_session_auth_hash(self.req, user)
        return super(ChangePawssordView, self).form_valid(form)


@login_required
def etabibMobileApp(request):
    return render(request, "common/mobile-app.html", {}, using=request.template_version)


@login_required
@is_operator
def rocketchat(request):
    # Login to rocketChat
    authToken = ""
    try:
        m = hashlib.md5()
        m.update(request.user.username.encode())
        response = createOrLoginRcUser(
            m.hexdigest(),
            "%s %s" % (request.user.first_name, request.user.last_name),
            request.user.email
        )
        authToken = response["data"]["authToken"]
        # join group
        joinRcGroups(request.user, response["data"]["userId"])
        # setUserPreferences
        data = {
            "language": request.LANGUAGE_CODE
        }
        setRcUserPreferences(response["data"]["userId"], data)
    except Exception as e:
        print(e)

    r = render(request, "common/rocket-chat.html", {"authToken": authToken})
    return r


@login_required
def changeTemplate(request):
    if request.template_version == "v1":
        if hasattr(request.user, 'profile'):
            request.user.profile.template_version = 2
            request.user.profile.save()
        else:
            Profile.objects.create(template_version=2, user=request.user)
    elif request.template_version == "v2":
        if hasattr(request.user, 'profile'):
            request.user.profile.template_version = 1
            request.user.profile.save()
        else:
            Profile.objects.create(template_version=1, user=request.user)

    return HttpResponseRedirect("/")


def qrCodeLogin(request):
    if request.is_ajax():
        key = request.POST['pk']
        try:
            patient = Patient.objects.get(pk=offer_id_unhash(key))
            AuthBackend.authenticate(request=request, username=patient.user.username)
            return JsonResponse({'patient': 'patient'}, status=200)
        except ObjectDoesNotExist as e:
            return JsonResponse({'error': 'error'}, status=404)
