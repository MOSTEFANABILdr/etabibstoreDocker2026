import datetime
import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from djmoney.models.fields import MoneyField

from appointements.models import DemandeRendezVous
from core.models import Patient, Medecin
from coupons.models import Coupon
from etabibWebsite import settings


class Tdemand(models.Model):
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.DO_NOTHING, verbose_name=_("Patient"))
    medecin = models.ForeignKey(Medecin, on_delete=models.DO_NOTHING, verbose_name=_("Médecin"))
    date_demande = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de la demande"))
    salle_discussion = models.CharField(max_length=50, null=True, blank=True,
                                        verbose_name=_("Nom de la salle de discussion"))
    mot_de_passe = models.CharField(max_length=20, null=True, blank=True, verbose_name=_("Mot de passe"))
    annulee = models.BooleanField(default=False, verbose_name=_("Annulée"))
    acceptee = models.BooleanField(default=False, verbose_name=_("Acceptée"))
    rendez_vous = models.OneToOneField(DemandeRendezVous, on_delete=models.PROTECT, null=True, blank=True)
    facturee = models.BooleanField(default=False, verbose_name=_("Facturée"))
    tarif = MoneyField(verbose_name=_("Tarif"), max_digits=14, decimal_places=0,
                       default_currency='DZD', default=0,
                       null=True, blank=True)
    gain = MoneyField(verbose_name=_("Gain"), max_digits=14, decimal_places=0,
                      default_currency='DZD', default=0,
                      null=True, blank=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT, null=True, blank=True)
    sessions = models.ManyToManyField('Tsession', verbose_name=_("Sessions"), blank=True)
    feedbacks = models.ManyToManyField('Tfeedback', verbose_name=_("Feedbacks"), blank=True)
    from_patient = models.BooleanField(default=True)

    def createRoom(self):
        self.salle_discussion = "%s" % uuid.uuid4().hex
        self.mot_de_passe = User.objects.make_random_password(length=8)

    def is_still_valid(self):
        return not self.annulee and not self.acceptee and (
                timezone.now() - self.date_demande
        ).total_seconds() < settings.CANCELLATION_TIME

    @staticmethod
    def is_rejected(user):
        dmds = Tdemand.objects.filter(patient__user=user)
        if dmds:
            return (timezone.now() - dmds.latest('id').date_demande).total_seconds() < getattr(settings,
                                                                                               "TIME_BETWEEN_DEMANDS",
                                                                                               60)
        return False

    @property
    def is_free(self):
        #a demand is free of charge if the doctor accept to do a teleconsultation free when fixing the RDV
        if self.rendez_vous:
            if self.rendez_vous.gratuit:
                return True
        return False

    def caller_name(self, user):
        if user == self.medecin.user:
            return self.medecin.full_name
        if user == self.patient.user:
            return self.patient.full_name
        return "Anonyme"

    class Meta:
        verbose_name = _("Demande")
        verbose_name_plural = _("Demandes")


class Tsession(models.Model):
    """
    this model is used to save econsultion session between a patient and a doctor
    """
    date_creation = models.DateTimeField(verbose_name=_("Date de création"))
    statistiques_conférenciers = models.ManyToManyField('TspeakerStats',
                                                        verbose_name=_("Statistiques des conférenciers"), blank=True)

    class Meta:
        verbose_name = _("Session")
        verbose_name_plural = _("Sessions")


