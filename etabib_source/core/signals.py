import django
from allauth.account.signals import user_logged_in
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User, Group
from django.db.models.signals import pre_save, post_save
from django.dispatch.dispatcher import receiver
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from notifications.models import Notification
from post_office import mail
from post_office.models import Email
from post_office.signals import email_queued
from ptrack.templatetags.ptrack import ptrack

from appointements.models import DemandeRendezVous
from core import tasks
from core.decorators import skip_signal
from core.enums import LoyaltyServices, Role, WebsocketCommand, NotificationVerb
from core.models import CarteProfessionnelle, Module, Partenaire, \
    Action, Tache, Eula, Contact, DetailAction, ServiceFedilite, PointsHistory, DemandeIntervention, Medecin, Patient, \
    EquipeSoins
from core.templatetags.event_tags import is_tech_intervention, is_punctual_tracking, is_formation, \
    is_commercial_request, is_active_tracking
from core.templatetags.notif_tags import getNotificationIconUrl, getNotificationUrl
from core.utils import has_basic_wafi, has_gold_wafi, getUserNotification, getNotificationContent
from etabibWebsite import settings
from smsgateway.utils import verify_number
from smsicosnet.utils import send_sms_icosnet
from teleconsultation.models import Tdemand


@receiver(pre_save, sender=CarteProfessionnelle)
def save_carte_professionnelle(sender, instance, **kwargs):
    """
    PreSave signal used to send a mail to the doctor if his account is verified by an administrator
    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    if not instance._state.adding:
        try:
            carte = CarteProfessionnelle.objects.get(pk=instance.pk)
            if carte.checked is False and instance.checked is True:
                user, contact, license = None, None, None

                if len(carte.medecin_set.all()) > 0:
                    medecin = carte.medecin_set.first()
                    user = medecin.user
                    contact = medecin.contact
                    if medecin.licenses.count() == 1:
                        license = medecin.licenses.first()

                elif len(carte.professionnelsante_set.all()) > 0:
                    professionnelsante = carte.professionnelsante_set.first()
                    user = professionnelsante.user
                    contact = professionnelsante.contact

                if user and contact:
                    instance.date_validation = timezone.now()
                    to = [user.email]
                    from_email = "eTabib <{}>".format(settings.EMAIL_HOST_USER)
                    if license:
                        mail.send(
                            to,
                            from_email,
                            template='account_confirmed_freemium',
                            context={
                                "license": license.clef
                            },
                        )
                    else:
                        mail.send(
                            to,
                            from_email,
                            template='account_confirmed',
                            context={
                            },
                        )
                    if verify_number(contact):
                        send_sms_icosnet(obj=contact, template="account_confirmed", template_language='fr')

        except CarteProfessionnelle.DoesNotExist:
            pass


@receiver(pre_save, sender=Partenaire)
def save_partner(sender, instance, **kwargs):
    """
    PreSave signal used to send a mail to the partner if his account is verified by an administrator
    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    if not instance._state.adding:
        partner = Partenaire.objects.get(pk=instance.pk)
        if partner.verifie == False and instance.verifie == True:
            pass
            # TODO: verify this workflow with the team

            # if partner.user.email:
            #     to = [partner.user.email]
            #     from_email = "eTabib <{}>".format(settings.EMAIL_HOST_USER)
            #     mail.send(
            #         to,
            #         from_email,
            #         template='account_confirmed',
            #         context={
            #         },
            #     )
            #     if verify_number(partner.contact):
            #         sendSms(contact=partner.contact, template="account_confirmed", template_language='fr', priority=1)


@receiver(post_save, sender=Module)
def poste_save_module(sender, instance, created, **kwargs):
    """
    post_save signal used to push a notification to the doctor if a new application is added to the store
    :param sender:
    :param instance:
    :param created:
    :param kwargs:
    :return:
    """
    if created:
        medecins = User.objects.filter(medecin__isnull=False)
        tasks.notify(instance, recipients=medecins, verb='Nouvelle Application',
                     description=
                     "%s: Une nouvelle application disponible, cliquez ici pour plus d'informations" % instance.libelle)


