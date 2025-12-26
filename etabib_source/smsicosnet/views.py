from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse

from core.decorators import is_operator
from core.models import Prospect, Contact
from smsgateway.models import SMSTemplate
from smsicosnet.models import Smsicosnet
from smsicosnet.utils import send_list_sms


@login_required
@is_operator
def SendSmsProspectIcosnet(request):
    prospect = Prospect.objects.filter(cree_par__user=request.user).values("contact__id")
    sms = SMSTemplate.objects.get(name="show_doctor", language="ar")
    contactIdsmsList = Smsicosnet.objects.filter(template=sms, contact__in=prospect).values("contact__id")
    contactId = prospect.exclude(contact__id__in=contactIdsmsList)
    if contactId:
        contacts = Contact.objects.filter(pk__in=contactId)
        send_list_sms(objs=contacts, operateur=request.user.operateur, template="show_doctor", template_language="ar")
        messages.add_message(request, messages.SUCCESS, 'Message envoyé')
    else:
        messages.add_message(request, messages.ERROR, 'Le message a déjà été envoyé au prospects')
    return HttpResponseRedirect(reverse('commercial-list-prospect'))
