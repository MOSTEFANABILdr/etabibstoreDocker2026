from invitations.adapters import get_invitations_adapter
from invitations.models import Invitation
from invitations.views import accept_invitation

from econgre.models import CongressInvitation
from etabibWebsite import settings


def accept_invite_after_final_signup(sender, request, user, **kwargs):
    if hasattr(user, 'medecin'):
        invitation = CongressInvitation.objects.filter(
            email__iexact=user.email
        ).first()
        if invitation:
            accept_invitation(invitation=invitation,
                              request=request,
                              signal_sender=Invitation)


if settings.INVITATIONS_ACCEPT_INVITE_AFTER_FINAL_SIGNUP:
    doctor_signed_up_signal = get_invitations_adapter().get_doctor_signed_up_signal()
    doctor_signed_up_signal.connect(accept_invite_after_final_signup)