class TspeakerStats(models.Model):
    """
        this model is used to save econsultion speaker stats
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    total_dominant_speaker_time = models.DurationField(blank=True, null=True)

    class Meta:
        verbose_name = _("Statistique conférencier")
        verbose_name_plural = _("statistiques conférenciers")


class Treclamation(models.Model):
    """
    this model is used to save econsultion reclamation
    message: from the patient
    reponse: from the doctor
    you can get patient and doctor values from tdemande
    """
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    message = models.TextField()
    reponse = models.TextField(null=True, blank=True)
    tdemande = models.OneToOneField(Tdemand, on_delete=models.CASCADE, verbose_name=_("Demande de Téléconsultation"))

    class Meta:
        verbose_name = _("Réclamation")
        verbose_name_plural = _("Réclamations")


class Tfeedback(models.Model):
    """
    this model is used to save users feedbacks
    """
    MESSAGE_CHOICES = (
        ("1", _('Acceptable')),
        ("2", _('Bon')),
        ("3", _('Mauvais')),
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    message = models.CharField(max_length=1, choices=MESSAGE_CHOICES, null=True, blank=True)

    class Meta:
        verbose_name = _("Feedback")
        verbose_name_plural = _("Feedbacks")


class PresenceManager(models.Manager):
    def touch(self, channel_name):
        self.filter(channel_name=channel_name).update(last_seen=now())

    def leave_all(self, channel_name):
        for presence in self.select_related("room").filter(channel_name=channel_name):
            room = presence.room
            room.remove_presence(presence=presence)

    def setBusy(self, user, stauts, time=None):
        self.filter(user=user).update(busy=stauts, remove_busy_after=time)


class Presence(models.Model):
    room = models.ForeignKey("Room", on_delete=models.CASCADE)
    channel_name = models.CharField(
        max_length=255, help_text="Reply channel for connection that is present"
    )
    user = models.ForeignKey(
        User, null=True, on_delete=models.CASCADE
    )
    nombre_session = models.IntegerField(
        default=1
    )
    last_seen = models.DateTimeField(default=now)

    remove_busy_after = models.DateTimeField(null=True, blank=True)
    busy = models.BooleanField(default=False)

    objects = PresenceManager()

    def __str__(self):
        return self.channel_name

    def increment_session(self):
        self.nombre_session = self.nombre_session + 1
        self.save()

    def decrement_session(self):
        self.nombre_session = self.nombre_session - 1
        self.save()

    class Meta:
        unique_together = [("room", "channel_name")]


class RoomManager(models.Manager):
    def add(self, room_channel_name, user_channel_name, user=None):
        room, created = Room.objects.get_or_create(channel_name=room_channel_name)
        room.add_presence(user_channel_name, user)
        return room

    def remove(self, room_channel_name, user_channel_name):
        try:
            room = Room.objects.get(channel_name=room_channel_name)
        except Room.DoesNotExist:
            return
        room.remove_presence(user_channel_name)

    def prune_presences(self, channel_layer=None, age=None):
        for room in Room.objects.all():
            room.prune_presences(age)

    def prune_rooms(self):
        Room.objects.filter(presence__isnull=True).delete()


class Room(models.Model):
    channel_name = models.CharField(
        max_length=255, unique=True, help_text="Group channel name for this room"
    )

    objects = RoomManager()

    def __str__(self):
        return self.channel_name

    def has_presence(self, user):
        return Presence.objects.filter(room=self, user=user).exists()

    def add_presence(self, channel_name, user=None):
        if user and user.is_authenticated:
            authed_user = user
        else:
            authed_user = None
        presence, created = Presence.objects.get_or_create(
            room=self, channel_name=channel_name, user=authed_user
        )
        if created:
            self.broadcast_changed(added=presence)
        else:
            presence.increment_session()

    def remove_presence(self, channel_name=None, presence=None):
        if presence is None:
            try:
                presence = Presence.objects.get(room=self, channel_name=channel_name)
            except Presence.DoesNotExist:
                return

        if presence.nombre_session > 1:
            presence.decrement_session()
        else:
            presence.delete()
            self.broadcast_changed(removed=presence)

    def prune_presences(self, age_in_seconds=None):
        if age_in_seconds is None:
            age_in_seconds = getattr(settings, "CHANNELS_PRESENCE_MAX_AGE", 60)

        num_deleted, num_per_type = Presence.objects.filter(
            room=self, last_seen__lt=now() - datetime.timedelta(seconds=age_in_seconds)
        ).delete()
        if num_deleted > 0:
            self.broadcast_changed(bulk_change=True)

        # prune busy state
        Presence.objects.filter(
            busy=True, remove_busy_after__lt=now()
        ).update(busy=False, remove_busy_after=None)

    def get_users(self):
        return User.objects.filter(presence__room=self).distinct()

    def get_anonymous_count(self):
        return self.presence_set.filter(user=None).count()

    def broadcast_changed(self, added=None, removed=None, bulk_change=False):
        from teleconsultation.signals import presence_changed
        presence_changed.send(
            sender=self.__class__,
            room=self,
            added=added,
            removed=removed,
            bulk_change=bulk_change,
        )
