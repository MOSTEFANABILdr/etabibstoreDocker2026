from datetime import datetime

from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

from appointements.models import DemandeRendezVous
from core.models import Contact
from core.templatetags.role_tags import is_patient
from directory.templatetags.directory_tags import rdv_unhash


def rdv_middleware(get_response):
    def middleware(request):
        if request.user.is_authenticated:
            rdvc = request.GET.get('rdvc', None)
            if rdvc:
                if is_patient(request.user):
                    # try:
                    contact_id, timestamp = rdv_unhash(rdvc)
                    date_rendez_vous = datetime.fromtimestamp(float(timestamp))
                    contact = Contact.objects.get(id=contact_id)

                    exists = False
                    if not hasattr(contact, "medecin"):
                        if DemandeRendezVous.objects.filter(
                                destinataire_contact=contact, date_creation=date_rendez_vous
                        ).exists():
                            messages.warning(request, _("votre demande de rendez-vous a déjà été envoyée au médecin."))
                            exists = True
                    else:
                        if DemandeRendezVous.objects.filter(
                                destinataire=contact.medecin.user, date_creation=date_rendez_vous
                        ).exists():
                            messages.warning(request, _("votre demande de rendez-vous a déjà été envoyée au médecin."))
                            exists = True

                    if not exists:
                        drv = DemandeRendezVous()
                        drv.demandeur = request.user
                        if hasattr(contact, "medecin"):
                            drv.destinataire = contact.medecin.user
                        else:
                            drv.destinataire_contact = contact

                        drv.save()

                        #ovewrite date_creation field
                        drv.date_creation = date_rendez_vous
                        drv.save(update_fields=['date_creation'])

                        messages.success(request, _("Votre demande de rendez-vous a été envoyée au médecin."))


                    # except Exception as e:
                    #     print(e)


        response = get_response(request)
        return response

    return middleware