@receiver(post_save, sender=Notification)
def post_save_notification(sender, instance, created, **kwargs):
    """
    Send notification through channels
    :param sender:
    :param instance:
    :param created:
    :param kwargs:
    :return:
    """
    if created:
        channel_layer = get_channel_layer()
        room_group_name = 'chat_%s' % instance.recipient.pk

        icon = getNotificationIconUrl(instance)
        url = getNotificationUrl(instance)
        is_acall = False
        is_patient = None
        notify_count, notify_list_html = getUserNotification(instance.recipient)
        sender_name = ""
        title = ""
        # Teleconsultation call
        if isinstance(instance.actor, Tdemand):
            context = {
                "teleconsultation_url": url,
                "teleconsultationDemand": instance.actor,
                "notification_id": instance.id,
                "recipient": instance.recipient,
            }
            is_acall = True
            is_patient = instance.actor.from_patient
            if hasattr(instance.recipient, "medecin"):
                title = _("Une demande de téléconsultation par %s") % (instance.action_object)
            else:
                title = _("Dr %s vous appel") % instance.action_object
            sender_name = instance.actor.patient.full_name
            content = render_to_string("partial/teleconsultation_demand_notification.html", context)
        else:
            # Appointement
            verb, content = getNotificationContent(instance)
            if isinstance(instance.actor, DemandeRendezVous):
                sender_name = instance.actor.demandeur.get_full_name()

        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'notification_message',
                'data': {
                    'command': WebsocketCommand.NEW_NOTIFICATION.value,
                    'is_a_call': is_acall,
                    'redirect_url': url,
                    'is_patient': is_patient,
                    'notif_title': sender_name if is_acall else "Nouvelle notification",
                    'notif_body': "Vous avez un appel" if is_acall else content,
                    'title': title if isinstance(instance.actor, Tdemand) else False,
                    'content': content,
                    'icon': icon,
                    'url': "" if isinstance(instance.actor, Tdemand) else url,
                    'tdemand_id': instance.actor.pk if isinstance(instance.actor, Tdemand) else "",
                    'notify_count': notify_count,
                    'notify_list_html': notify_list_html,
                    'delay': 40000 if isinstance(instance.actor, Tdemand) else 15000
                }
            }
        )


@receiver(pre_save, sender=Medecin)
def pre_save_medecin(sender, instance, **kwargs):
    """
    pre_save signal used to send notification to the doctor if his points is Increased or decreased
    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    if instance.id is None:  # new object will be created
        pass
    else:
        previous = Medecin.objects.get(id=instance.id)
        if previous.user == instance.user:  # no change in user
            if previous.points != instance.points:  # points fielad will be updated
                diff = instance.points - previous.points
                if diff > 0:
                    tasks.notify(instance, recipients=[instance.user, ], verb=_('Rechargement'),
                                 description=
                                 "Votre compte est crédité de %s point(s)"
                                 % diff)
                else:
                    tasks.notify(instance, recipients=[instance.user, ], verb=_('Débitement'),
                                 description=
                                 "Votre compte est débité de %s point(s)"
                                 % diff)
                # desactivate app
                for poste in instance.postes.all():
                    poste.desactive_apps = (instance.points <= 0)
                    poste.save()
            if previous.solde != instance.solde:  # sold field will be updated
                diff = instance.solde - previous.solde
                if diff.amount > 0:
                    tasks.notify(instance, recipients=[instance.user, ], verb='Rechargement',
                                 description=
                                 "Votre compte est crédité de %s"
                                 % diff)
                else:
                    tasks.notify(instance, recipients=[instance.user, ], verb='Débitement',
                                 description=
                                 "Votre compte est débité de %s"
                                 % diff)


# @receiver(pre_save, sender=Partenaire)
# def pre_save_partenaire(sender, instance, **kwargs):
#     """
#     pre_save signal used to send notification to the partner if his points is Increased or decreased
#     :param sender:
#     :param instance:
#     :param kwargs:
#     :return:
#     """
#     if instance.id is None:  # new object will be created
#         pass
#     else:
#         previous = Partenaire.objects.get(id=instance.id)
#         if previous.user == instance.user:  # no change in user
#             if previous.points != instance.points:  # points fielad will be updated
#                 diff = instance.points - previous.points
#                 if diff > 0:
#                     tasks.notify(instance, recipients=[instance.user, ], verb=_('Rechargement'),
#                                  description=_(
#                                      "Votre compte est crédité de %s point(s), cliquez ici pour plus d'informations"
#                                  ) % diff)
#                 else:
#                     tasks.notify(instance, recipients=[instance.user, ], verb=_('Débitement'),
#                                  description=_(
#                                      "Votre compte est débité de %s point(s), cliquez ici pour plus d'informations"
#                                  ) % diff)


