import ptrack
from post_office.models import Email

from core.models import TrackingPixel
from core.utils import get_client_ip


class EmailTrackingPixel(ptrack.TrackingPixel):
    def record(self, request, *args, **kwargs):
        user_agent = request.META['HTTP_USER_AGENT']
        ip_address = get_client_ip(request)
        traking_type = email_id = label = None
        for key, value in kwargs.items():
            if key == "type":
                traking_type = value
            elif key == "email_id":
                email_id = value
            elif key == "label":
                label = value

        tp = TrackingPixel()
        tp.user_agent = user_agent
        tp.ip_address = ip_address
        tp.type = traking_type
        if label:
            tp.label = label

        if email_id:
            emails = Email.objects.filter(id=email_id)
            if emails.exists():
                tp.source = emails.first()
        tp.save()


ptrack.tracker.register(EmailTrackingPixel)
