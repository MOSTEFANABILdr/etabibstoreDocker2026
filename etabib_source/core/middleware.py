from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from notifications.models import Notification

from core.utils import get_template_version


def notification_middleware(get_response):
    def middleware(request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        notif_id = request.GET.get('notif_id', None)
        if notif_id:
            Notification.objects.filter(id=notif_id).mark_all_as_read()
        response = get_response(request)
        return response

    return middleware


def profile_middleware(get_response):
    def middleware(request):
        request.template_version = get_template_version(request=request)

        #update crispy configuration
        if request.template_version == "v2":
            settings.CRISPY_TEMPLATE_PACK = "bootstrap4"
        elif request.template_version == "v1":
            settings.CRISPY_TEMPLATE_PACK = "bootstrap3"
        response = get_response(request)
        return response

    return middleware


class ForceDefaultLanguageMiddleware(MiddlewareMixin):
    """
    Ignore Accept-Language HTTP headers

    This will force the I18N machinery to always choose settings.LANGUAGE_CODE
    as the default initial language, unless another one is set via sessions or cookies

    Should be installed *before* any middleware that checks request.META['HTTP_ACCEPT_LANGUAGE'],
    namely django.middleware.locale.LocaleMiddleware
    """

    def process_request(self, request):
        if 'HTTP_ACCEPT_LANGUAGE' in request.META:
            del request.META['HTTP_ACCEPT_LANGUAGE']