@receiver(pre_save, sender=Action)
@skip_signal()
def pre_save_action(sender, instance, **kwargs):
    if instance.id is None:  # new object will be created
        pass
    else:
        previous = Action.objects.get(id=instance.id)
        if previous.active != instance.active:
            if not instance.active:
                instance.date_cloture = timezone.now()
                if instance.cree_par.user != instance.attribuee_a:
                    description = "%s: %s est marqué comme résolue" % (
                        instance.get_type_display(), instance.contact.full_name
                    )
                    tasks.notify(instance, recipients=[instance.cree_par.user], verb="Demande résolue",
                                 description=description)


@receiver(post_save, sender=Action)
def post_save_action(sender, instance, created, **kwargs):
    if created:
        if instance.attribuee_a:
            if instance.cree_par.user != instance.attribuee_a:
                if is_tech_intervention(instance):
                    verb = 'Intervention technique'
                elif is_punctual_tracking(instance):
                    verb = 'Suivi ponctuel'
                elif is_formation(instance):
                    verb = 'Demande de formation'
                elif is_commercial_request(instance):
                    verb = 'Demande commerciale'
                elif is_active_tracking(instance):
                    verb = 'Suivi Actif'
                else:
                    verb = ""

                description = "Une nouvelle demande a été créée, cliquez ici pour plus d'informations"
                users = []
                if isinstance(instance.attribuee_a, User):
                    users.append(instance.attribuee_a)
                if isinstance(instance.attribuee_a, Group):
                    users = User.objects.filter(groups__name__in=[instance.attribuee_a.name])

                tasks.notify(instance, recipients=users, verb=verb,
                             description=description)


@receiver(post_save, sender=Tache)
def post_save_task(sender, instance, created, **kwargs):
    if created:
        if instance.attribuee_a:
            users = []
            users.append(instance.attribuee_a.user)

            tasks.notify(instance, recipients=users, verb="",
                         description="Une nouvelle tache vous a été assignée, "
                                     "cliquez ici pour plus d'informations")


@receiver(pre_save, sender=Tache)
def pre_save_task(sender, instance: Tache, **kwargs):
    if instance.id:
        previous = Tache.objects.get(id=instance.id)
        if not previous.termine:
            if previous.termine != instance.termine:  # field will be updated
                users = []
                users.append(instance.cree_par.user)

                tasks.notify(instance, recipients=users, verb="",
                             description="La tâche attribuée à %s est marquée comme terminée" % instance.attribuee_a)


@receiver(pre_save, sender=Eula)
def pre_save_eula(sender, instance, **kwargs):
    """
    pre save signal used to set dernier=False for all  previous Eula entries
    before saving the new Eula entry
    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    if instance._state.adding:
        if instance.dernier == True:
            Eula.objects.all().update(dernier=False)


@receiver(pre_save, sender=Contact)
def pre_save_contact(sender, instance, **kwargs):
    """
    Set contact.medecin.first_name and contact.medecin.last_name values
    if contact.nom and contact.prenom have changed
    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    if instance.id is None:  # new object will be created
        pass
    else:
        previous = Contact.all_objects.get(id=instance.id)
        user = None
        if hasattr(previous, 'medecin'):
            user = previous.medecin.user
        elif hasattr(previous, 'partenaire'):
            user = previous.partenaire.user
        elif hasattr(previous, 'professionnelsante'):
            user = previous.professionnelsante.user

        if user:
            user.first_name = instance.nom if instance.nom else ""
            user.last_name = instance.prenom if instance.prenom else ""
            user.save()


