from django.conf.urls import url

from smsicosnet import views

urlpatterns = [
    # Send sms Icosnet
    url(r'^sms/prospect/$', views.SendSmsProspectIcosnet, name='prospect-send-sms'),
]

