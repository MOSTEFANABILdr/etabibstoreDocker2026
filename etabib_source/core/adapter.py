from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from invitations.app_settings import app_settings

from core.enums import Role
from core.models import ComptePreCree, Contact, ProfessionnelSante
from core.signals import doctor_signup_done
from core.templatetags.role_tags import is_operator


class AccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        if is_operator(request.user):
            return reverse('operator-dashboard')
        elif request.user.groups.filter(name=Role.PARTNER.value).exists():
            if not hasattr(request.user, 'partenaire'):
                return reverse('partner-registration')
            elif hasattr(request.user, 'partenaire'):
                return reverse('partner-dashboard')
        elif request.user.groups.filter(name=Role.DOCTOR.value).exists():
            if hasattr(request.user, 'medecin'):
                return reverse('doctor-dashboard')
            else:
                return reverse('registration')
        elif hasattr(request.user, 'professionnelsante'):
            if request.user.groups.filter(name__in=[
                Role.PHARMACIST.value, Role.TEACHER.value, Role.RESEARCHER.value, Role.COMPUTER_SCIENCE.value,
                Role.COMM_MARKETING.value, Role.MEDICAL_COMPANY_MANAGER.value, Role.MEDICAL_PURCHASING_MANAGER.value,
                Role.BIOLOGISTE.value, Role.PARAMEDICAL.value, Role.AUXILIARY.value, Role.PSYCHOLOGIST.value,
                Role.MINISTRY.value, Role.ADMINISTRATION.value, Role.STUDENT.value, Role.DENTIST.value,
                Role.VISITOR.value
            ]).exists():
                return reverse('professional-dashboard')
            else:
                return reverse('professional-identity')
        elif request.user.groups.filter(name=Role.PATIENT.value).exists():
            if hasattr(request.user, 'patient'):
                if hasattr(request.user, "profile"):
                    if request.template_version == "v1":
                        return reverse('patient-teleconsultation')
                    elif request.template_version == "v2":
                        return reverse('patient-dashboard')
                else:
                    return reverse('patient-dashboard')
            else:
                return reverse('registration')
        elif request.user.groups.filter(name=Role.ORGANISATEUR.value).exists():
            if hasattr(request.user, 'organisateur'):
                return reverse('organizer-dashboard')
        elif request.user.groups.filter(name=Role.SPEAKER.value).exists():
            if hasattr(request.user, 'speaker'):
                return reverse('speaker-dashboard')
        elif request.user.groups.filter(name=Role.MODERATOR.value).exists():
            if hasattr(request.user, 'moderateur'):
                return reverse('moderator-dashboard')
        elif request.user.is_staff or request.user.is_superuser:
            return reverse('admin:index')
        else:
            return reverse('registration')
        return '/'

    def is_open_for_signup(self, request):
        if hasattr(request, 'session') and request.session.get(
                'account_verified_email'):
            return True
        elif app_settings.INVITATION_ONLY is True:
            # Site is ONLY open for invites
            return False
        else:
            # Site is open to signup
            return True

    def get_doctor_signed_up_signal(self):
        return doctor_signup_done

    def pre_authenticate(self, request, **credentials):
        super(AccountAdapter, self).pre_authenticate(request, **credentials)
        username = credentials["username"]
        password = credentials["password"]
        pre_comptes = ComptePreCree.objects.filter(username=username)
        if pre_comptes.exists():
            if pre_comptes.first().is_available and password == pre_comptes.first().password:
                with transaction.atomic():
                    user = User()
                    user.username = username
                    user.set_password(password)
                    user.save()

                    contact = Contact()
                    contact.save()

                    pro = ProfessionnelSante()
                    pro.user = user
                    pro.contact = contact
                    pro.save()
                    pro.user.groups.add(Group.objects.get(name=Role.VISITOR.value))


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_login_redirect_url(self, request):
        if request.user.groups.filter(name=Role.PATIENT.value).exists():
            if hasattr(request.user, "profile"):
                if request.template_version == "v1":
                    return reverse('patient-teleconsultation')
                elif request.template_version == "v2":
                    return reverse('list-virtual-offices')
            else:
                return reverse('list-virtual-offices')
        else:
            return reverse('doctor-dashboard')
