from django.utils import timezone

from core.models import Contact, Patient
from etabibWebsite import settings
from etabibWebsite.settings import SMS_PHONE
from smsgateway.models import Sms, Critere, SMSTemplate


def smsmDailyQuotaExceeded():
    todays_sms = Sms.objects.filter(date_creation__gte=timezone.now().replace(hour=0, minute=0, second=0)).count()
    return todays_sms >= settings.SMS_DAILY_QUOTA


def sendSms(contact=None, sim=None, smsmodel=None, message=None, critere=None, operateur=None, template=None,
            template_language=None, priority=2, context=None, patient=None):
    if settings.SMS_ENABLED:
        if not smsmDailyQuotaExceeded() or priority == 1:
            sms = Sms()
            number_mobile = None
            source = None
            if contact:
                if contact.mobile:
                    number_mobile = correct_numbers(contact)
                    source = contact
            if patient:
                if patient.telephone:
                    number_mobile = correct_numbers(patient)
                    source = patient
            if number_mobile:
                if number_mobile[:2] == SMS_PHONE.get("Sim1")[:2]:
                    sms.sim = 1
                elif number_mobile[:2] == SMS_PHONE.get("Sim2")[:2]:
                    sms.sim = 2
                else:
                    sms.sim = sim if sim else 1
                if smsmodel:
                    sms.smsmodel = smsmodel
                elif message:
                    sms.message = message
                elif template:
                    sms.template = SMSTemplate.objects.get(name=template, language=template_language)
                if critere:
                    sms.critere = Critere.objects.get(pk=critere)
                if operateur:
                    sms.cree_par = operateur
                sms.priority = priority
                sms.source = source
                sms.save()


def verify_number(obj=None):
    nb = None
    if isinstance(obj, Contact):
        if obj.mobile:
            nb = obj.mobile.replace(' ', '')
    elif isinstance(obj, Patient):
        if obj.telephone:
            nb = str(obj.telephone).replace(' ', '')
    if nb:
        if len(nb) == 10:
            if nb[:2] in ["07", "06", "05"]:
                return True
            else:
                return False
        elif len(nb) == 13:
            if nb[:5] in ["+2137", "+2136", "+2135"]:
                return True
            else:
                return False
        elif len(nb) == 14:
            if nb[:6] in ["002137", "002136", "002135"]:
                return True
            else:
                return False
    else:
        return False


def mobilis_numbers(objects=None):
    mobilis = []
    for obj in objects:
        mb = None
        if isinstance(obj, Contact):
            if obj.mobile:
                mb = obj.mobile.replace(' ', '')
        elif isinstance(obj, Patient):
            if obj.telephone:
                mb = str(obj.telephone).replace(' ', '')

        if mb:
            if len(mb) == 10:
                if mb[:2] in ["07", "06", "05"]:
                    if mb[:2] in ["06"]:
                        mobilis.append(obj.pk)
            elif len(mb) == 13:
                if mb[:5] in ["+2137", "+2136", "+2135"]:
                    if mb[:5] in ["+2136"]:
                        mobilis.append(obj.pk)
            elif len(mb) == 14:
                if mb[:6] in ["002137", "002136", "002135"]:
                    if mb[:6] in ["002136"]:
                        mobilis.append(obj.pk)
        return mobilis


def correct_numbers(obj=None):
    mb = None
    if isinstance(obj, Contact):
        if obj.mobile:
            mb = obj.mobile.replace(' ', '')
    elif isinstance(obj, Patient):
        if obj.telephone:
            mb = str(obj.telephone).replace(' ', '')
    if mb:
        if len(mb) == 13:
            if mb[:5] in ["+2137", "+2136", "+2135"]:
                mb.replace("+213", "0")
        elif len(mb) == 14:
            if mb[:6] in ["002137", "002136", "002135"]:
                mb.replace("00213", "0")
        return mb