@receiver(post_save, sender=DetailAction)
def post_save_detail_action(sender, instance, created, **kwargs):
    """

    :param sender:
    :param instance:
    :param created:
    :param kwargs:
    :return:
    """
    if created:
        if instance.action:
            if instance.cree_par:
                users = [d.cree_par.user for d in instance.action.detail_set.all()]
                users.append(instance.action.cree_par.user)
                # remove duplicates
                users = list(set(users))
                # remove the operator who created the instance
                if instance.cree_par.user in users:
                    users.remove(instance.cree_par.user)

                description = "%s: %s a ajouté un détail" % (
                    instance.action.get_type_display(), instance.cree_par
                )
                tasks.notify(instance, recipients=users, verb="",
                             description=description)


@receiver(pre_save, sender=Patient)
def pre_save_patient(sender, instance, **kwargs):
    """
    pre_save signal used to send notification to the patient if his account is debited or credited
    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    if instance.id is None:  # new object will be created
        pass
    else:
        previous = Patient.objects.get(id=instance.id)
        if previous.user == instance.user:  # no change in user
            if previous.solde != instance.solde:  # sold field will be updated
                diff = instance.solde - previous.solde
                if diff.amount > 0:
                    tasks.notify(instance, recipients=[instance.user, ], verb='Rechargement',
                                 description=
                                 "Votre compte est crédité de %s"
                                 % diff)
                else:
                    tasks.notify(instance, recipients=[instance.user, ], verb='Débitement',
                                 description=
                                 "Votre compte est débité de %s"
                                 % diff)


def record_user_logged_in(sender, user, request, **kwargs):
    """
    if a doctor is logged in increment his points according to his offer
    :param sender:
    :param user:
    :param request:
    :param kwargs:
    :return:
    """
    if hasattr(user, 'medecin'):
        d = user.medecin.date_derniere_connexion_web
        for poste in user.medecin.postes.all():
            if not d or d.date() != timezone.now().date():
                if poste.licence:
                    if has_basic_wafi(poste.licence):
                        try:
                            sf = ServiceFedilite.objects.get(code=LoyaltyServices.WAFI_BASIC.value)
                            poste.medecin.points += sf.nb_points
                            poste.medecin.save()

                            ph = PointsHistory()
                            ph.points = sf.nb_points
                            ph.poste = poste
                            ph.description = "Service de fédélité: %s " % sf.libelle
                            ph.save()
                        except Exception as e:
                            pass

                    if has_gold_wafi(poste.licence):
                        try:
                            sf = ServiceFedilite.objects.get(code=LoyaltyServices.WAFI_GOLD.value)
                            poste.medecin.points += sf.nb_points
                            poste.medecin.save()

                            ph = PointsHistory()
                            ph.points = sf.nb_points
                            ph.poste = poste
                            ph.description = "Service de fédélité: %s " % sf.libelle
                            ph.save()
                        except Exception as e:
                            pass
        user.medecin.date_derniere_connexion_web = timezone.now()
        user.medecin.save()


user_logged_in.connect(record_user_logged_in)


@receiver(post_save, sender=DemandeIntervention)
def post_save_demandeIntervention(sender, instance, created, **kwargs):
    if created:
        users = User.objects.filter(groups__name=Role.COMMUNICATION.value)
        description = "%s demande une assistance" % (instance.poste.medecin)
        tasks.notify(instance, recipients=users, verb="",
                     description=description)


@receiver(post_save, sender=EquipeSoins)
def poste_save_equipe_soins(sender, instance, created, **kwargs):
    if created:
        tasks.notify(instance, recipients=[instance.professionnel], verb=NotificationVerb.DEMAND_ADD_TO_CARE_TEAM.value)


@receiver(email_queued)
def post_email_queued(sender, emails, **kwargs):
    for email in emails:
        if "root@localhost" not in email.from_email:
            tracker_url = ptrack(
                type="Email", email_id=email.id, label=email.subject
            )
            email.html_message = email.html_message + "<br>" + tracker_url
            email.save()


doctor_signup_done = django.dispatch.Signal(providing_args=["user"])
