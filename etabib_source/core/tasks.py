from celery import shared_task, Celery
from django.core import management
from django.utils.translation import gettext as _
from notifications import signals
from post_office import mail

from core.models import Poste, PointsHistory

celery = Celery('tasks', broker='redis://localhost:6379/0')


@shared_task
def send_mail(recipients=None, sender=None, template=None, context=None, subject='',
              message='', html_message='', scheduled_time=None, headers=None,
              priority=None, attachments=None, render_on_delivery=False,
              log_level=None, commit=True, cc=None, bcc=None, language='',
              backend=''):
    mail.send(
        recipients, sender, template, context, subject,
        message, html_message, scheduled_time, headers,
        priority, attachments, render_on_delivery,
        log_level, commit, cc, bcc, language,
        backend
    )


@shared_task
def notify(sender, recipients, actor=None, verb=None, action_object=None, target=None, public=True,
           description=None,
           level='info',
           url=None):
    for recipient in recipients:
        signals.notify.send(sender, recipient=recipient, actor=actor, verb=verb,
                            action_object=action_object, target=target, description=description,
                            level=level, public=public, url=url)


"""
TODO: add https://healthchecks.io/ to periodic tasks to Get immediate alerts 
When tasks are not done
"""


@shared_task
def manageConsomation():
    """
    task to manage the consomation of the user
    - this task will be executed every friday
    *   it will get user's yearly consommation
    *   calculate weakly consommation

    :return:
    """
    postes = Poste.objects.all()
    for poste in postes:
        yearly_consommation = poste.yearly_consommation

        if yearly_consommation > 0 and poste.medecin.points > 0:
            consomation = yearly_consommation // 52
            poste.medecin.points = (poste.medecin.points - consomation) if poste.medecin.points >= consomation else 0
            poste.medecin.save()

            if poste.medecin.points < consomation:
                users = [poste.medecin.user,]
                notify(poste, users, verb='',
                                 description=_(
                                     "%s: Votre solde de points est épuisé"
                                 ) % poste.licence.clef)

            ph = PointsHistory()
            ph.points = - consomation
            ph.poste = poste
            ph.description = _("Consommation hebdomadaire")
            ph.save()


@celery.task
def send_queued_mail():
    try:
        """Send queued emails by using Django management command."""
        management.call_command("send_queued_mail", verbosity=0)
    except Exception as e:
        print(e)

@celery.task
def backup_db_and_media():
    # management.call_command("mediabackup", compress=True, clean=True, verbosity=0)
    management.call_command("dbbackup", compress=True, clean=True, verbosity=0)