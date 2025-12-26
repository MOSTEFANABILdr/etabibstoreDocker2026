from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.urls.conf import include
from notifications import urls

urlpatterns = [
    path('docs/', include('docs.urls')),
                  path('admin/', admin.site.urls),
                  path('tinymce/', include('tinymce.urls')),
                  path('econgre/', include('econgre.urls')),
                  path('taggit_autosuggest/', include('taggit_autosuggest.urls')),
                  url('^inbox/notifications/', include(urls, namespace='notifications')),
                  path('basket/', include('basket.urls')),
                  path('api/', include('api.urls')),
                  path('sms/', include('smsgateway.urls')),
                  path('icossms/', include('smsicosnet.urls')),
                  url(r'^rest-auth/', include('rest_auth.urls')),
                  url(r'^rest-auth/registration/', include('rest_auth.registration.urls')),
                  url(r'^invitations/', include('invitations.urls', namespace='invitations')),
                  path('appointments/', include('appointements.urls')),
                  url(r'^captcha/', include('captcha.urls')),
                  url(r'^epayment/', include('epayment.urls')),
                  url(r'^clinical/', include('clinique.urls')),
                  url(r'^directory/', include('directory.urls')),
                  url(r'^rosetta/', include('rosetta.urls')),
                  url(r'^coupon/', include('coupons.urls')),
                  path('i18n/', include('django.conf.urls.i18n')),
                  path('newsletter/', include('enewsletter.urls')),
                  path('qr_code/', include('qr_code.urls', namespace="qr_code")),
                  path('expo/', include('expo.urls')),
                  path('', include('dicom.urls')),
                  url('^ptrack/', include('ptrack.urls')),
                  url(r'^maintenance-mode/', include('maintenance_mode.urls')),
                  url(r'^tracking/', include('tracking.urls')),
                  path('', include('store.urls')),
                  path('', include('teleconsultation.urls')),
                  path('', include('crm.urls')),
                  path('', include('ads.urls')),
                  path('', include('filesharing.urls')),
                  path('', include('core.urls')),
              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
if settings.DEBUG:
    urlpatterns = urlpatterns + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
