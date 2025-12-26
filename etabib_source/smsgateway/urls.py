from django.conf.urls import url

from smsgateway import views

urlpatterns = [
    # API
    url(r'^send_api/', views.SmsSendView.as_view(), name="list-sms"),
    url(r'^status_api/', views.SmsStatusView.as_view(), name="sms-status"),

    # sms & email urls
    url(r'^email/send/(?P<contact_pk>\d+)/$', views.SendEmailToContactView.as_view(), name='contact-send-email'),
    url(r'^sms/send/(?P<contact_pk>\d+)/$', views.SendSmsToContactView.as_view(), name='contact-send-sms'),

    ##Liste envoi statique
    url(r'^listenvoi/statique/list/$', views.ListEnvoiStatiqueDatatableView.as_view(), name='listenvoi-statique-list'),
    url(r'^listenvoi/statique/detail/(?P<listenvoi_pk>\d+)/$', views.ListEnvoiStatiqueDetailDatatableView.as_view(),
        name='listenvoi-statique-detail'),
    url(r'^listenvoi/statique/create/$', views.ListEnvoiStatiqueCreateView.as_view(),
        name='listenvoi-statique-create'),
    url(r'^listenvoi/statique/update/(?P<pk>\d+)/$', views.ListEnvoiStatiqueUpdateView.as_view(),
        name='listenvoi-statique-update'),
    url(r'^listenvoi/statique/add-contact/(?P<contact_pk>\d+)/$', views.ListEnvoiStatiqueAddContact.as_view(),
        name='listenvoi-statique-add-contact'),
    url(r'^listenvoi/statique/detail/delete-contact/(?P<listenvoi_pk>\d+)/(?P<contact_pk>\d+)/$',
        views.listEnvoiStatiqueDeleteContact, name='listenvoi-statique-detail-delete-contact'),
    url(r'^listenvoi/statique/send-sms-model/(?P<listenvoi_pk>\d+)/$',
        views.ListEnvoiStatiqueSendSmsModelView.as_view(),
        name='listenvoi-statique-send-sms-model'),
    url(r'^listenvoi/statique/send-sms/(?P<listenvoi_pk>\d+)/$', views.ListEnvoiStatiqueSendSmsView.as_view(),
        name='listenvoi-statique-send-sms'),
    url(r'^listenvoi/statique/send-email-model/(?P<listenvoi_pk>\d+)/$',
        views.ListEnvoiStatiqueSendEmailModelView.as_view(),
        name='listenvoi-statique-send-email-model'),
    url(r'^listenvoi/statique/send-email/(?P<listenvoi_pk>\d+)/$', views.ListEnvoiStatiqueSendEmailView.as_view(),
        name='listenvoi-statique-send-email'),

    ## List envoi dynamique
    url(r'^listenvoi/dynamique/list/$', views.ListEnvoiDynamiqueDatatableView.as_view(),
        name='listenvoi-dynamique-list'),
    url(r'^listenvoi/dynamique/create/$', views.ListEnvoiDynamiqueCreateView.as_view(),
        name='listenvoi-dynamique-create'),
    url(r'^listenvoi/dynamique/update/(?P<pk>\d+)/$', views.ListEnvoiDynamiqueUpdateView.as_view(),
        name='listenvoi-dynamique-update'),
    url(r'^listenvoi/dynamique/send-sms/(?P<critere_pk>\d+)/$', views.ListEnvoiDynamiqueSendSmsView.as_view(),
        name='listenvoi-dynamique-send-sms'),
    url(r'^listenvoi/dynamique/send-sms-model/(?P<critere_pk>\d+)/$',
        views.ListEnvoiDynamiqueSendSmsModelView.as_view(),
        name='listenvoi-dynamique-send-sms-model'),
    url(r'^listenvoi/dynamique/send-email-model/(?P<critere_pk>\d+)/$',
        views.ListEnvoiDynamiqueSendEmailModelView.as_view(),
        name='listenvoi-dynamique-send-email-model'),
    url(r'^listenvoi/dynamique/send-email/(?P<critere_pk>\d+)/$', views.ListEnvoiDynamiqueSendEmailView.as_view(),
        name='listenvoi-dynamique-send-email'),
    url(r'^listenvoi/dynamique/email-problems/(?P<critere_pk>\d+)/$',
        views.ListEnvoiDynamiqueEmailProblemeDatatableView.as_view(),
        name='listenvoi-dynamique-email-probleme'),
    url(r'^listenvoi/dynamique/mobile-problems/(?P<critere_pk>\d+)/$',
        views.ListEnvoiDynamiqueMobileProblemeDatatableView.as_view(),
        name='listenvoi-dynamique-mobile-probleme'),
    url(r'^listenvoi/dynamique/problems/fix/(?P<pk>\d+)/$', views.ListEnvoiDynamiqueProblemeFixView.as_view(),
        name='listenvoi-dynamique-probleme-fix'),

    ## SMS modeles
    url(r'^smsmodel/list/$', views.SmsModelDatatableView.as_view(), name='smsmodel-list'),
    url(r'^smsmodel/create/$', views.SmsModelCreateView.as_view(), name='smsmodel-create'),
    url(r'^smsmodel/update/(?P<pk>\d+)/$', views.SmsModelUpdateView.as_view(), name='smsmodel-update'),
    url(r'^smsmodel/delete/(?P<pk>\d+)/$', views.SmsModelDeleteView.as_view(), name='smsmodel-delete'),

    ## Email modeles
    url(r'^emailmodel/list/$', views.EmailModelDatatableView.as_view(), name='emailmodel-list'),
    url(r'^emailmodel/create/$', views.EmailModelCreateView.as_view(), name='emailmodel-create'),
    url(r'^emailmodel/update/(?P<pk>\d+)/$', views.EmailModelUpdateView.as_view(), name='emailmodel-update'),
    url(r'^emailmodel/delete/(?P<pk>\d+)/$', views.EmailModelDeleteView.as_view(), name='emailmodel-delete'),

    ## Email and sms history
    url(r'^sms/history/(?P<contact_pk>\d+)/$', views.HistoriqueSmsDatatableView.as_view(), name='sms-history'),
    url(r'^email/history/(?P<contact_pk>\d+)/$', views.HistoriqueEmailDatatableView.as_view(), name='email-history'),

]
