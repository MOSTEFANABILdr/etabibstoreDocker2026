from allauth.account.models import EmailAddress
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from post_office import mail

from appointements.models import DemandeRendezVous
from core.enums import Role
from core.models import Contact, Patient, Medecin
from core.templatetags.role_tags import is_doctor
from directory.templatetags.directory_tags import contact_id_unhash, contact_id_hash
from etabibWebsite import settings
from smsgateway.utils import verify_number
from smsicosnet.utils import send_sms_icosnet


@xframe_options_exempt
@csrf_exempt
def signup_directory(request):
    if request.is_ajax():
        if request.method == 'POST':
            context = {}
            contact_id = request.POST.get('contact', None)
            firstname = request.POST.get('inputfirstname', None)
            lastname = request.POST.get('inputlastname', None)
            phone = request.POST.get('inputphone', None)
            choice = request.POST.get('choice', None)

            context['UserExist'] = False
            context['Steptwo'] = True
            context['firstname'] = firstname
            context['lastname'] = lastname
            context['choice'] = choice
            context['phone'] = phone

            context['contact'] = contact_id

            return render(request, 'dmd-rdv.html', context)


@xframe_options_exempt
@csrf_exempt
def signup_step_two(request, template='dmd-rdv.html'):
    if request.is_ajax():
        if request.method == 'POST':
            context = {}
            context['UserExist'] = False
            context['Steptwo'] = False
            contact_id = request.POST.get('contact', None)
            email = request.POST.get('inputemail', None)
            firstname = request.POST.get('inputfirstname', None)
            lastname = request.POST.get('inputlastname', None)
            phone = request.POST.get('inputphone', None)
            choice = request.POST.get('choice', None)

            if User.objects.filter(email=email).exists() or EmailAddress.objects.filter(email=email).exists():
                context['UserExist'] = True
                return render(request, 'dmd-rdv.html', context)

            with transaction.atomic():
                user = User()
                user.first_name = firstname
                user.last_name = lastname
                user.email = email
                password = User.objects.make_random_password()
                user.set_password(password)
                user.username = email
                user.save()
                user.groups.add(Group.objects.get(name=Role.PATIENT.value))
                patient = Patient()
                patient.user = user
                patient.telephone = phone
                patient.save()
                cnt = Contact.objects.get(pk=contact_id)
                dmd = DemandeRendezVous()
                dmd.demandeur = patient.user
                dmd.type = choice
                if is_doctor(cnt):
                    med = Medecin.objects.get(contact=cnt)
                    dmd.destinataire = med.user
                else:
                    dmd.destinataire_contact = cnt

                dmd.save()

                emailaddress = EmailAddress()
                emailaddress.user = user
                emailaddress.primary = True
                emailaddress.verified = False
                emailaddress.email = email
                emailaddress.save()
                mail.send(
                    user.email,
                    settings.DEFAULT_FROM_EMAIL,
                    template='registration_annuaire',
                    context={
                        'username': user.email,
                        'password': password,
                        'login_link': "{}://{}".format(request.scheme, request.get_host())
                    },
                )
                if verify_number(cnt):
                    if dmd.destinataire_contact:
                        message = "Mr {0} Demande à vous consulter - " \
                              "voir la demande sur https://{2}/directory/signup/{1} ".format(patient.full_name, contact_id_hash(dmd.destinataire_contact),  request.META['HTTP_HOST'] )
                    elif dmd.destinataire:
                        message = "Mr {0} Demande à vous consulter - " \
                                  "voir la demande sur https://{{1}}/".format(patient.full_name,  request.META['HTTP_HOST'])
                    send_sms_icosnet(obj=cnt, message=message)
                return render(request, template, context)


def signup_doctor_link_directory(request, template="medecin-directory.html", pk=None):
    context = {}
    demande = DemandeRendezVous.objects.get(destinataire_contact__id=contact_id_unhash(pk))
    context['demande'] = demande
    return render(request, template, context)


def signup_doctor_directory(request):
    if request.is_ajax():
        context = {}
        email = request.POST.get('inputemail', None)
        contact = request.POST.get('contact', None)
        cnt = Contact.objects.get(pk=contact)
        if User.objects.filter(email=email).exists() or EmailAddress.objects.filter(email=email).exists():
            context['MailExist'] = True
            return render(request, 'medecin-signup-request.html', context)
        else:
            with transaction.atomic():
                context['MailExist'] = False
                context['email'] = email
                cnt.email = email
                cnt.save()
                user = User()
                user.email = email
                user.username = email
                password = User.objects.make_random_password()
                user.set_password(password)
                user.save()
                dmends = DemandeRendezVous.objects.filter(destinataire_contact=contact)
                for dmd in dmends:
                    dmd.destinataire = user
                    dmd.destinataire_contact = None
                    dmd.save()
                if cnt.email:
                    user.email = cnt.email
                    emailaddress = EmailAddress()
                    emailaddress.user = user
                    emailaddress.primary = True
                    emailaddress.verified = False
                    emailaddress.email = email
                    emailaddress.save()
                    mail.send(
                        user.email,
                        settings.DEFAULT_FROM_EMAIL,
                        template='registration',
                        context={
                            'username': user.username,
                            'password': password,
                            'login_link': "{}://{}".format(request.scheme, request.get_host())
                        },
                    )
                return render(request, 'medecin-signup-request.html', context)
