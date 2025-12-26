from smsicosnet.utils import send_queued_sms_until_done
from celery import shared_task


@shared_task(ignore_result=True)
def send_queued_sms(*args, **kwargs):
    """
    To be called by the Celery task manager.
    """
    send_queued_sms_until_done()
