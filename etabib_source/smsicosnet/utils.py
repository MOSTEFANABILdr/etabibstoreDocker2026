import logging
import os
import sys
import tempfile

import requests
from django.db import connection as db_connection
from django.db.models import Q
from post_office.lockfile import FileLock, FileLocked

from core.models import Contact, Patient
from etabibWebsite import settings
from etabibWebsite.settings import env
from smsgateway.models import SMSTemplate
from smsgateway.utils import verify_number
from smsicosnet.models import Smsicosnet, STATUS

logger = logging.getLogger(__name__)


def correct_numbers(obj=None):
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
                return mb.replace("0", "213", 1)
        if len(mb) == 13:
            if mb[:5] in ["+2137", "+2136", "+2135"]:
                return mb.replace("+213", "213")
        elif len(mb) == 14:
            if mb[:6] in ["002137", "002136", "002135"]:
                return mb.replace("00213", "213")


def sms_unicode(text=None):
    return "".join(["%s" % hex(ord(l))[2:].zfill(4) for l in text])


def send_list_sms(objs=None, operateur=None, template=None, template_language=None):
    if settings.SMS_ICOSNET_ENABLED:
        for obj in objs:
            if verify_number(obj):
                send_sms_icosnet(obj=obj, operateur=operateur, template=template,
                                 template_language=template_language)


def send_sms_icosnet(obj=None, message=None, operateur=None, template=None, template_language=None):
    if settings.SMS_ICOSNET_ENABLED:
        smsIcons = Smsicosnet()
        if obj:
            if isinstance(obj, Contact):
                if obj.mobile:
                    number_mobile = correct_numbers(obj)
                    if number_mobile:
                        if message:
                            smsIcons.message = message
                        if template:
                            smsIcons.template = SMSTemplate.objects.get(name=template, language=template_language)
                            smsIcons.message = smsIcons.template.content
                        if operateur:
                            smsIcons.cree_par = operateur

                        smsIcons.status = STATUS.queued
                        smsIcons.source = obj
                        smsIcons.save()


def get_queued_sms():
    query = (
        (Q(status=STATUS.queued) | Q(status=STATUS.requeued))
    )
    return Smsicosnet.objects.filter(query).order_by("id")[:100]


def send_queued_sms():
    """
    Sends out all queued sms
    """
    queued_smss = get_queued_sms()
    total_sent, total_failed, total_requeued = 0, 0, 0

    total_sms = len(queued_smss)

    logger.info('Started sending %s sms.' % total_sms)

    if queued_smss:
        for queued_sms in queued_smss:
            type = '2'
            dlr = '1'
            src = 'eTabib'

            number_mobile = correct_numbers(queued_sms.source)
            if queued_sms.message and number_mobile:
                message = sms_unicode(queued_sms.message)
                try:
                    url = f'{env("SMS_ICOSNET_PROTOCOL")}://{env("SMS_ICOSNET_HOST")}:{env("SMS_ICOSNET_PORT")}/bulksms/bulksms?username=' \
                          f'{env("SMS_ICOSNET_USERNAME")}&password={env("SMS_ICOSNET_PASSWORD")}&type={type}&dlr={dlr}' \
                          f'&destination={number_mobile}&source={src}&message={message}'
                    logger.info('url: %s' % url)
                    payload = {}
                    headers = {}
                    resq = requests.request("GET", url, headers=headers, data=payload)

                    queued_sms.reponse = resq.text

                    if resq.text:
                        if "1701" in resq.text:
                            total_sent += 1
                            queued_sms.status = STATUS.sent
                        elif any(code in resq.text for code in
                                 ["1702", "1703", "1704", "1705", "1706", "1707", "1708", "1709", "1710", "1025"]):
                            queued_sms.status = STATUS.failed
                            total_failed += 1
                        elif "1715" in resq.text:
                            queued_sms.status = STATUS.requeued
                            total_requeued += 1
                except Exception as e:
                    logger.debug('Failed to send sms #%d' % queued_sms.id)
                    total_failed += 1
                    queued_sms.status = STATUS.failed
                queued_sms.save()
    logger.info(
        '%s sms attempted, %s sent, %s failed, %s requeued',
        total_sms, total_sent, total_failed, total_requeued,
    )
    return total_sent, total_failed, total_requeued


def send_queued_sms_until_done(lockfile=os.path.join(tempfile.gettempdir(), 'smsiconsnet')):
    """
    Send smss in queue batch by batch, until all smss have been processed.
    """
    try:
        with FileLock(lockfile):
            logger.info('Acquired lock for sending queued emails at %s.lock', lockfile)
            while True:
                try:
                    send_queued_sms()
                except Exception as e:
                    logger.error(e, exc_info=sys.exc_info(), extra={'status_code': 500})
                    raise

                # Close DB connection to avoid multiprocessing errors
                db_connection.close()

                if not get_queued_sms().exists():
                    break
    except FileLocked:
        logger.info('Failed to acquire lock, terminating now.')
